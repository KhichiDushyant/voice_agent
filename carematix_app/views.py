"""
Django views for the Carematix healthcare scheduling system.
"""

import json
import logging
import asyncio
import websockets
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import (
    Patient, Nurse, PatientNurseAssignment, NurseAvailability, 
    NurseAvailabilityOverride, Appointment, Call, ConversationLog, 
    CallTranscript, Notification
)
from .database_helper import VoiceAgentDatabaseHelper
from django.conf import settings

logger = logging.getLogger('carematix.views')


@api_view(['GET'])
def index_page(request):
    """Health check endpoint."""
    return Response({
        "message": "Carematix AI Voice Assistant is running!", 
        "status": "healthy"
    })


@api_view(['GET'])
def dashboard(request):
    """Serve the dashboard HTML page."""
    from django.shortcuts import render
    return render(request, 'dashboard.html')


@api_view(['GET'])
def test_transcripts_page(request):
    """Serve a test page for transcript functionality."""
    from django.http import HttpResponse
    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Test Transcript Functionality</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .call-item { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
        .btn { padding: 8px 12px; margin: 5px; background: #007bff; color: white; border: none; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .modal { display: none; position: fixed; top: 50px; left: 50px; right: 50px; bottom: 50px; background: white; border: 2px solid #333; padding: 20px; overflow-y: auto; z-index: 1000; }
        .modal.show { display: block; }
        .close { float: right; font-size: 20px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Transcript Testing Page</h1>
    <p>This page tests the transcript functionality by directly calling the APIs.</p>
    
    <div id="calls-container"></div>
    
    <div id="modal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <div id="modal-content"></div>
    </div>

    <script>
        async function loadCalls() {
            try {
                const response = await fetch('/calls/');
                const calls = await response.json();
                
                const container = document.getElementById('calls-container');
                container.innerHTML = calls.map(call => `
                    <div class="call-item">
                        <h3>Call ${call.id} - ${call.patient_name}</h3>
                        <p><strong>Status:</strong> ${call.call_status}</p>
                        <p><strong>Phone:</strong> ${call.patient_phone}</p>
                        <p><strong>Duration:</strong> ${call.call_duration || 'N/A'} seconds</p>
                        <button class="btn" onclick="viewTranscript(${call.id})">View Transcript</button>
                        <button class="btn" onclick="viewDetails(${call.id})">View Details</button>
                    </div>
                `).join('');
                
                console.log('Loaded', calls.length, 'calls');
            } catch (error) {
                console.error('Error loading calls:', error);
            }
        }
        
        async function viewTranscript(callId) {
            try {
                const response = await fetch(`/calls/${callId}/transcript/`);
                const data = await response.json();
                const transcript = data.transcript;
                
                const content = `
                    <h2>Transcript for Call ${callId}</h2>
                    <h3>Full Conversation</h3>
                    <div style="border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">
                        ${transcript.full_transcript.replace(/\\\\n/g, '<br>')}
                    </div>
                    <h3>Summary</h3>
                    <p>${transcript.appointment_summary}</p>
                    <h3>Outcome</h3>
                    <p><strong>${transcript.scheduling_outcome}</strong></p>
                `;
                
                showModal(content);
            } catch (error) {
                console.error('Error loading transcript:', error);
                alert('Failed to load transcript');
            }
        }
        
        async function viewDetails(callId) {
            try {
                const response = await fetch(`/calls/${callId}/details/`);
                const data = await response.json();
                const call = data.call;
                const transcript = data.transcript;
                
                const content = `
                    <h2>Call Details for Call ${callId}</h2>
                    <p><strong>Patient:</strong> ${call.patient_name}</p>
                    <p><strong>Phone:</strong> ${call.patient_phone}</p>
                    <p><strong>Status:</strong> ${call.call_status}</p>
                    <p><strong>Direction:</strong> ${call.call_direction}</p>
                    <p><strong>Duration:</strong> ${call.call_duration || 'N/A'} seconds</p>
                    
                    ${transcript ? `
                        <h3>Transcript Available</h3>
                        <p><strong>Summary:</strong> ${transcript.appointment_summary}</p>
                        <p><strong>Outcome:</strong> ${transcript.scheduling_outcome}</p>
                        <h4>Full Conversation</h4>
                        <div style="border: 1px solid #ddd; padding: 10px; background: #f9f9f9; max-height: 200px; overflow-y: auto;">
                            ${transcript.full_transcript.replace(/\\\\n/g, '<br>')}
                        </div>
                    ` : '<p>No transcript available</p>'}
                `;
                
                showModal(content);
            } catch (error) {
                console.error('Error loading details:', error);
                alert('Failed to load call details');
            }
        }
        
        function showModal(content) {
            document.getElementById('modal-content').innerHTML = content;
            document.getElementById('modal').classList.add('show');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('show');
        }
        
        loadCalls();
    </script>
</body>
</html>'''
    return HttpResponse(html_content)


@api_view(['GET'])
def test_openai_connection(request):
    """Test OpenAI Realtime API connection."""
    try:
        async def test_connection():
            async with websockets.connect(
                f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={settings.OPENAI_TEMPERATURE}",
                additional_headers=[
                    ("Authorization", f"Bearer {settings.OPENAI_API_KEY}")
                ]
            ) as openai_ws:
                # Send a simple session update
                session_update = {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": "gpt-realtime",
                        "output_modalities": ["audio"],
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcmu"},
                                "turn_detection": {"type": "server_vad"}
                            },
                            "output": {
                                "format": {"type": "audio/pcmu"},
                                "voice": settings.OPENAI_VOICE
                            }
                        },
                        "instructions": "Test connection."
                    }
                }
                
                await openai_ws.send(json.dumps(session_update))
                
                # Wait for session update confirmation
                async for message in openai_ws:
                    response = json.loads(message)
                    if response['type'] == 'session.updated':
                        await openai_ws.close()
                        return {"status": "success", "message": "OpenAI connection working"}
                    elif response['type'] == 'error':
                        await openai_ws.close()
                        return {"status": "error", "message": f"OpenAI error: {response}"}
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_connection())
        loop.close()
        
        return Response(result)
        
    except Exception as e:
        return Response(
            {"status": "error", "message": f"Connection failed: {str(e)}"}, 
            status=500
        )


@api_view(['POST'])
def make_outbound_call(request):
    """Initiate an outbound call to a specified phone number."""
    logger.info("=== OUTBOUND CALL REQUEST STARTED ===")
    
    try:
        data = request.data
        to_number = data.get('phone_number')
        logger.info(f"Received call request for phone number: {to_number}")
        
        if not to_number:
            logger.error("No phone number provided in request")
            return Response(
                {"error": "Phone number is required"},
                status=400
            )

        # Validate phone number format
        if not to_number.startswith('+'):
            logger.warning(f"Phone number {to_number} doesn't start with '+', this might cause issues")
        
        # Create full webhook URL using ngrok URL if provided, otherwise use current host
        if settings.NGROK_URL:
            # Remove protocol if present and construct WebSocket URL
            clean_ngrok = settings.NGROK_URL.replace('https://', '').replace('http://', '')
            webhook_url = f"wss://{clean_ngrok}/ws/media-stream/"
            logger.info(f"Using NGROK URL for webhook: {webhook_url}")
        else:
            host = request.get_host()
            webhook_url = f"wss://{host}/ws/media-stream/"
            logger.info(f"Using request host for webhook: {webhook_url}")
        
        # Create TwiML with greeting messages and media stream connection
        from twilio.twiml.voice_response import VoiceResponse, Connect, Say
        
        response = VoiceResponse()
        
        connect = Connect()
        stream = connect.stream(url=webhook_url)
        stream.parameter(name="format", value="audio/pcmu")
        response.append(connect)
        
        # Log TwiML being sent to Twilio
        twiml_content = str(response)
        logger.info(f"TwiML to be sent to Twilio:\n{twiml_content}")
        
        # Make the call
        from twilio.rest import Client
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        logger.info(f"Attempting to create call from {settings.TWILIO_PHONE_NUMBER} to {to_number}")
        call = twilio_client.calls.create(
            to=to_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            twiml=twiml_content
        )
        
        logger.info(f"Call created successfully! Call SID: {call.sid}")
        logger.info(f"Call status: {call.status}")
        logger.info(f"Call direction: {call.direction}")
        
        # Log the call start in database
        try:
            call_obj = Call.objects.create(
                call_sid=call.sid,
                patient_phone=to_number,
                call_direction="outbound",
                call_status="initiated"
            )
            logger.info(f"Call logged in database with ID: {call_obj.id}")
        except Exception as db_error:
            logger.error(f"Failed to log call in database: {db_error}")
            # Don't fail the call if database logging fails
        
        logger.info("=== OUTBOUND CALL REQUEST COMPLETED SUCCESSFULLY ===")
        return Response({
            "message": "Call initiated", 
            "call_sid": call.sid, 
            "call_id": call_obj.id if 'call_obj' in locals() else None,
            "status": call.status,
            "webhook_url": webhook_url
        })
        
    except Exception as e:
        error_msg = f"Error in make_outbound_call: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Full traceback: {str(e)}")
        
        return Response(
            {"error": error_msg},
            status=500
        )


@api_view(['GET', 'POST'])
def handle_incoming_call(request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    from twilio.twiml.voice_response import VoiceResponse, Connect, Say
    
    response = VoiceResponse()
    # <Say> punctuation to improve text-to-speech flow
    response.say(
        "Please wait while we connect your call to the A. I. voice assistant, powered by Twilio and the Open A I Realtime API",
        voice="Google.en-US-Chirp3-HD-Aoede"
    )
    response.pause(length=1)
    response.say(   
        "O.K. you can start talking!",
        voice="Google.en-US-Chirp3-HD-Aoede"
    )
    host = request.get_host()
    connect = Connect()
    connect.stream(url=f'wss://{host}/ws/media-stream/')
    response.append(connect)
    return HttpResponse(str(response), content_type="application/xml")


@api_view(['GET'])
def get_available_nurses(request):
    """Get available nurses for a specific date and time slot."""
    date = request.GET.get('date')
    time_slot = request.GET.get('time_slot')
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
        day_of_week = appointment_date.strftime("%A")
        
        if time_slot:
            # Check specific time slot
            nurses = Nurse.objects.filter(
                is_active=True
            ).filter(
                Q(availability__day_of_week=day_of_week, availability__is_available=True) |
                Q(availability_overrides__override_date=appointment_date, availability_overrides__is_available=True)
            ).exclude(
                appointments__appointment_date=appointment_date,
                appointments__appointment_time=time_slot,
                appointments__status__in=['scheduled', 'confirmed']
            ).distinct()
        else:
            # Get all nurses with availability for the day
            nurses = Nurse.objects.filter(
                is_active=True
            ).filter(
                Q(availability__day_of_week=day_of_week, availability__is_available=True) |
                Q(availability_overrides__override_date=appointment_date, availability_overrides__is_available=True)
            ).distinct()
        
        nurse_data = []
        for nurse in nurses:
            nurse_data.append({
                'id': nurse.id,
                'name': nurse.name,
                'specialization': nurse.specialization,
                'phone': nurse.phone,
                'email': nurse.email
            })
        
        return Response({
            "nurses": nurse_data, 
            "date": date, 
            "time_slot": time_slot
        })
        
    except Exception as e:
        logger.error(f"Error getting available nurses: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_call_history(request):
    """Get call history, optionally filtered by patient phone."""
    patient_phone = request.GET.get('patient_phone')
    limit = int(request.GET.get('limit', 50))
    
    try:
        calls_query = Call.objects.select_related('patient').all()
        
        if patient_phone:
            calls_query = calls_query.filter(patient_phone=patient_phone)
        
        calls = calls_query.order_by('-start_time')[:limit]
        
        call_data = []
        for call in calls:
            call_data.append({
                'id': call.id,
                'call_sid': call.call_sid,
                'patient_phone': call.patient_phone,
                'patient_id': call.patient.id if call.patient else None,
                'call_direction': call.call_direction,
                'call_status': call.call_status,
                'call_duration': call.call_duration,
                'appointment_scheduled': call.appointment_scheduled,
                'appointment_id': call.appointment.id if call.appointment else None,
                'start_time': call.start_time.isoformat(),
                'end_time': call.end_time.isoformat() if call.end_time else None,
                'patient_name': call.patient.name if call.patient else None
            })
        
        return Response({"calls": call_data})
        
    except Exception as e:
        logger.error(f"Error getting call history: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_call_transcript(request, call_id):
    """Get the full transcript for a specific call."""
    try:
        call = Call.objects.get(id=call_id)
        transcript = getattr(call, 'transcript', None)
        
        if not transcript:
            return Response(
                {"error": "Transcript not found for this call"},
                status=404
            )
        
        return Response({
            "transcript": {
                "id": transcript.id,
                "call_id": transcript.call.id,
                "full_transcript": transcript.full_transcript,
                "patient_transcript": transcript.patient_transcript,
                "assistant_transcript": transcript.assistant_transcript,
                "appointment_summary": transcript.appointment_summary,
                "scheduling_outcome": transcript.scheduling_outcome,
                "created_at": transcript.created_at.isoformat()
            }
        })
        
    except Call.DoesNotExist:
        return Response(
            {"error": "Call not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting call transcript: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_call_details(request, call_id):
    """Get detailed information about a specific call including transcripts."""
    try:
        call = Call.objects.select_related('patient', 'appointment').get(id=call_id)
        
        call_info = {
            "id": call.id,
            "call_sid": call.call_sid,
            "patient_phone": call.patient_phone,
            "patient_id": call.patient.id if call.patient else None,
            "call_direction": call.call_direction,
            "call_status": call.call_status,
            "call_duration": call.call_duration,
            "appointment_scheduled": call.appointment_scheduled,
            "appointment_id": call.appointment.id if call.appointment else None,
            "start_time": call.start_time.isoformat(),
            "end_time": call.end_time.isoformat() if call.end_time else None,
            "patient_name": call.patient.name if call.patient else None,
            "nurse_name": call.appointment.nurse.name if call.appointment else None,
            "nurse_specialization": call.appointment.nurse.specialization if call.appointment else None
        }

        # Get conversation transcript
        transcript = getattr(call, 'transcript', None)
        transcript_info = None
        if transcript:
            transcript_info = {
                "full_transcript": transcript.full_transcript,
                "patient_transcript": transcript.patient_transcript,
                "assistant_transcript": transcript.assistant_transcript,
                "appointment_summary": transcript.appointment_summary,
                "scheduling_outcome": transcript.scheduling_outcome
            }

        # Get conversation parts
        conversation_parts = []
        conversation_logs = call.conversation_logs.all().order_by('timestamp')
        for log in conversation_logs:
            conversation_parts.append({
                "speaker": log.speaker,
                "message": log.message_text,
                "message_type": log.message_type,
                "timestamp": log.timestamp.isoformat()
            })

        return Response({
            "call": call_info,
            "transcript": transcript_info,
            "conversation": conversation_parts
        })

    except Call.DoesNotExist:
        return Response(
            {"error": "Call not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting call details: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_all_transcripts(request):
    """Get all call transcripts with call details."""
    limit = int(request.GET.get('limit', 50))
    
    try:
        transcripts = CallTranscript.objects.select_related(
            'call', 'call__patient'
        ).order_by('-created_at')[:limit]
        
        transcript_data = []
        for transcript in transcripts:
            transcript_data.append({
                'id': transcript.id,
                'call_id': transcript.call.id,
                'full_transcript': transcript.full_transcript,
                'patient_transcript': transcript.patient_transcript,
                'assistant_transcript': transcript.assistant_transcript,
                'appointment_summary': transcript.appointment_summary,
                'scheduling_outcome': transcript.scheduling_outcome,
                'created_at': transcript.created_at.isoformat(),
                'patient_phone': transcript.call.patient_phone,
                'call_direction': transcript.call.call_direction,
                'call_status': transcript.call.call_status,
                'patient_name': transcript.call.patient.name if transcript.call.patient else None
            })
        
        return Response({"transcripts": transcript_data})
        
    except Exception as e:
        logger.error(f"Error getting all transcripts: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['POST'])
def schedule_nurse_call(request, call_id):
    """Schedule a nurse for a specific call."""
    try:
        data = request.data
        nurse_id = data.get('nurse_id')
        scheduled_date = data.get('scheduled_date')
        scheduled_time = data.get('scheduled_time')
        
        if not all([nurse_id, scheduled_date, scheduled_time]):
            return Response(
                {"error": "nurse_id, scheduled_date, and scheduled_time are required"},
                status=400
            )
        
        call = Call.objects.get(id=call_id)
        appointment_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
        appointment_time = datetime.strptime(scheduled_time, "%H:%M").time()
        
        # Create appointment
        appointment = Appointment.objects.create(
            patient=call.patient,
            nurse_id=nurse_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        )
        
        # Update call with appointment info
        call.appointment_scheduled = True
        call.appointment = appointment
        call.save()
        
        # Get appointment details for confirmation
        appointment_details = {
            'id': appointment.id,
            'patient_name': appointment.patient.name,
            'nurse_name': appointment.nurse.name,
            'appointment_date': appointment.appointment_date.isoformat(),
            'appointment_time': appointment.appointment_time.strftime("%H:%M")
        }
        
        # Create notifications
        Notification.objects.create(
            recipient_type="patient",
            recipient_id=appointment.patient.name,
            notification_type="appointment_confirmed",
            message=f"Your appointment with {appointment.nurse.name} is scheduled for {appointment.appointment_date} at {appointment.appointment_time}",
            appointment=appointment
        )
        
        Notification.objects.create(
            recipient_type="nurse",
            recipient_id=appointment.nurse.name,
            notification_type="appointment_assigned",
            message=f"New appointment scheduled with {appointment.patient.name} on {appointment.appointment_date} at {appointment.appointment_time}",
            appointment=appointment
        )
        
        return Response({
            "message": "Nurse scheduled successfully",
            "appointment_id": appointment.id,
            "appointment": appointment_details
        })
        
    except Call.DoesNotExist:
        return Response(
            {"error": "Call not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error scheduling nurse call: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_patient_assigned_nurse(request, patient_phone):
    """Get the assigned nurse for a patient."""
    try:
        # First get patient by phone
        patient = Patient.objects.get(phone=patient_phone)
        
        # Get assigned nurse
        assignment = PatientNurseAssignment.objects.filter(
            patient=patient,
            assignment_date=datetime.now().date(),
            is_primary=True
        ).select_related('nurse').first()
        
        if not assignment:
            return Response(
                {"error": "No assigned nurse found for this patient"},
                status=404
            )
        
        nurse_data = {
            'id': assignment.nurse.id,
            'name': assignment.nurse.name,
            'specialization': assignment.nurse.specialization,
            'phone': assignment.nurse.phone,
            'email': assignment.nurse.email
        }
        
        patient_data = {
            'id': patient.id,
            'name': patient.name,
            'phone': patient.phone,
            'email': patient.email
        }
        
        return Response({
            "nurse": nurse_data, 
            "patient": patient_data
        })
        
    except Patient.DoesNotExist:
        return Response(
            {"error": "Patient not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting patient assigned nurse: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_nurse_availability(request, nurse_id):
    """Get available time slots for a specific nurse on a given date."""
    try:
        date = request.GET.get('date')
        duration = int(request.GET.get('duration', 30))
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Check if nurse exists
        nurse = Nurse.objects.get(id=nurse_id)
        appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Get available slots using database helper
        db_helper = VoiceAgentDatabaseHelper()
        available_slots = db_helper._get_nurse_available_slots(nurse_id, appointment_date, duration)
        
        nurse_data = {
            'id': nurse.id,
            'name': nurse.name,
            'specialization': nurse.specialization,
            'phone': nurse.phone,
            'email': nurse.email
        }
        
        return Response({
            "nurse": nurse_data,
            "date": date,
            "available_slots": available_slots,
            "duration_minutes": duration
        })
        
    except Nurse.DoesNotExist:
        return Response(
            {"error": "Nurse not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting nurse availability: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['POST'])
def create_appointment(request):
    """Create a new appointment directly."""
    try:
        data = request.data
        patient_phone = data.get('patient_phone')
        patient_id = data.get('patient_id')
        nurse_id = data.get('nurse_id')
        appointment_date = data.get('appointment_date')
        appointment_time = data.get('appointment_time')
        duration = data.get('duration_minutes', 30)
        appointment_type = data.get('appointment_type', 'consultation')
        notes = data.get('notes')
        
        # If patient_phone is provided, get patient_id
        if patient_phone and not patient_id:
            patient = Patient.objects.get(phone=patient_phone)
            patient_id = patient.id
        
        if not all([patient_id, nurse_id, appointment_date, appointment_time]):
            return Response(
                {"error": "patient_id (or patient_phone), nurse_id, appointment_date, and appointment_time are required"},
                status=400
            )
        
        # Check availability using database helper
        db_helper = VoiceAgentDatabaseHelper()
        appointment_date_obj = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        appointment_time_obj = datetime.strptime(appointment_time, "%H:%M").time()
        
        if not db_helper._check_nurse_availability(nurse_id, appointment_date_obj, appointment_time_obj, duration):
            return Response(
                {"error": "Nurse not available at requested time"},
                status=409
            )
        
        # Create appointment
        appointment = Appointment.objects.create(
            patient_id=patient_id,
            nurse_id=nurse_id,
            appointment_date=appointment_date_obj,
            appointment_time=appointment_time_obj,
            duration_minutes=duration,
            appointment_type=appointment_type,
            notes=notes
        )
        
        # Get appointment details
        appointment_details = {
            'id': appointment.id,
            'patient_name': appointment.patient.name,
            'patient_phone': appointment.patient.phone,
            'patient_email': appointment.patient.email,
            'nurse_name': appointment.nurse.name,
            'nurse_phone': appointment.nurse.phone,
            'nurse_email': appointment.nurse.email,
            'nurse_specialization': appointment.nurse.specialization,
            'appointment_date': appointment.appointment_date.isoformat(),
            'appointment_time': appointment.appointment_time.strftime("%H:%M"),
            'duration_minutes': appointment.duration_minutes,
            'status': appointment.status,
            'appointment_type': appointment.appointment_type,
            'notes': appointment.notes,
            'created_at': appointment.created_at.isoformat()
        }
        
        return Response({
            "message": "Appointment created successfully",
            "appointment_id": appointment.id,
            "appointment": appointment_details
        })
        
    except Patient.DoesNotExist:
        return Response(
            {"error": "Patient not found with provided phone number"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_appointment(request, appointment_id):
    """Get appointment details by ID."""
    try:
        appointment = Appointment.objects.select_related('patient', 'nurse').get(id=appointment_id)
        
        appointment_data = {
            'id': appointment.id,
            'patient_name': appointment.patient.name,
            'patient_phone': appointment.patient.phone,
            'patient_email': appointment.patient.email,
            'nurse_name': appointment.nurse.name,
            'nurse_phone': appointment.nurse.phone,
            'nurse_email': appointment.nurse.email,
            'nurse_specialization': appointment.nurse.specialization,
            'appointment_date': appointment.appointment_date.isoformat(),
            'appointment_time': appointment.appointment_time.strftime("%H:%M"),
            'duration_minutes': appointment.duration_minutes,
            'status': appointment.status,
            'appointment_type': appointment.appointment_type,
            'notes': appointment.notes,
            'created_at': appointment.created_at.isoformat(),
            'updated_at': appointment.updated_at.isoformat()
        }
        
        return Response({"appointment": appointment_data})
        
    except Appointment.DoesNotExist:
        return Response(
            {"error": "Appointment not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_appointments(request):
    """Get appointments with optional filters."""
    try:
        patient_id = request.GET.get('patient_id')
        nurse_id = request.GET.get('nurse_id')
        date = request.GET.get('date')
        limit = int(request.GET.get('limit', 50))
        
        appointments_query = Appointment.objects.select_related('patient', 'nurse').all()
        
        if patient_id:
            appointments_query = appointments_query.filter(patient_id=patient_id)
        
        if nurse_id:
            appointments_query = appointments_query.filter(nurse_id=nurse_id)
        
        if date:
            appointments_query = appointments_query.filter(appointment_date=date)
        
        appointments = appointments_query.order_by('appointment_date', 'appointment_time')[:limit]
        
        appointment_data = []
        for appointment in appointments:
            appointment_data.append({
                'id': appointment.id,
                'appointment_date': appointment.appointment_date.isoformat(),
                'appointment_time': appointment.appointment_time.strftime("%H:%M"),
                'duration_minutes': appointment.duration_minutes,
                'status': appointment.status,
                'appointment_type': appointment.appointment_type,
                'notes': appointment.notes,
                'created_at': appointment.created_at.isoformat(),
                'patient_name': appointment.patient.name,
                'patient_phone': appointment.patient.phone,
                'nurse_name': appointment.nurse.name,
                'nurse_specialization': appointment.nurse.specialization
            })
        
        return Response({"appointments": appointment_data})
        
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['POST'])
def create_notification(request):
    """Create a notification for a patient or nurse."""
    try:
        data = request.data
        recipient_type = data.get('recipient_type')
        recipient_id = data.get('recipient_id')
        notification_type = data.get('notification_type')
        message = data.get('message')
        appointment_id = data.get('appointment_id')
        
        if not all([recipient_type, recipient_id, notification_type, message]):
            return Response(
                {"error": "recipient_type, recipient_id, notification_type, and message are required"},
                status=400
            )
        
        appointment = None
        if appointment_id:
            appointment = Appointment.objects.get(id=appointment_id)
        
        Notification.objects.create(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            notification_type=notification_type,
            message=message,
            appointment=appointment
        )
        
        return Response({"message": "Notification created successfully"})
        
    except Appointment.DoesNotExist:
        return Response(
            {"error": "Appointment not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


# Dashboard API endpoints
@api_view(['GET'])
def get_all_patients(request):
    """Get all patients for dashboard."""
    try:
        patients = Patient.objects.all().order_by('-created_at')
        
        patient_data = []
        for patient in patients:
            patient_data.append({
                "id": patient.id,
                "name": patient.name,
                "phone": patient.phone,
                "email": patient.email,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "medical_conditions": patient.medical_conditions,
                "created_at": patient.created_at.isoformat(),
                "updated_at": patient.updated_at.isoformat()
            })
        
        return Response(patient_data)
        
    except Exception as e:
        logger.error(f"Error getting all patients: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_all_nurses(request):
    """Get all nurses for dashboard."""
    try:
        nurses = Nurse.objects.all().order_by('-created_at')
        
        nurse_data = []
        for nurse in nurses:
            nurse_data.append({
                "id": nurse.id,
                "name": nurse.name,
                "phone": nurse.phone,
                "email": nurse.email,
                "specialization": nurse.specialization,
                "license_number": nurse.license_number,
                "is_active": nurse.is_active,
                "created_at": nurse.created_at.isoformat(),
                "updated_at": nurse.updated_at.isoformat()
            })
        
        return Response(nurse_data)
        
    except Exception as e:
        logger.error(f"Error getting all nurses: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_all_calls(request):
    """Get all calls for dashboard."""
    try:
        calls = Call.objects.select_related('patient').all().order_by('-start_time')
        
        call_data = []
        for call in calls:
            call_data.append({
                "id": call.id,
                "call_sid": call.call_sid,
                "patient_phone": call.patient_phone,
                "patient_id": call.patient.id if call.patient else None,
                "call_direction": call.call_direction,
                "call_status": call.call_status,
                "call_duration": call.call_duration,
                "appointment_scheduled": call.appointment_scheduled,
                "appointment_id": call.appointment.id if call.appointment else None,
                "start_time": call.start_time.isoformat(),
                "end_time": call.end_time.isoformat() if call.end_time else None,
                "patient_name": call.patient.name if call.patient else None
            })
        
        return Response(call_data)
        
    except Exception as e:
        logger.error(f"Error getting all calls: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['POST'])
def add_patient(request):
    """Add a new patient via API."""
    try:
        data = request.data
        patient = Patient.objects.create(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email'),
            date_of_birth=data.get('date_of_birth'),
            medical_conditions=data.get('medical_conditions', [])
        )
        
        return Response({
            "success": True, 
            "patient_id": patient.id, 
            "message": "Patient added successfully"
        })
        
    except Exception as e:
        logger.error(f"Error adding patient: {e}")
        return Response(
            {"error": str(e)},
            status=400
        )


@api_view(['POST'])
def add_nurse(request):
    """Add a new nurse via API."""
    try:
        data = request.data
        nurse = Nurse.objects.create(
            name=data['name'],
            specialization=data['specialization'],
            phone=data.get('phone'),
            email=data.get('email'),
            license_number=data.get('license_number')
        )
        
        return Response({
            "success": True, 
            "nurse_id": nurse.id, 
            "message": "Nurse added successfully"
        })
        
    except Exception as e:
        logger.error(f"Error adding nurse: {e}")
        return Response(
            {"error": str(e)},
            status=400
        )


@api_view(['POST'])
def assign_nurse_to_patient(request):
    """Assign a nurse to a patient."""
    try:
        data = request.data
        patient_id = data.get('patient_id')
        nurse_id = data.get('nurse_id')
        assignment_date = data.get('assignment_date', datetime.now().strftime('%Y-%m-%d'))
        is_primary = data.get('is_primary', True)
        notes = data.get('notes', '')
        
        if not patient_id or not nurse_id:
            return Response(
                {"error": "patient_id and nurse_id are required"},
                status=400
            )
        
        # Check if patient exists
        patient = Patient.objects.get(id=patient_id)
        
        # Check if nurse exists
        nurse = Nurse.objects.get(id=nurse_id)
        
        # Assign nurse to patient
        assignment = PatientNurseAssignment.objects.create(
            patient=patient,
            nurse=nurse,
            assignment_date=assignment_date,
            is_primary=is_primary,
            notes=notes
        )
        
        return Response({
            "success": True, 
            "assignment_id": assignment.id,
            "message": f"Nurse {nurse.name} assigned to patient {patient.name}"
        })
        
    except Patient.DoesNotExist:
        return Response(
            {"error": "Patient not found"},
            status=404
        )
    except Nurse.DoesNotExist:
        return Response(
            {"error": "Nurse not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error assigning nurse to patient: {e}")
        return Response(
            {"error": str(e)},
            status=400
        )


@api_view(['GET'])
def get_patient_nurses(request, patient_id):
    """Get all nurses assigned to a patient."""
    try:
        assignments = PatientNurseAssignment.objects.filter(
            patient_id=patient_id
        ).select_related('nurse').order_by('-assignment_date', '-is_primary')
        
        nurses = []
        for assignment in assignments:
            nurses.append({
                'assignment_id': assignment.id,
                'assignment_date': assignment.assignment_date.isoformat(),
                'is_primary': assignment.is_primary,
                'notes': assignment.notes,
                'created_at': assignment.created_at.isoformat(),
                'nurse_id': assignment.nurse.id,
                'nurse_name': assignment.nurse.name,
                'specialization': assignment.nurse.specialization,
                'phone': assignment.nurse.phone,
                'email': assignment.nurse.email
            })
        
        return Response({"nurses": nurses})
        
    except Exception as e:
        logger.error(f"Error getting patient nurses: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['DELETE'])
def remove_nurse_assignment(request, assignment_id):
    """Remove a nurse assignment."""
    try:
        assignment = PatientNurseAssignment.objects.get(id=assignment_id)
        assignment.delete()
        
        return Response({
            "success": True, 
            "message": "Nurse assignment removed"
        })
        
    except PatientNurseAssignment.DoesNotExist:
        return Response(
            {"error": "Assignment not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error removing nurse assignment: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['PUT'])
def update_patient(request, patient_id):
    """Update patient information."""
    try:
        patient = Patient.objects.get(id=patient_id)
        data = request.data
        
        patient.name = data.get('name', patient.name)
        patient.phone = data.get('phone', patient.phone)
        patient.email = data.get('email', patient.email)
        patient.date_of_birth = data.get('date_of_birth', patient.date_of_birth)
        patient.medical_conditions = data.get('medical_conditions', patient.medical_conditions)
        patient.save()
        
        return Response({
            "success": True,
            "message": "Patient updated successfully"
        })
        
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)
    except Exception as e:
        logger.error(f"Error updating patient: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['DELETE'])
def delete_patient(request, patient_id):
    """Delete a patient."""
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.delete()
        
        return Response({
            "success": True,
            "message": "Patient deleted successfully"
        })
        
    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting patient: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['PUT'])
def update_nurse(request, nurse_id):
    """Update nurse information."""
    try:
        nurse = Nurse.objects.get(id=nurse_id)
        data = request.data
        
        nurse.name = data.get('name', nurse.name)
        nurse.specialization = data.get('specialization', nurse.specialization)
        nurse.phone = data.get('phone', nurse.phone)
        nurse.email = data.get('email', nurse.email)
        nurse.license_number = data.get('license_number', nurse.license_number)
        nurse.save()
        
        return Response({
            "success": True,
            "message": "Nurse updated successfully"
        })
        
    except Nurse.DoesNotExist:
        return Response({"error": "Nurse not found"}, status=404)
    except Exception as e:
        logger.error(f"Error updating nurse: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['DELETE'])
def delete_nurse(request, nurse_id):
    """Delete a nurse."""
    try:
        nurse = Nurse.objects.get(id=nurse_id)
        nurse.delete()
        
        return Response({
            "success": True,
            "message": "Nurse deleted successfully"
        })
        
    except Nurse.DoesNotExist:
        return Response({"error": "Nurse not found"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting nurse: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['PUT'])
def update_appointment(request, appointment_id):
    """Update appointment information."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        data = request.data
        
        if 'appointment_date' in data:
            appointment.appointment_date = data['appointment_date']
        if 'appointment_time' in data:
            appointment.appointment_time = data['appointment_time']
        if 'duration_minutes' in data:
            appointment.duration_minutes = data['duration_minutes']
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        
        appointment.save()
        
        return Response({
            "success": True,
            "message": "Appointment updated successfully"
        })
        
    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['DELETE'])
def delete_appointment(request, appointment_id):
    """Delete an appointment."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.delete()
        
        return Response({
            "success": True,
            "message": "Appointment deleted successfully"
        })
        
    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting appointment: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
def make_test_call(request):
    """Make a test call to a patient with OpenAI integration."""
    try:
        data = request.data
        patient_phone = data.get('patient_phone')
        patient_id = data.get('patient_id')
        
        if not patient_phone and not patient_id:
            return Response(
                {"error": "Either patient_phone or patient_id is required"},
                status=400
            )
        
        # Get patient information
        if patient_id:
            patient = Patient.objects.get(id=patient_id)
        else:
            patient = Patient.objects.get(phone=patient_phone)
        
        # Get assigned nurse
        try:
            assignment = PatientNurseAssignment.objects.filter(
                patient=patient, is_primary=True
            ).select_related('nurse').first()
            
            if assignment:
                nurse = assignment.nurse
            else:
                # Get any available nurse if no primary assignment
                nurse = Nurse.objects.filter(is_active=True).first()
        except:
            nurse = None
        
        # Create call record
        call = Call.objects.create(
            patient_phone=patient.phone,
            patient=patient,
            call_direction='outbound',
            call_status='initiated'
        )
        
        # Prepare patient and nurse context for OpenAI
        context = {
            'patient': {
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone,
                'medical_conditions': patient.medical_conditions
            },
            'nurse': {
                'id': nurse.id if nurse else None,
                'name': nurse.name if nurse else 'No assigned nurse',
                'specialization': nurse.specialization if nurse else 'General'
            },
            'call_id': call.id
        }
        
        return Response({
            "success": True,
            "message": f"Test call initiated to {patient.name}",
            "call_id": call.id,
            "patient_context": context['patient'],
            "nurse_context": context['nurse']
        })
        
    except Patient.DoesNotExist:
        return Response(
            {"error": "Patient not found"},
            status=404
        )
    except Exception as e:
        logger.error(f"Error making test call: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(['GET'])
def get_call_audio(request, call_id, speaker):
    """Get audio recording for a specific call and speaker."""
    try:
        import os
        audio_file = f"recordings/call_{call_id}_{speaker}.wav"
        if os.path.exists(audio_file):
            return FileResponse(open(audio_file, 'rb'), content_type="audio/wav")
        else:
            return Response(
                {"error": "Audio file not found"},
                status=404
            )
    except Exception as e:
        logger.error(f"Error getting call audio: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )

