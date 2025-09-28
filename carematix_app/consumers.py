"""
WebSocket consumers for the Carematix healthcare scheduling system.
"""

import json
import asyncio
import logging
import traceback
import base64
import wave
import os
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .models import Call, ConversationLog, CallTranscript, Patient, Nurse, PatientNurseAssignment
from .database_helper import VoiceAgentDatabaseHelper

logger = logging.getLogger('carematix.websocket')
openai_logger = logging.getLogger('carematix.openai')


class MediaStreamConsumer(AsyncWebsocketConsumer):
    """Handle WebSocket connections between Twilio and OpenAI with database integration."""
    
    async def connect(self):
        """Accept WebSocket connection."""
        logger.info("=== WEBSOCKET CONNECTION STARTED ===")
        logger.info(f"Client connecting from: {self.scope['client']}")
        
        await self.accept()
        logger.info("WebSocket connection accepted successfully")
        
        # Initialize database helper
        self.db_helper = VoiceAgentDatabaseHelper()
        
        # Get call information for logging
        self.call_sid = None
        self.call_id = None
        self.call_start_time = datetime.now()
        
        # Conversation tracking for full transcript
        self.conversation_parts = []
        self.patient_messages = []
        self.assistant_messages = []
        
        # Audio recording
        self.patient_audio_data = []
        self.assistant_audio_data = []
        
        # Call termination control
        self.call_should_end = False
        self.last_activity_time = datetime.now()
        self.silence_threshold = 10  # seconds of silence before ending call
        
        logger.info(f"WebSocket session started at: {self.call_start_time}")
        
        # Initialize OpenAI connection
        await self.initialize_openai_connection()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")
        
        # Log call end if we have call_id
        if self.call_id:
            call_duration = int((datetime.now() - self.call_start_time).total_seconds())
            logger.info(f"Call duration: {call_duration} seconds")
            
            try:
                await self.update_call_end(self.call_sid, call_duration)
                logger.info("Call end logged in database")
            except Exception as e:
                logger.error(f"Error logging call end: {e}")
            
            # Save full conversation transcript
            if self.conversation_parts:
                try:
                    full_transcript = "\n".join(self.conversation_parts)
                    patient_transcript = "\n".join(self.patient_messages)
                    assistant_transcript = "\n".join(self.assistant_messages)
                    
                    # Determine scheduling outcome based on conversation
                    scheduling_outcome = "completed"  # Default
                    if any("scheduled" in part.lower() or "appointment" in part.lower() for part in self.conversation_parts):
                        scheduling_outcome = "scheduled"
                    
                    await self.save_full_transcript(
                        self.call_id, full_transcript, patient_transcript, 
                        assistant_transcript, None, scheduling_outcome
                    )
                    logger.info(f"Saved full transcript: {len(self.conversation_parts)} conversation parts")
                except Exception as e:
                    logger.error(f"Error saving transcript: {e}")
            
            # Save audio recordings
            try:
                await self.save_call_audio(self.call_id, self.patient_audio_data, self.assistant_audio_data)
                logger.info(f"Saved audio recordings for call {self.call_id}")
            except Exception as e:
                logger.error(f"Error saving audio: {e}")
    
    async def receive(self, text_data):
        """Receive message from WebSocket."""
        try:
            data = json.loads(text_data)
            event_type = data.get('event', 'unknown')
            logger.debug(f"Twilio event: {event_type}")
            
            if data['event'] == 'media' and hasattr(self, 'openai_ws') and self.openai_ws:
                logger.debug("Processing media data from Twilio")
                # Capture patient audio
                audio_payload = data['media']['payload']
                self.patient_audio_data.append(audio_payload)
                
                # Update activity time
                self.last_activity_time = datetime.now()
                
                audio_append = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_payload
                }
                await self.openai_ws.send(json.dumps(audio_append))
                logger.debug("Audio data sent to OpenAI")
                
            elif data['event'] == 'start':
                self.stream_sid = data['start']['streamSid']
                self.call_sid = data['start'].get('callSid')
                logger.info(f"Stream started - Stream SID: {self.stream_sid}, Call SID: {self.call_sid}")
                
                # Log call start if we have call_sid
                if self.call_sid and not self.call_id:
                    try:
                        logger.info(f"Fetching call details for SID: {self.call_sid}")
                        # Get patient phone from call
                        from twilio.rest import Client
                        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                        call = twilio_client.calls(self.call_sid).fetch()
                        patient_phone = call.to
                        logger.info(f"Call details - To: {patient_phone}, From: {call.from_}, Status: {call.status}")
                        
                        self.call_id = await self.log_call_start(self.call_sid, patient_phone)
                        logger.info(f"Call logged in database with ID: {self.call_id}")
                    except Exception as e:
                        logger.error(f"Error logging call start: {e}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
            elif data.get('event') == 'mark' and data.get('mark', {}).get('name') == 'speech_started':
                logger.info("User started speaking - sending interrupt to OpenAI")
                # Send interrupt signal to OpenAI
                interrupt_signal = {
                    "type": "interrupt"
                }
                await self.openai_ws.send(json.dumps(interrupt_signal))
                logger.debug("Interrupt signal sent to OpenAI")
                
            elif data.get('event') == 'stop':
                logger.info("Stream stopped event received")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Twilio message: {e}")
            logger.error(f"Raw message: {text_data}")
        except Exception as e:
            logger.error(f"Error processing Twilio message: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def initialize_openai_connection(self):
        """Initialize OpenAI WebSocket connection."""
        try:
            openai_logger.info("Attempting to connect to OpenAI Realtime API")
            openai_logger.info(f"OpenAI API URL: wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={settings.OPENAI_TEMPERATURE}")
            
            import websockets
            self.openai_ws = await websockets.connect(
                f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={settings.OPENAI_TEMPERATURE}",
                additional_headers=[
                    ("Authorization", f"Bearer {settings.OPENAI_API_KEY}")
                ]
            )
            
            openai_logger.info("OpenAI WebSocket connected successfully")
            openai_logger.info(f"OpenAI WebSocket state: {self.openai_ws.state.name}")
            
            # Send session update
            await self.send_session_update()
            openai_logger.info("Session update sent to OpenAI")
            
            # Start message processing
            asyncio.create_task(self.process_openai_messages())
            
        except Exception as e:
            openai_logger.error(f"Error connecting to OpenAI: {e}")
            openai_logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def send_session_update(self):
        """Send session update to OpenAI WebSocket."""
        openai_logger.info("Preparing session update for OpenAI")
        
        system_message = (
            "You are a professional Carematix healthcare assistant specialized in scheduling "
            "appointments with qualified nurses. You have access to a database to look up "
            "patient information, check nurse availability, and schedule appointments. "
            "\n\nIMPORTANT: Respond in the SAME LANGUAGE the patient is speaking. If they speak "
            "Hindi, respond in Hindi. If they speak English, respond in English. If they speak "
            "any other language, respond in that language. Always match their language preference."
            "\n\nPATIENT DATA CONTEXT:\n"
            "You already have access to the patient's information from our database. The patient data "
            "is provided to you at the beginning of each call. Do not ask for phone numbers or basic "
            "patient information - you already have this data. Focus on scheduling their nurse appointment."
            "\n\nNURSE MEETING SCHEDULING WORKFLOW:\n"
            "1. GREETING: Start with a warm, professional greeting using their name\n"
            "2. CONFIRM DETAILS: Use the patient data you already have\n"
            "3. FIND ASSIGNED NURSE: Use the nurse data you already have\n"
            "4. GET PREFERRED DATE/TIME: Ask what date and time they prefer for their nurse meeting\n"
            "5. CHECK NURSE AVAILABILITY: Verify the nurse's availability for the requested date and time\n"
            "6. SCHEDULE OR ALTERNATIVES: Either confirm the nurse meeting or suggest alternative dates/times\n"
            "7. CONFIRMATION: Provide clear confirmation details and next steps\n"
            "8. NOTIFICATIONS: Inform them that both they and their nurse will be notified\n"
            "\nCONVERSATION FLOW:\n"
            "- Start: 'Hello [Patient Name]! This is your Carematix healthcare assistant calling. I have your information from our system and can see you have an assigned nurse [Nurse Name]. What date and time would work best for your nurse meeting?' "
            "(or equivalent greeting in patient's language)\n"
            "- Patient info: You already have their name, phone, DOB, and medical conditions\n"
            "- Find nurse: You already have their assigned nurse information\n"
            "- Ask availability: 'What date and time would work best for your nurse meeting?'\n"
            "- Check availability: Send database request to check nurse availability\n"
            "- Schedule: Send database request to schedule appointment\n"
            "- Confirm: 'Perfect! I've scheduled your appointment with [nurse name] for [date] at [time].'\n"
            "\nKEY RESPONSIBILITIES:\n"
            "- You already have patient data - don't ask for phone numbers or basic info\n"
            "- Use the patient and nurse data provided in the context\n"
            "- Check real nurse availability before confirming\n"
            "- Schedule actual appointments in the database\n"
            "- Provide confirmation with real appointment details\n"
            "- Be empathetic, professional, and reassuring\n"
            "- End the conversation naturally when appointment is scheduled\n"
            "- Use phrases like 'Thank you', 'Have a great day', or 'Goodbye' to signal conversation end\n"
            "\nTIME PARSING:\n"
            "- Accept various time formats: '2 PM', '2:30 PM', '14:30', '2 o'clock'\n"
            "- Convert to 24-hour format for database queries\n"
            "- If time is unclear, ask for clarification\n"
            "\nDATABASE ACCESS:\n"
            "You can access the database by sending special messages in this format:\n"
            '{"type": "database_request", "action": "action_name", "params": {...}}\n\n'
            "Available actions:\n"
            "- get_patient_info: Get patient information by phone number (you already have this)\n"
            "- get_assigned_nurse: Get patient's assigned nurse (you already have this)\n"
            "- check_nurse_availability: Check if nurse is available at specific time\n"
            "- get_available_times: Get all available times for a nurse\n"
            "- schedule_appointment: Schedule an appointment\n"
            "\nDATABASE INTEGRATION:\n"
            "- You already have patient and nurse data - use it\n"
            "- Don't make assumptions about patient or nurse information\n"
            "- Verify availability before confirming appointments\n"
            "- Log all database interactions for audit purposes\n"
            "\nAlways maintain a caring, professional tone and prioritize the patient's health needs. "
            "Use the database to provide accurate, real-time information. "
            "\n\nIMPORTANT: All conversations are being transcribed and logged for quality assurance "
            "and follow-up care. Speak clearly and ensure all important details are captured."
        )
        
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
                "instructions": system_message,
            }
        }
        
        openai_logger.info(f'Sending session update with voice: {settings.OPENAI_VOICE}')
        openai_logger.debug(f'Session update content: {json.dumps(session_update, indent=2)}')
        
        try:
            await self.openai_ws.send(json.dumps(session_update))
            openai_logger.info("Session update sent successfully")
        except Exception as e:
            openai_logger.error(f"Error sending session update: {e}")
            raise
    
    async def process_openai_messages(self):
        """Process messages from OpenAI WebSocket."""
        try:
            async for message in self.openai_ws:
                try:
                    response = json.loads(message)
                    response_type = response.get('type', 'unknown')
                    openai_logger.debug(f"OpenAI Response: {response_type}")
                    
                    if response_type == 'session.updated':
                        openai_logger.info("Session updated successfully")
                        # Get patient and nurse data for this call
                        await self.setup_patient_nurse_context()
                        # Send initial greeting
                        await self.send_initial_greeting()
                        
                    elif response_type == 'response.output_audio.delta' and response.get('delta'):
                        # Audio from OpenAI
                        openai_logger.debug("Processing audio delta from OpenAI")
                        try:
                            # Capture assistant audio
                            self.assistant_audio_data.append(response['delta'])
                            
                            # Update activity time
                            self.last_activity_time = datetime.now()
                            
                            audio_delta = {
                                "event": "media",
                                "streamSid": getattr(self, 'stream_sid', ''),
                                "media": {
                                    "payload": response['delta']
                                }
                            }
                            await self.send(text_data=json.dumps(audio_delta))
                            openai_logger.debug("Audio delta sent to Twilio")
                        except Exception as e:
                            openai_logger.error(f"Error processing audio data: {e}")
                            openai_logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Log conversation events and capture transcripts
                    if self.call_id:
                        await self.process_conversation_events(response)
                        
                except json.JSONDecodeError as e:
                    openai_logger.error(f"Error parsing OpenAI message: {e}")
                    openai_logger.error(f"Raw message: {message}")
                except Exception as e:
                    openai_logger.error(f"Error processing OpenAI message: {e}")
                    openai_logger.error(f"Traceback: {traceback.format_exc()}")
                    
        except Exception as e:
            openai_logger.error(f"Error in process_openai_messages: {e}")
            openai_logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def setup_patient_nurse_context(self):
        """Set up patient and nurse context for the call."""
        if self.call_sid:
            try:
                # Get patient phone from call
                from twilio.rest import Client
                twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                call = twilio_client.calls(self.call_sid).fetch()
                patient_phone = call.to
                openai_logger.info(f"Call to patient: {patient_phone}")
                
                # Get patient data
                patient_data = await self.get_patient_by_phone(patient_phone)
                if patient_data:
                    openai_logger.info(f"Found patient: {patient_data['name']}")
                    # Store patient data in database helper
                    self.db_helper.current_patient_data = patient_data
                    self.db_helper.current_patient_id = patient_data['id']
                    self.db_helper.current_patient_phone = patient_phone
                    
                    # Get assigned nurse
                    nurse_data = await self.get_patient_assigned_nurse(patient_data['id'])
                    if nurse_data:
                        openai_logger.info(f"Found assigned nurse: {nurse_data['name']}")
                        self.db_helper.current_nurse = nurse_data
            except Exception as e:
                openai_logger.error(f"Error getting patient/nurse data: {e}")
    
    async def send_initial_greeting(self):
        """Send initial greeting to start the conversation."""
        openai_logger.info("Sending initial greeting to start conversation")
        
        if hasattr(self.db_helper, 'current_patient_data') and self.db_helper.current_patient_data:
            patient_data = self.db_helper.current_patient_data
            nurse_data = getattr(self.db_helper, 'current_nurse', None)
            greeting_text = f"Hello {patient_data['name']}! This is your Carematix healthcare assistant. I'm calling to schedule your nurse meeting with {nurse_data['name'] if nurse_data else 'your assigned nurse'}. What date and time are you available for your nurse meeting?"
        else:
            greeting_text = "Hello! This is your Carematix healthcare assistant. I'm calling to schedule your nurse meeting. What date and time are you available for your nurse meeting?"
        
        greeting_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "input_text",
                        "text": greeting_text
                    }
                ]
            }
        }
        await self.openai_ws.send(json.dumps(greeting_message))
        openai_logger.info("Initial greeting sent to OpenAI")
    
    async def process_conversation_events(self, response):
        """Process conversation events and capture transcripts."""
        response_type = response.get('type', 'unknown')
        
        if response_type == 'conversation.item.input_audio_buffer.speech_started':
            openai_logger.info("Patient started speaking")
            await self.log_conversation(self.call_id, 'patient', '[Patient started speaking]', 'action', None)
            
        elif response_type == 'conversation.item.output_audio.done':
            openai_logger.info("Assistant audio response completed")
            await self.log_conversation(self.call_id, 'assistant', '[Assistant audio response completed]', 'action', None)
            
        elif response_type == 'conversation.item.input_audio_buffer.speech_stopped':
            openai_logger.info("Patient finished speaking")
            await self.log_conversation(self.call_id, 'patient', '[Patient finished speaking]', 'action', None)
            
        # Capture conversation content for transcript
        elif response_type == 'conversation.item.input_audio_buffer.committed':
            # Patient speech was processed
            openai_logger.info("Processing patient speech transcript")
            if 'transcript' in response.get('input_audio_buffer', {}):
                transcript_text = response['input_audio_buffer']['transcript']
                if transcript_text:
                    openai_logger.info(f"Patient transcript: {transcript_text}")
                    self.conversation_parts.append(f"Patient: {transcript_text}")
                    self.patient_messages.append(transcript_text)
                    await self.log_conversation(self.call_id, 'patient', transcript_text, 'transcript', None)
                    
                    # Check for conversation end signals
                    if self.check_conversation_end(transcript_text):
                        openai_logger.info("Conversation end detected from patient speech")
                        self.call_should_end = True
                        await self.end_call_gracefully()
                        return
                    
                    # Check for database requests in patient speech
                    await self.process_database_requests(transcript_text)
        
        elif response_type == 'conversation.item.output_audio.done':
            # Assistant response completed
            openai_logger.info("Processing assistant response transcript")
            if 'transcript' in response.get('output_audio', {}):
                transcript_text = response['output_audio']['transcript']
                if transcript_text:
                    openai_logger.info(f"Assistant transcript: {transcript_text}")
                    self.conversation_parts.append(f"Assistant: {transcript_text}")
                    self.assistant_messages.append(transcript_text)
                    await self.log_conversation(self.call_id, 'assistant', transcript_text, 'transcript', None)
    
    def check_conversation_end(self, transcript_text):
        """Check if the conversation should end based on transcript content"""
        end_phrases = [
            "goodbye", "bye", "thank you", "thanks", "that's all", "that's it",
            "i'm done", "i'm finished", "end call", "hang up", "disconnect",
            "see you later", "talk to you later", "have a good day", "take care",
            "appointment scheduled", "meeting scheduled", "confirmed", "done",
            "okay bye", "ok bye", "alright bye", "sounds good", "perfect"
        ]
        
        transcript_lower = transcript_text.lower().strip()
        
        # Check for exact matches
        for phrase in end_phrases:
            if phrase in transcript_lower:
                return True
        
        # Check for appointment confirmation patterns
        if any(word in transcript_lower for word in ["scheduled", "confirmed", "booked", "set"]):
            if any(word in transcript_lower for word in ["appointment", "meeting", "call"]):
                return True
        
        return False
    
    async def end_call_gracefully(self):
        """End the call gracefully with a closing message"""
        try:
            # Send closing message
            closing_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Thank you for your time! Your appointment has been scheduled and you'll receive a confirmation shortly. Have a great day!"
                        }
                    ]
                }
            }
            await self.openai_ws.send(json.dumps(closing_message))
            
            # Wait a moment for the message to be processed
            await asyncio.sleep(2)
            
            # Send hangup command to Twilio
            hangup_message = {
                "event": "hangup",
                "streamSid": getattr(self, 'stream_sid', '')
            }
            try:
                await self.send(text_data=json.dumps(hangup_message))
                logger.info("Hangup command sent to Twilio")
            except Exception as e:
                logger.error(f"Error sending hangup command: {e}")
            
            logger.info(f"Call {self.call_id} ended gracefully")
            
        except Exception as e:
            logger.error(f"Error ending call gracefully: {e}")
    
    async def process_database_requests(self, transcript_text):
        """Process database requests from voice agent transcript"""
        try:
            import re
            # Look for phone numbers in the transcript
            phone_match = re.search(r'\+?[1-9]\d{1,14}', transcript_text)
            
            if phone_match:
                phone_number = phone_match.group()
                openai_logger.info(f"Found phone number in transcript: {phone_number}")
                
                # Get patient info from database
                patient_info = await self.db_helper.get_patient_info(phone_number)
                
                if patient_info.get('success'):
                    # Get assigned nurse
                    nurse_info = await self.db_helper.get_assigned_nurse(patient_info['patient']['id'])
                    
                    # Send response back to OpenAI
                    response_message = {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": f"{patient_info['message']} {nurse_info['message']}"
                                }
                            ]
                        }
                    }
                    await self.openai_ws.send(json.dumps(response_message))
                    openai_logger.info("Sent database response to OpenAI")
                    
                    # Log the database interaction
                    await self.log_conversation(self.call_id, 'assistant', f"Database lookup: {patient_info['message']}", 'database', None)
                    
        except Exception as e:
            openai_logger.error(f"Error processing database request: {e}")
    
    async def save_call_audio(self, call_id, patient_audio_data, assistant_audio_data):
        """Save audio recordings for a call"""
        try:
            # Create recordings directory
            os.makedirs("recordings", exist_ok=True)
            
            # Save patient audio
            if patient_audio_data:
                patient_audio_file = f"recordings/call_{call_id}_patient.wav"
                with open(patient_audio_file, 'wb') as f:
                    for chunk in patient_audio_data:
                        f.write(base64.b64decode(chunk))
                logger.info(f"Saved patient audio: {patient_audio_file}")
            
            # Save assistant audio
            if assistant_audio_data:
                assistant_audio_file = f"recordings/call_{call_id}_assistant.wav"
                with open(assistant_audio_file, 'wb') as f:
                    for chunk in assistant_audio_data:
                        f.write(base64.b64decode(chunk))
                logger.info(f"Saved assistant audio: {assistant_audio_file}")
                
        except Exception as e:
            logger.error(f"Error saving audio files: {e}")
    
    # Database helper methods
    @database_sync_to_async
    def log_call_start(self, call_sid, patient_phone):
        """Log call start in database."""
        try:
            # Try to find patient by phone
            patient = Patient.objects.filter(phone=patient_phone).first()
            patient_id = patient.id if patient else None
            
            call = Call.objects.create(
                call_sid=call_sid,
                patient_phone=patient_phone,
                patient_id=patient_id,
                call_direction="outbound",
                call_status="initiated"
            )
            return call.id
        except Exception as e:
            logger.error(f"Error logging call start: {e}")
            return None
    
    @database_sync_to_async
    def update_call_end(self, call_sid, duration):
        """Update call end in database."""
        try:
            Call.objects.filter(call_sid=call_sid).update(
                call_status="completed",
                call_duration=duration,
                end_time=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error updating call end: {e}")
    
    @database_sync_to_async
    def log_conversation(self, call_id, speaker, message, message_type, intent):
        """Log conversation in database."""
        try:
            ConversationLog.objects.create(
                call_id=call_id,
                speaker=speaker,
                message_text=message,
                message_type=message_type,
                intent=intent
            )
        except Exception as e:
            logger.error(f"Error logging conversation: {e}")
    
    @database_sync_to_async
    def save_full_transcript(self, call_id, full_transcript, patient_transcript, assistant_transcript, appointment_summary, scheduling_outcome):
        """Save full transcript in database."""
        try:
            CallTranscript.objects.update_or_create(
                call_id=call_id,
                defaults={
                    'full_transcript': full_transcript,
                    'patient_transcript': patient_transcript,
                    'assistant_transcript': assistant_transcript,
                    'appointment_summary': appointment_summary,
                    'scheduling_outcome': scheduling_outcome
                }
            )
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
    
    @database_sync_to_async
    def get_patient_by_phone(self, phone):
        """Get patient by phone number."""
        try:
            patient = Patient.objects.get(phone=phone)
            return {
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone,
                'email': patient.email,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'medical_conditions': patient.medical_conditions
            }
        except Patient.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_patient_assigned_nurse(self, patient_id):
        """Get patient's assigned nurse."""
        try:
            assignment = PatientNurseAssignment.objects.filter(
                patient_id=patient_id,
                assignment_date=datetime.now().date(),
                is_primary=True
            ).select_related('nurse').first()
            
            if assignment:
                return {
                    'id': assignment.nurse.id,
                    'name': assignment.nurse.name,
                    'specialization': assignment.nurse.specialization,
                    'phone': assignment.nurse.phone,
                    'email': assignment.nurse.email
                }
            return None
        except Exception as e:
            logger.error(f"Error getting assigned nurse: {e}")
            return None

