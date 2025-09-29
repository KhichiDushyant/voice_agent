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
from datetime import datetime, timedelta
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
        await self.accept()
        logger.info(f"WebSocket connected from: {self.scope['client']}")
        
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
        
        # Initialize context variables
        self.patient_name = 'Unknown Patient'
        self.patient_phone = 'Unknown Phone'
        self.nurse_name = 'No assigned nurse'
        self.nurse_specialization = 'General'
        self.current_date = 'Unknown Date'
        self.current_time = 'Unknown Time'
        
        # Call termination control
        self.call_should_end = False
        self.call_ending = False  # Flag to prevent duplicate error handling
        self.last_activity_time = datetime.now()
        self.silence_threshold = 8  # seconds of silence before ending call
        self.max_call_duration = 120  # 5 minutes maximum call duration
        
        # Response state management
        self.active_response_id = None
        self.response_in_progress = False
        
        # Initialize OpenAI connection
        await self.initialize_openai_connection()
        
        # Start call monitoring task
        asyncio.create_task(self.monitor_call_timeout())
    
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
            
            # Save comprehensive conversation transcript
            logger.info(f"Saving transcript - Parts: {len(self.conversation_parts)}, Patient: {len(self.patient_messages)}, Assistant: {len(self.assistant_messages)}")
            
            if self.conversation_parts:
                try:
                    # Create detailed transcript with timestamps and context
                    
                    # Build comprehensive transcript header
                    transcript_header = f"""
===============================================
CAREMATIX CALL TRANSCRIPT
===============================================
Call ID: {self.call_id}
Call SID: {self.call_sid}
Patient: {getattr(self, 'patient_name', 'Unknown')} ({getattr(self, 'patient_phone', 'Unknown')})
Nurse: {getattr(self, 'nurse_name', 'Unknown')} ({getattr(self, 'nurse_specialization', 'Unknown')})
Call Start: {self.call_start_time.strftime('%Y-%m-%d %H:%M:%S')}
Call End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Call Duration: {call_duration} seconds
Current Date: {getattr(self, 'current_date', 'Unknown')}
Current Time: {getattr(self, 'current_time', 'Unknown')}
===============================================

CONVERSATION TRANSCRIPT:
"""
                    
                    # Build full transcript with timestamps
                    timestamped_parts = []
                    for i, part in enumerate(self.conversation_parts):
                        timestamp = self.call_start_time + timedelta(seconds=i*2)  # Approximate timestamp
                        timestamped_parts.append(f"[{timestamp.strftime('%H:%M:%S')}] {part}")
                    
                    full_transcript = transcript_header + "\n".join(timestamped_parts)
                    patient_transcript = "\n".join([f"[{self.call_start_time + timedelta(seconds=i*2):%H:%M:%S}] {msg}" for i, msg in enumerate(self.patient_messages)])
                    assistant_transcript = "\n".join([f"[{self.call_start_time + timedelta(seconds=i*2):%H:%M:%S}] {msg}" for i, msg in enumerate(self.assistant_messages)])
                    
                    # Determine scheduling outcome based on conversation content
                    scheduling_outcome = "completed"  # Default
                    appointment_keywords = ["scheduled", "appointment", "meeting", "confirmed", "booked", "set up"]
                    if any(keyword in " ".join(self.conversation_parts).lower() for keyword in appointment_keywords):
                        scheduling_outcome = "scheduled"
                        logger.info("✅ Appointment scheduling detected in transcript")
                    
                    # Create appointment summary if scheduling occurred
                    appointment_summary = None
                    if scheduling_outcome == "scheduled":
                        appointment_summary = f"Appointment scheduled for {getattr(self, 'patient_name', 'patient')} with {getattr(self, 'nurse_name', 'nurse')} on {getattr(self, 'current_date', 'unknown date')}"
                    
                    # Save comprehensive transcript
                    await self.save_full_transcript(
                        self.call_id, full_transcript, patient_transcript, 
                        assistant_transcript, appointment_summary, scheduling_outcome
                    )
                    
                    logger.info(f"Transcript saved - Call {self.call_id}, Duration: {call_duration}s, Outcome: {scheduling_outcome}")
                    
                    # Print full transcript to console
                    print("\n" + "="*80)
                    print("FULL CALL TRANSCRIPT")
                    print("="*80)
                    print(full_transcript)
                    print("="*80)
                    print("END OF TRANSCRIPT")
                    print("="*80 + "\n")
                    
                except Exception as e:
                    logger.error(f"Error saving transcript: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                # Fallback: Save basic transcript even if no conversation parts
                logger.warning("No conversation parts found, saving basic transcript")
                try:
                    call_duration = int((datetime.now() - self.call_start_time).total_seconds())
                    basic_transcript = f"""
===============================================
CAREMATIX CALL TRANSCRIPT (BASIC)
===============================================
Call ID: {self.call_id}
Call SID: {self.call_sid}
Patient: {getattr(self, 'patient_name', 'Unknown')} ({getattr(self, 'patient_phone', 'Unknown')})
Nurse: {getattr(self, 'nurse_name', 'Unknown')} ({getattr(self, 'nurse_specialization', 'Unknown')})
Call Start: {self.call_start_time.strftime('%Y-%m-%d %H:%M:%S')}
Call End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Call Duration: {call_duration} seconds
Current Date: {getattr(self, 'current_date', 'Unknown')}
Current Time: {getattr(self, 'current_time', 'Unknown')}
===============================================

NOTE: No conversation parts were captured during this call.
This may indicate an issue with the WebSocket connection or transcript processing.
"""
                    
                    await self.save_full_transcript(
                        self.call_id, basic_transcript, "No patient messages captured", 
                        "No assistant messages captured", "No appointment scheduled", "failed"
                    )
                    logger.info("Basic transcript saved as fallback")
                    
                    # Print basic transcript to console
                    print("\n" + "="*80)
                    print("BASIC CALL TRANSCRIPT (FALLBACK)")
                    print("="*80)
                    print(basic_transcript)
                    print("="*80)
                    print("END OF BASIC TRANSCRIPT")
                    print("="*80 + "\n")
                    
                except Exception as e:
                    logger.error(f"Error saving basic transcript: {e}")
            
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
            if data['event'] == 'media' and hasattr(self, 'openai_ws') and self.openai_ws:
                # Capture patient audio
                audio_payload = data['media']['payload']
                self.patient_audio_data.append(audio_payload)
                
                # Update activity time
                self.last_activity_time = datetime.now()
                
                # Send audio to OpenAI using the correct format
                audio_message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_payload
                }
                await self.openai_ws.send(json.dumps(audio_message))
                
            elif data['event'] == 'start':
                self.stream_sid = data['start']['streamSid']
                self.call_sid = data['start'].get('callSid')
                
                # Extract stream parameters for context
                custom_params = data['start'].get('customParameters', {})
                
                self.patient_name = custom_params.get('patient_name', 'Unknown Patient')
                self.patient_phone = custom_params.get('patient_phone', 'Unknown Phone')
                self.nurse_name = custom_params.get('nurse_name', 'No assigned nurse')
                self.nurse_specialization = custom_params.get('nurse_specialization', 'General')
                self.call_id = custom_params.get('call_id', None)
                self.current_date = custom_params.get('current_date', 'Unknown Date')
                self.current_time = custom_params.get('current_time', 'Unknown Time')
                
                logger.info(f"Call started - Patient: {self.patient_name}, Nurse: {self.nurse_name}")
                
                # Log call start if we have call_sid
                if self.call_sid and not self.call_id:
                    try:
                        # Get patient phone from call
                        from twilio.rest import Client
                        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                        call = twilio_client.calls(self.call_sid).fetch()
                        patient_phone = call.to
                        
                        self.call_id = await self.log_call_start(self.call_sid, patient_phone)
                        
                        # ALWAYS get patient info from database since we're using our UI
                        patient_info = await self.get_patient_by_phone(patient_phone)
                        if patient_info:
                            self.patient_name = patient_info['name']
                            self.patient_phone = patient_info['phone']
                            
                            # Get assigned nurse
                            nurse_info = await self.get_patient_assigned_nurse(patient_info['id'])
                            if nurse_info:
                                self.nurse_name = nurse_info['name']
                                self.nurse_specialization = nurse_info['specialization']
                            
                            logger.info(f"Patient context loaded: {self.patient_name} -> {self.nurse_name}")
                        else:
                            logger.error(f"Patient not found for phone {patient_phone} - ending call")
                            await self.close()
                            return
                        
                        # OpenAI session will be started when we receive session.created
                        logger.info("Patient context loaded - waiting for OpenAI session creation")
                        
                    except Exception as e:
                        logger.error(f"Error logging call start: {e}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        # End the call if we can't get patient info
                        await self.close()
                        return
                
            elif data.get('event') == 'mark' and data.get('mark', {}).get('name') == 'speech_started':
                logger.info("User started speaking - checking if interrupt is needed")
                # Only send interrupt if there's an active response to interrupt
                if self.response_in_progress:
                    logger.info("Response in progress - sending interrupt to OpenAI")
                    interrupt_signal = {
                        "type": "interrupt"
                    }
                    await self.openai_ws.send(json.dumps(interrupt_signal))
                    logger.debug("Interrupt signal sent to OpenAI")
                else:
                    logger.info("No active response to interrupt - skipping interrupt signal")
                
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
            openai_logger.info("Connecting to OpenAI Realtime API")
            
            import websockets
            self.openai_ws = await websockets.connect(
                f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={settings.OPENAI_TEMPERATURE}",
                additional_headers=[
                    ("Authorization", f"Bearer {settings.OPENAI_API_KEY}")
                ]
            )
            
            openai_logger.info("OpenAI WebSocket connected successfully")
            openai_logger.info(f"WebSocket state: {self.openai_ws.state.name}")
            
            # Reset response state
            self.response_in_progress = False
            self.active_response_id = None
            
            # Start message processing task
            asyncio.create_task(self.process_openai_messages())
            
        except Exception as e:
            openai_logger.error(f"Error connecting to OpenAI: {e}")
            openai_logger.error(f"Traceback: {traceback.format_exc()}")
            # Set to None so we don't try to use it
            self.openai_ws = None
            
            # Reset response state on connection error
            self.response_in_progress = False
            self.active_response_id = None
            
            # Cut the call on OpenAI connection error
            if not self.call_ending:
                self.call_ending = True
                openai_logger.error("OpenAI connection failed - ending call")
                self.call_should_end = True
                await self.end_call_gracefully()
    
    async def send_session_update(self):
        """Send session update to OpenAI WebSocket."""
        if not hasattr(self, 'openai_ws') or not self.openai_ws:
            openai_logger.error("OpenAI WebSocket not connected - cannot send session update")
            return
            
        openai_logger.info("Preparing session update for OpenAI")
        
        # Set up patient and nurse context BEFORE generating availability
        await self.setup_patient_nurse_context()
        
        # Get current context from stream parameters
        patient_name = getattr(self, 'patient_name', 'Unknown Patient')
        patient_phone = getattr(self, 'patient_phone', 'Unknown Phone')
        nurse_name = getattr(self, 'nurse_name', 'No assigned nurse')
        nurse_specialization = getattr(self, 'nurse_specialization', 'General')
        current_date = getattr(self, 'current_date', 'Unknown Date')
        current_time = getattr(self, 'current_time', 'Unknown Time')
        
        # Get nurse availability for the next 7 days
        availability_info = await self.get_nurse_availability_timeline()
        
        # Get additional nurse context
        print(f"DEBUG: Calling get_nurse_context_info")
        nurse_context = await self.get_nurse_context_info()
        print(f"DEBUG: get_nurse_context_info result: {nurse_context[:100] if nurse_context else 'None'}...")
        
        system_message = (
    f"You're calling {patient_name} from Carematrix to help schedule their nurse appointment. "
    f"You're friendly, natural, and genuinely helpful - like talking to a caring neighbor.\n\n"
    
    f"PATIENT CONTEXT:\n"
    f"- Name: {patient_name}\n"
    f"- Phone: {patient_phone}\n" 
    f"- Nurse: {nurse_name} ({nurse_specialization})\n"
    f"- Today: {current_date} at {current_time}\n\n"
    
    f"NURSE SCHEDULE & AVAILABILITY:\n"
    f"{availability_info}\n\n"
    
    f"{nurse_context}\n"
    
    "CONVERSATION STYLE:\n"
    "- Sound like a real person having a genuine conversation\n"
    "- Use contractions (I'm, you're, we'll) and natural speech patterns\n"
    "- Include brief, natural pauses: 'Hi there... how are you doing today?'\n"
    "- Respond to what they actually say, don't stick rigidly to a script\n"
    "- Show empathy: 'I understand' or 'That makes sense'\n"
    "- Ask open questions: 'What would work better for you?' vs 'Does Tuesday work?'\n"
    "- Match their communication style and pace\n\n"
    
    "OPENING APPROACH:\n"
    f"Start warmly: 'Hi {patient_name}, this is [your name] calling from Carematrix about your upcoming nurse appointment with {nurse_name}. How's your day going?' "
    "Then gauge their availability to chat before diving into scheduling.\n\n"
    
    "CONVERSATION FLOW (be flexible!):\n"
    "1. Warm greeting + brief check-in on how they're doing\n"
    "2. Confirm they have a moment to chat about scheduling\n"
    "3. Ask what days generally work well for them (don't assume)\n"
    "4. When they share preferences, immediately offer specific available times from the schedule above\n"
    "5. If they request a specific time, check it against the schedule and confirm or offer alternatives\n"
    "6. If they need to check something, offer to wait or call back\n"
    "7. Confirm details and end warmly\n\n"
    
    "HANDLE RESPONSES NATURALLY:\n"
    "- If busy: 'No problem at all - when would be better to call back?'\n"
    "- If flexible: 'Great! I have a few good options...' then offer specific times from the schedule\n"
    "- If specific day: 'Perfect! For [day], {nurse_name} has these times available: [list specific times from schedule]'\n"
    "- If needs to check: 'Of course! Should I hold on or would you prefer I call back?'\n"
    "- If hesitant: 'I understand - is there anything specific you'd like to know about the appointment?'\n\n"
    
    "IMPORTANT - YOU ALREADY KNOW THE SCHEDULE:\n"
    "- You have the complete availability schedule above - use it directly\n"
    "- Never say 'let me check' or 'I need to look that up'\n"
    "- Always offer specific times from the schedule when asked\n"
    "- Be confident and direct about available times\n\n"
    
    "EXAMPLE RESPONSES:\n"
    "- If patient asks about today: 'For today, {nurse_name} has these times available: [list today's times from schedule]'\n"
    "- If patient asks about tomorrow: 'For tomorrow, {nurse_name} has these times available: [list tomorrow's times from schedule]'\n"
    "- If patient asks about a specific day: 'For [day], {nurse_name} has these times available: [list that day's times from schedule]'\n"
    "- Always be specific and confident - you already have all the information!\n\n"
    
    "HANDLING DIRECT TIME REQUESTS:\n"
    "- If patient says 'today 9 AM': Check if 9 AM is in today's schedule\n"
    "  * If available: 'Perfect! 9 AM today works great. Let me confirm that appointment for you.'\n"
    "  * If not available: 'I don't have 9 AM available today, but I do have [list closest available times]'\n"
    "- If patient says 'tomorrow 2 PM': Check if 2 PM is in tomorrow's schedule\n"
    "  * If available: 'Great! 2 PM tomorrow is available. Let me book that for you.'\n"
    "  * If not available: 'I don't have 2 PM tomorrow, but I do have [list available times for tomorrow]'\n"
    "- Always check the exact time against the schedule before confirming\n"
    "- When confirming an appointment, be enthusiastic: 'Excellent! I've got you down for [day] at [time] with {nurse_name}'\n"
    "- If the time isn't available, be helpful: 'I don't have [requested time] available, but I do have [list 2-3 closest times] - would any of these work for you?'\n\n"
    
    "REMEMBER:\n"
    "- Real conversations aren't perfectly linear - follow their lead\n"
    "- If they ask questions, answer them naturally before returning to scheduling\n"
    "- Use positive language: 'What would work best?' instead of 'When can't you do?'\n"
    "- End positively regardless of outcome\n"
    "- Keep it conversational, not transactional"
)

        # Debug: Print the complete system message
        print("\n" + "="*100)
        print("COMPLETE SYSTEM MESSAGE BEING SENT TO OPENAI:")
        print("="*100)
        print(system_message)
        print("="*100)
        print("END OF SYSTEM MESSAGE")
        print("="*100 + "\n")
        
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
                "instructions": system_message
            }
        }
        
        try:
            # Debug: Print the complete system message
            print("\n" + "="*80)
            print("SYSTEM MESSAGE BEING SENT TO AGENT:")
            print("="*80)
            print(system_message)
            print("="*80)
            print("END OF SYSTEM MESSAGE")
            print("="*80 + "\n")
            
            await self.openai_ws.send(json.dumps(session_update))
            openai_logger.info("Session update sent successfully")
            openai_logger.info("Waiting for session.updated response...")
        except Exception as e:
            openai_logger.error(f"Error sending session update: {e}")
            openai_logger.error(f"WebSocket state: {self.openai_ws.state.name if self.openai_ws else 'None'}")
            
            # Cut the call on session update error
            if not self.call_ending:
                self.call_ending = True
                openai_logger.error("Session update failed - ending call")
                self.call_should_end = True
                await self.end_call_gracefully()
            raise
    
    async def process_openai_messages(self):
        """Process messages from OpenAI WebSocket."""
        if not hasattr(self, 'openai_ws') or not self.openai_ws:
            openai_logger.error("OpenAI WebSocket not connected - cannot process messages")
            return
            
        try:
            async for message in self.openai_ws:
                try:
                    response = json.loads(message)
                    response_type = response.get('type', 'unknown')
                    openai_logger.debug(f"OpenAI Response: {response_type}")
                    
                    if response_type == 'session.created':
                        openai_logger.info("Session created - sending session update")
                        try:
                            await self.send_session_update()
                        except Exception as e:
                            openai_logger.error(f"Error sending session update: {e}")
                    elif response_type == 'session.updated':
                        openai_logger.info("Session updated successfully")
                        # Patient and nurse context already set up before session update
                        # Don't send greeting immediately - wait for patient to speak first
                        # This prevents the conversation_already_has_active_response error
                        openai_logger.info("Session ready - waiting for patient to speak first")
                    elif response_type == 'error':
                        error_info = response.get('error', {})
                        openai_logger.error(f"OpenAI error: {error_info}")
                        
                        # Reset response state on error
                        self.response_in_progress = False
                        self.active_response_id = None
                        
                        # Handle specific error types
                        error_code = error_info.get('code', '')
                        if error_code == 'conversation_already_has_active_response':
                            openai_logger.warning("Response already active - waiting for completion")
                            # Don't end the call, just wait for the current response to finish
                            return
                        elif error_code in ['invalid_request_error', 'rate_limit_exceeded', 'insufficient_quota']:
                            # These are serious errors that should end the call
                            if not self.call_ending:
                                self.call_ending = True
                                openai_logger.error(f"Serious OpenAI error ({error_code}) - ending call")
                                self.call_should_end = True
                                await self.end_call_gracefully()
                            return
                        else:
                            # For other errors, log but don't end the call immediately
                            openai_logger.warning(f"OpenAI error ({error_code}) - continuing call")
                            return
                    elif response_type == 'response.created':
                        # Response started
                        self.response_in_progress = True
                        self.active_response_id = response.get('response', {}).get('id')
                        openai_logger.info(f"Response started: {self.active_response_id}")
                        
                    elif response_type == 'response.output_audio.delta' and response.get('delta'):
                        # Process audio output from OpenAI
                        try:
                            # Capture assistant audio for recording
                            self.assistant_audio_data.append(response['delta'])
                            
                            # Update activity time
                            self.last_activity_time = datetime.now()
                            
                            # Send audio to Twilio in the correct format
                            twilio_audio = {
                                "event": "media",
                                "streamSid": getattr(self, 'stream_sid', ''),
                                "media": {
                                    "payload": response['delta']
                                }
                            }
                            await self.send(text_data=json.dumps(twilio_audio))
                            
                        except Exception as e:
                            openai_logger.error(f"Error processing audio output: {e}")
                            openai_logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    elif response_type == 'response.done':
                        # Response completed
                        self.response_in_progress = False
                        self.active_response_id = None
                        openai_logger.info("Response completed")
                        
                        # No pending greeting logic needed - assistant will respond naturally
                    
                    elif response_type == 'response.output_text.delta' and response.get('delta'):
                        # Process text output from OpenAI
                        try:
                            # Print text output to console for debugging
                            print(f"\nASSISTANT TEXT: {response['delta']}", end='', flush=True)
                            
                            # Update activity time
                            self.last_activity_time = datetime.now()
                            
                        except Exception as e:
                            openai_logger.error(f"Error processing text output: {e}")
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
            
            # Reset response state on error
            self.response_in_progress = False
            self.active_response_id = None
            
            # Cut the call on message processing error
            if not self.call_ending:
                self.call_ending = True
                openai_logger.error("Message processing failed - ending call")
                self.call_should_end = True
                await self.end_call_gracefully()
    
    async def get_nurse_availability_timeline(self):
        """Get nurse availability timeline for the next 7 days from database."""
        try:
            # Ensure at least one nurse exists in the database
            await self.ensure_nurse_exists()
            
            # Get nurse ID from context
            nurse_id = getattr(self, 'nurse_id', None)
            nurse_name = getattr(self, 'nurse_name', 'Nurse')
            
            print(f"\nDEBUG: Getting availability for nurse_id={nurse_id}, nurse_name={nurse_name}")
            
            if not nurse_id:
                print("DEBUG: No nurse_id found, trying to create default nurse assignment...")
                # Try to get patient ID and create default assignment
                patient_id = getattr(self.db_helper, 'current_patient_id', None)
                if patient_id:
                    success = await self.create_default_nurse_assignment(patient_id)
                    if success:
                        nurse_id = getattr(self, 'nurse_id', None)
                        nurse_name = getattr(self, 'nurse_name', 'Nurse')
                        print(f"DEBUG: Created default nurse assignment: nurse_id={nurse_id}, nurse_name={nurse_name}")
                    else:
                        print("DEBUG: Failed to create default nurse assignment")
                        return "Nurse availability not available - please check with our system."
                else:
                    print("DEBUG: No patient_id available to create nurse assignment")
                    return "Nurse availability not available - please check with our system."
            
            # Ensure nurse has availability data
            print(f"DEBUG: Calling ensure_nurse_availability_exists for nurse {nurse_id}")
            result = await self.ensure_nurse_availability_exists(nurse_id)
            print(f"DEBUG: ensure_nurse_availability_exists result: {result}")
            
            # Get comprehensive availability data from database
            print(f"DEBUG: Calling get_comprehensive_nurse_availability for nurse {nurse_id}")
            availability_data = await self.get_comprehensive_nurse_availability(nurse_id)
            print(f"DEBUG: get_comprehensive_nurse_availability result: {availability_data is not None}")
            
            # Format the data for OpenAI
            availability_text = self.format_availability_for_openai(nurse_name, availability_data)
            
            # Debug: Print the availability info
            print("\n" + "="*80)
            print("COMPREHENSIVE NURSE AVAILABILITY FOR OPENAI:")
            print("="*80)
            print(availability_text)
            print("="*80)
            print("END OF AVAILABILITY INFO")
            print("="*80 + "\n")
            
            return availability_text
            
        except Exception as e:
            openai_logger.error(f"Error getting nurse availability timeline: {e}")
            import traceback
            traceback.print_exc()
            return "Nurse availability not available - please check with our system."
    
    @database_sync_to_async
    def get_comprehensive_nurse_availability(self, nurse_id):
        """Get comprehensive availability data from database for a nurse."""
        try:
            from datetime import datetime, timedelta
            from .models import NurseAvailability, NurseAvailabilityOverride, Appointment
            
            # Get regular availability schedule
            regular_availability = {}
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                avail = NurseAvailability.objects.filter(
                    nurse_id=nurse_id,
                    day_of_week=day,
                    is_available=True
                ).first()
                
                if avail:
                    regular_availability[day] = {
                        'start_time': avail.start_time,
                        'end_time': avail.end_time,
                        'is_available': True
                    }
                else:
                    regular_availability[day] = {
                        'is_available': False
                    }
            
            # Get overrides for next 7 days
            today = datetime.now().date()
            overrides = {}
            for i in range(7):
                check_date = today + timedelta(days=i)
                override = NurseAvailabilityOverride.objects.filter(
                    nurse_id=nurse_id,
                    override_date=check_date
                ).first()
                
                if override:
                    overrides[check_date] = {
                        'is_available': override.is_available,
                        'start_time': override.start_time,
                        'end_time': override.end_time
                    }
            
            # Get existing appointments for next 7 days
            appointments = {}
            for i in range(7):
                check_date = today + timedelta(days=i)
                day_appointments = Appointment.objects.filter(
                    nurse_id=nurse_id,
                    appointment_date=check_date,
                    status__in=['scheduled', 'confirmed']
                ).values('appointment_time', 'duration_minutes')
                
                appointments[check_date] = list(day_appointments)
            
            return {
                'regular_availability': regular_availability,
                'overrides': overrides,
                'appointments': appointments,
                'nurse_id': nurse_id
            }
            
        except Exception as e:
            print(f"DEBUG: Error getting comprehensive availability: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def format_availability_for_openai(self, nurse_name, availability_data):
        """Format availability data for OpenAI consumption."""
        if not availability_data:
            return f"Nurse {nurse_name} availability not available - please check with our system."
        
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        availability_text = f"COMPLETE SCHEDULE FOR {nurse_name} - USE THESE EXACT TIMES:\n\n"
        
        # Add regular schedule
        availability_text += "REGULAR WEEKLY SCHEDULE:\n"
        for day, schedule in availability_data['regular_availability'].items():
            if schedule['is_available']:
                availability_text += f"{day}: {schedule['start_time'].strftime('%H:%M')} - {schedule['end_time'].strftime('%H:%M')}\n"
            else:
                availability_text += f"{day}: Not available\n"
        
        availability_text += "\nNEXT 7 DAYS AVAILABILITY:\n"
        
        # Generate availability for next 7 days
        for i in range(7):
            check_date = today + timedelta(days=i)
            day_name = check_date.strftime('%A')
            date_str = check_date.strftime('%Y-%m-%d')
            
            # Check if there's an override for this date
            if check_date in availability_data['overrides']:
                override = availability_data['overrides'][check_date]
                if not override['is_available']:
                    availability_text += f"{day_name} ({date_str}): Not available (override)\n"
                    continue
                elif override['start_time'] and override['end_time']:
                    # Use override times
                    start_time = override['start_time']
                    end_time = override['end_time']
                else:
                    availability_text += f"{day_name} ({date_str}): Not available (override)\n"
                    continue
            else:
                # Use regular schedule
                regular_schedule = availability_data['regular_availability'][day_name]
                if not regular_schedule['is_available']:
                    availability_text += f"{day_name} ({date_str}): Not available\n"
                    continue
                start_time = regular_schedule['start_time']
                end_time = regular_schedule['end_time']
            
            # Generate available time slots
            available_slots = self.generate_time_slots(
                check_date, 
                start_time, 
                end_time, 
                availability_data['appointments'].get(check_date, [])
            )
            
            if available_slots:
                times_list = ", ".join(available_slots)
                availability_text += f"{day_name} ({date_str}): {times_list}\n"
            else:
                availability_text += f"{day_name} ({date_str}): No availability\n"
        
        availability_text += f"\nIMPORTANT: You have the complete schedule above. When patients ask about times, offer these exact available slots directly. Don't say 'let me check' - you already know the schedule!"
        
        return availability_text
    
    def generate_time_slots(self, date, start_time, end_time, existing_appointments, slot_duration=30):
        """Generate available time slots for a specific date."""
        try:
            from datetime import datetime, timedelta
            
            slots = []
            current_time = datetime.combine(date, start_time)
            end_datetime = datetime.combine(date, end_time)
            
            # Create a set of occupied times for quick lookup
            occupied_times = set()
            for apt in existing_appointments:
                apt_start = datetime.combine(date, apt['appointment_time'])
                apt_end = apt_start + timedelta(minutes=apt['duration_minutes'])
                
                # Mark all times in this appointment as occupied
                check_time = apt_start
                while check_time < apt_end:
                    occupied_times.add(check_time.time())
                    check_time += timedelta(minutes=15)  # Check every 15 minutes
            
            # Generate available slots
            while current_time + timedelta(minutes=slot_duration) <= end_datetime:
                slot_time = current_time.time()
                slot_end = (current_time + timedelta(minutes=slot_duration)).time()
                
                # Check if this slot conflicts with any appointment
                is_available = True
                check_time = current_time
                while check_time < current_time + timedelta(minutes=slot_duration):
                    if check_time.time() in occupied_times:
                        is_available = False
                        break
                    check_time += timedelta(minutes=15)
                
                if is_available:
                    slots.append(slot_time.strftime("%H:%M"))
                
                current_time += timedelta(minutes=slot_duration)
            
            return slots
            
        except Exception as e:
            print(f"DEBUG: Error generating time slots: {e}")
            return []
    
    @database_sync_to_async
    def get_nurse_context_info(self):
        """Get additional nurse context information from database."""
        try:
            nurse_id = getattr(self, 'nurse_id', None)
            if not nurse_id:
                return ""
            
            from .models import Nurse, NurseAvailability
            
            try:
                nurse = Nurse.objects.get(id=nurse_id)
                context_info = f"\nNURSE DETAILS:\n"
                context_info += f"- Name: {nurse.name}\n"
                context_info += f"- Specialization: {nurse.specialization}\n"
                context_info += f"- Phone: {nurse.phone}\n"
                context_info += f"- Email: {nurse.email}\n"
                
                # Get nurse's working days
                working_days = NurseAvailability.objects.filter(
                    nurse_id=nurse_id,
                    is_available=True
                ).values_list('day_of_week', flat=True)
                
                if working_days:
                    context_info += f"- Working Days: {', '.join(working_days)}\n"
                
                return context_info
                
            except Nurse.DoesNotExist:
                return f"\nNURSE DETAILS:\n- Nurse ID {nurse_id} not found in database\n"
                
        except Exception as e:
            print(f"DEBUG: Error getting nurse context: {e}")
            return ""
    
    async def get_available_times_for_date(self, nurse_id, date_str):
        """Get available time slots for a specific nurse and date."""
        try:
            print(f"\nDEBUG: Getting available times for nurse_id={nurse_id}, date={date_str}")
            
            # First, let's check what's in the database
            await self.debug_nurse_availability(nurse_id, date_str)
            
            # Use the database helper to get available times
            result = await self.db_helper.get_available_times(nurse_id, date_str)
            print(f"DEBUG: Database result: {result}")
            
            if result.get('success'):
                available_times = result.get('available_times', [])
                print(f"DEBUG: Available times for {date_str}: {available_times}")
                return available_times
            print(f"DEBUG: No success in result for {date_str}")
            return []
        except Exception as e:
            openai_logger.error(f"Error getting available times for {date_str}: {e}")
            print(f"DEBUG: Exception getting times for {date_str}: {e}")
            return []
    
    async def debug_nurse_availability(self, nurse_id, date_str):
        """Debug function to check what's in the database for nurse availability."""
        try:
            from datetime import datetime
            from .models import Nurse, NurseAvailability, NurseAvailabilityOverride, Appointment
            
            print(f"\n=== DEBUGGING NURSE AVAILABILITY ===")
            print(f"Nurse ID: {nurse_id}")
            print(f"Date: {date_str}")
            
            # Check if nurse exists
            try:
                nurse = Nurse.objects.get(id=nurse_id)
                print(f"Nurse found: {nurse.name}")
            except Nurse.DoesNotExist:
                print(f"ERROR: Nurse with ID {nurse_id} not found!")
                return
            
            # Check day of week
            appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_of_week = appointment_date.strftime("%A")
            print(f"Day of week: {day_of_week}")
            
            # Check regular availability
            regular_availability = NurseAvailability.objects.filter(
                nurse_id=nurse_id,
                day_of_week=day_of_week,
                is_available=True
            )
            print(f"Regular availability records: {regular_availability.count()}")
            for avail in regular_availability:
                print(f"  - {avail.start_time} to {avail.end_time}")
            
            # Check overrides
            overrides = NurseAvailabilityOverride.objects.filter(
                nurse_id=nurse_id,
                override_date=appointment_date
            )
            print(f"Override records: {overrides.count()}")
            for override in overrides:
                print(f"  - Available: {override.is_available}, {override.start_time} to {override.end_time}")
            
            # Check existing appointments
            existing_appointments = Appointment.objects.filter(
                nurse_id=nurse_id,
                appointment_date=appointment_date,
                status__in=['scheduled', 'confirmed']
            )
            print(f"Existing appointments: {existing_appointments.count()}")
            for apt in existing_appointments:
                print(f"  - {apt.appointment_time} ({apt.duration_minutes} min)")
            
            print(f"=== END DEBUG ===\n")
            
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    @database_sync_to_async
    def ensure_nurse_availability_exists(self, nurse_id):
        """Ensure nurse has availability data, create basic availability if none exists."""
        try:
            from datetime import time
            from .models import NurseAvailability
            
            # Check if nurse has any availability records
            existing_availability = NurseAvailability.objects.filter(nurse_id=nurse_id).exists()
            
            if not existing_availability:
                print(f"DEBUG: No availability data found for nurse {nurse_id}, creating basic availability...")
                
                # Create basic availability for all days
                availability_schedule = {
                    'Monday': (time(9, 0), time(17, 0)),    # 9 AM to 5 PM
                    'Tuesday': (time(9, 0), time(17, 0)),   # 9 AM to 5 PM
                    'Wednesday': (time(9, 0), time(17, 0)), # 9 AM to 5 PM
                    'Thursday': (time(9, 0), time(17, 0)),  # 9 AM to 5 PM
                    'Friday': (time(9, 0), time(17, 0)),    # 9 AM to 5 PM
                    'Saturday': (time(10, 0), time(14, 0)), # 10 AM to 2 PM
                    'Sunday': (time(10, 0), time(14, 0)),   # 10 AM to 2 PM
                }
                
                for day, (start_time, end_time) in availability_schedule.items():
                    NurseAvailability.objects.create(
                        nurse_id=nurse_id,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time,
                        is_available=True
                    )
                    print(f"DEBUG: Created availability for {day}: {start_time} - {end_time}")
                
                print(f"DEBUG: Created basic availability for nurse {nurse_id}")
                return True
            else:
                print(f"DEBUG: Availability data already exists for nurse {nurse_id}")
                return True
                
        except Exception as e:
            print(f"DEBUG: Error ensuring nurse availability: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
                        # Store nurse info for availability timeline
                        self.nurse_id = nurse_data['id']
                        self.nurse_name = nurse_data['name']
                        self.nurse_specialization = nurse_data['specialization']
                        
                        # Debug: Print nurse info
                        print(f"\nDEBUG: Nurse context set up:")
                        print(f"  - Nurse ID: {self.nurse_id}")
                        print(f"  - Nurse Name: {self.nurse_name}")
                        print(f"  - Nurse Specialization: {self.nurse_specialization}")
                    else:
                        print(f"DEBUG: No assigned nurse found for patient {patient_data['name']}")
                        # Create a default nurse if none assigned
                        await self.create_default_nurse_assignment(patient_data['id'])
                else:
                    print(f"DEBUG: No patient data found for phone {patient_phone}")
            except Exception as e:
                openai_logger.error(f"Error getting patient/nurse data: {e}")
                import traceback
                traceback.print_exc()
    
    @database_sync_to_async
    def create_default_nurse_assignment(self, patient_id):
        """Create a default nurse assignment if none exists."""
        try:
            from .models import Patient, Nurse, PatientNurseAssignment
            
            # Ensure at least one nurse exists
            nurse = self.ensure_nurse_exists()
            if nurse:
                # Create assignment
                assignment, created = PatientNurseAssignment.objects.get_or_create(
                    patient_id=patient_id,
                    nurse=nurse,
                    defaults={'is_primary': True}
                )
                
                if created:
                    print(f"DEBUG: Created default nurse assignment: Patient {patient_id} -> Nurse {nurse.id} ({nurse.name})")
                    # Set nurse context
                    self.nurse_id = nurse.id
                    self.nurse_name = nurse.name
                    self.nurse_specialization = nurse.specialization
                    return True
                else:
                    print(f"DEBUG: Assignment already exists: Patient {patient_id} -> Nurse {nurse.id}")
                    return True
            else:
                print("DEBUG: No nurses available in database")
                return False
                
        except Exception as e:
            print(f"DEBUG: Error creating default nurse assignment: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @database_sync_to_async
    def ensure_nurse_exists(self):
        """Ensure at least one nurse exists in the database."""
        try:
            from .models import Nurse
            
            # Check if any nurses exist
            if not Nurse.objects.exists():
                print("DEBUG: No nurses found, creating default nurse...")
                # Create a default nurse
                default_nurse = Nurse.objects.create(
                    name="Dr. Sarah Johnson",
                    specialization="General Practice",
                    phone="+1234567890",
                    email="sarah.johnson@carematrix.com",
                    is_available=True
                )
                print(f"DEBUG: Created default nurse: {default_nurse.name} (ID: {default_nurse.id})")
                return default_nurse
            else:
                nurse = Nurse.objects.first()
                print(f"DEBUG: Found existing nurse: {nurse.name} (ID: {nurse.id})")
                return nurse
                
        except Exception as e:
            print(f"DEBUG: Error ensuring nurse exists: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def process_conversation_events(self, response):
        """Process conversation events and capture transcripts."""
        response_type = response.get('type', 'unknown')
        
        if response_type == 'conversation.item.input_audio_buffer.speech_started':
            openai_logger.info("Patient started speaking")
            await self.log_conversation(self.call_id, 'patient', '[Patient started speaking]', 'action', None)
            
        elif response_type == 'conversation.item.input_audio_buffer.speech_stopped':
            openai_logger.info("Patient finished speaking")
            await self.log_conversation(self.call_id, 'patient', '[Patient finished speaking]', 'action', None)
            
        # Capture conversation content for transcript
        elif response_type == 'conversation.item.input_audio_buffer.committed':
            # Patient speech was processed
            if 'transcript' in response.get('input_audio_buffer', {}):
                transcript_text = response['input_audio_buffer']['transcript']
                if transcript_text:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    # Print to console in real-time
                    print(f"\nPATIENT [{timestamp}]: {transcript_text}")
                    
                    # Add to conversation tracking
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
            if 'transcript' in response.get('output_audio', {}):
                transcript_text = response['output_audio']['transcript']
                if transcript_text:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    # Print to console in real-time
                    print(f"\nASSISTANT [{timestamp}]: {transcript_text}")
                    
                    # Add to conversation tracking
                    self.conversation_parts.append(f"Assistant: {transcript_text}")
                    self.assistant_messages.append(transcript_text)
                    
                    await self.log_conversation(self.call_id, 'assistant', transcript_text, 'transcript', None)
                    
                    # Check for conversation end signals in assistant speech
                    if self.check_conversation_end(transcript_text):
                        openai_logger.info("Conversation end detected from assistant speech")
                        self.call_should_end = True
                        await self.end_call_gracefully()
                        return
                    
                    # Check for appointment confirmations in assistant speech
                    await self.process_appointment_confirmation(transcript_text)
    
    async def process_appointment_confirmation(self, transcript_text):
        """Process appointment confirmations from assistant speech and schedule in database."""
        try:
            import re
            from datetime import datetime, timedelta
            
            # Look for appointment confirmation patterns
            confirmation_patterns = [
                r"i've got you down for (.+?) at (.+?) with",
                r"appointment confirmed for (.+?) at (.+?)",
                r"booked for (.+?) at (.+?)",
                r"scheduled for (.+?) at (.+?)",
                r"confirmed for (.+?) at (.+?)"
            ]
            
            transcript_lower = transcript_text.lower()
            
            # Check if this is an appointment confirmation
            if any(phrase in transcript_lower for phrase in ["confirmed", "booked", "scheduled", "got you down", "appointment"]):
                for pattern in confirmation_patterns:
                    match = re.search(pattern, transcript_lower)
                    if match:
                        day_info = match.group(1).strip()
                        time_info = match.group(2).strip()
                        
                        openai_logger.info(f"Appointment confirmation detected: {day_info} at {time_info}")
                        
                        # Parse the day and time
                        appointment_date = await self.parse_appointment_date(day_info)
                        appointment_time = await self.parse_appointment_time(time_info)
                        
                        if appointment_date and appointment_time:
                            # Schedule the appointment in the database
                            await self.schedule_appointment_in_database(appointment_date, appointment_time)
                        else:
                            openai_logger.warning(f"Could not parse appointment details: {day_info} at {time_info}")
                        
                        break
                        
        except Exception as e:
            openai_logger.error(f"Error processing appointment confirmation: {e}")
    
    async def parse_appointment_date(self, day_info):
        """Parse appointment date from day information."""
        try:
            from datetime import datetime, timedelta
            
            day_lower = day_info.lower()
            today = datetime.now().date()
            
            if "today" in day_lower:
                return today
            elif "tomorrow" in day_lower:
                return today + timedelta(days=1)
            elif "monday" in day_lower:
                return self.get_next_weekday(0)  # Monday
            elif "tuesday" in day_lower:
                return self.get_next_weekday(1)  # Tuesday
            elif "wednesday" in day_lower:
                return self.get_next_weekday(2)  # Wednesday
            elif "thursday" in day_lower:
                return self.get_next_weekday(3)  # Thursday
            elif "friday" in day_lower:
                return self.get_next_weekday(4)  # Friday
            elif "saturday" in day_lower:
                return self.get_next_weekday(5)  # Saturday
            elif "sunday" in day_lower:
                return self.get_next_weekday(6)  # Sunday
            
            return None
        except Exception as e:
            openai_logger.error(f"Error parsing appointment date: {e}")
            return None
    
    def get_next_weekday(self, weekday):
        """Get the next occurrence of a specific weekday."""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    async def parse_appointment_time(self, time_info):
        """Parse appointment time from time information."""
        try:
            import re
            
            # Common time patterns
            time_patterns = [
                r"(\d{1,2}):?(\d{2})?\s*(am|pm)",
                r"(\d{1,2})\s*(am|pm)",
                r"(\d{1,2}):(\d{2})"
            ]
            
            time_lower = time_info.lower()
            
            for pattern in time_patterns:
                match = re.search(pattern, time_lower)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if match.group(2) else 0
                    
                    # Handle AM/PM
                    if len(match.groups()) >= 3 and match.group(3):
                        period = match.group(3)
                        if period == "pm" and hour != 12:
                            hour += 12
                        elif period == "am" and hour == 12:
                            hour = 0
                    
                    return f"{hour:02d}:{minute:02d}"
            
            return None
        except Exception as e:
            openai_logger.error(f"Error parsing appointment time: {e}")
            return None
    
    async def schedule_appointment_in_database(self, appointment_date, appointment_time):
        """Schedule the appointment in the database."""
        try:
            # Get patient and nurse IDs
            patient_id = getattr(self, 'db_helper', {}).get('current_patient_id')
            nurse_id = getattr(self, 'nurse_id', None)
            
            if not patient_id or not nurse_id:
                openai_logger.error("Missing patient or nurse ID for appointment scheduling")
                return
            
            # Use the database helper to schedule the appointment
            result = await self.db_helper.schedule_appointment(
                patient_id=patient_id,
                nurse_id=nurse_id,
                date=appointment_date.strftime('%Y-%m-%d'),
                time=appointment_time,
                duration=30  # Default 30 minutes
            )
            
            if result.get('success'):
                openai_logger.info(f"Appointment scheduled successfully: {appointment_date} at {appointment_time}")
            else:
                openai_logger.error(f"Failed to schedule appointment: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            openai_logger.error(f"Error scheduling appointment in database: {e}")

    async def monitor_call_timeout(self):
        """Monitor call for timeouts and automatically end if needed."""
        try:
            while not self.call_should_end and not self.call_ending:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_time = datetime.now()
                
                # Check for silence timeout
                silence_duration = (current_time - self.last_activity_time).total_seconds()
                if silence_duration > self.silence_threshold:
                    logger.info(f"Call timeout due to silence: {silence_duration}s")
                    self.call_should_end = True
                    await self.end_call_gracefully()
                    break
                
                # Check for maximum call duration
                call_duration = (current_time - self.call_start_time).total_seconds()
                if call_duration > self.max_call_duration:
                    logger.info(f"Call timeout due to maximum duration: {call_duration}s")
                    self.call_should_end = True
                    await self.end_call_gracefully()
                    break
                    
        except Exception as e:
            logger.error(f"Error in call monitoring: {e}")

    def check_conversation_end(self, transcript_text):
        """Check if the conversation should end based on transcript content"""
        end_phrases = [
            "goodbye", "bye", "thank you", "thanks", "that's all", "that's it",
            "i'm done", "i'm finished", "end call", "hang up", "disconnect",
            "see you later", "talk to you later", "have a good day", "take care",
            "appointment scheduled", "meeting scheduled", "confirmed", "done",
            "okay bye", "ok bye", "alright bye", "sounds good", "perfect",
            "i've got you down", "booked", "scheduled", "appointment confirmed",
            "you're all set", "that works", "great choice", "excellent",
            "call you back", "send confirmation", "receive confirmation"
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
            # Log closing message but don't send to OpenAI to avoid conflicts
            closing_text = "Thank you for your time! Your appointment has been scheduled and you'll receive a confirmation shortly. Have a great day!"
            logger.info(f"Call ending: {closing_text}")
            # Note: We don't send closing messages to OpenAI as they can cause response conflicts
            # await asyncio.sleep(1)  # Brief pause before hangup
            
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
            import json
            import re
            
            # Look for JSON database requests in the transcript
            # More flexible regex to catch JSON with database_request
            json_match = re.search(r'\{[^{}]*"type"[^{}]*"database_request"[^{}]*\}', transcript_text, re.IGNORECASE)
            
            if json_match:
                try:
                    request_data = json.loads(json_match.group())
                    action = request_data.get('action')
                    params = request_data.get('params', {})
                    
                    print(f"\nDATABASE REQUEST: {action} with params: {params}")
                    
                    if action == "check_nurse_availability":
                        result = await self.db_helper.check_nurse_availability(
                            params.get('nurse_id'),
                            params.get('date'),
                            params.get('time')
                        )
                        response_text = f"Nurse availability check: {result.get('available', False)}"
                        
                    elif action == "schedule_appointment":
                        result = await self.db_helper.schedule_appointment(
                            params.get('patient_id'),
                            params.get('nurse_id'),
                            params.get('date'),
                            params.get('time'),
                            params.get('duration', 30)
                        )
                        response_text = f"Appointment scheduled: {result.get('success', False)}"
                        
                    elif action == "get_available_times":
                        result = await self.db_helper.get_available_times(
                            params.get('nurse_id'),
                            params.get('date')
                        )
                        response_text = f"Available times: {result.get('available_times', [])}"
                        
                    else:
                        response_text = f"Unknown database action: {action}"
                    
                    print(f"DATABASE RESPONSE: {response_text}")
                    
                    # Log database response but don't send to OpenAI to avoid conflicts
                    openai_logger.info(f"Database response: {response_text}")
                    # Note: We don't send database responses to OpenAI as they can cause response conflicts
                    
                    # Log the database interaction
                    await self.log_conversation(self.call_id, 'assistant', f"Database {action}: {response_text}", 'database', None)
                    
                except json.JSONDecodeError as e:
                    openai_logger.error(f"Invalid JSON in database request: {e}")
                    
            else:
                # Fallback: Look for phone numbers in the transcript
                phone_match = re.search(r'\+?[1-9]\d{1,14}', transcript_text)
            
            if phone_match:
                phone_number = phone_match.group()
                openai_logger.info(f"Found phone number in transcript: {phone_number}")
                
                # Get patient info from database
                patient_info = await self.db_helper.get_patient_info(phone_number)
                
                if patient_info.get('success'):
                    # Get assigned nurse
                    nurse_info = await self.db_helper.get_assigned_nurse(patient_info['patient']['id'])
                    
                    # Log phone lookup response but don't send to OpenAI to avoid conflicts
                    response_text = f"{patient_info['message']} {nurse_info['message']}"
                    openai_logger.info(f"Phone lookup response: {response_text}")
                    # Note: We don't send phone lookup responses to OpenAI as they can cause response conflicts
                    
                    # Log the database interaction
                    await self.log_conversation(self.call_id, 'assistant', f"Phone lookup: {patient_info['message']}", 'database', None)
                    
        except Exception as e:
            openai_logger.error(f"Error processing database request: {e}")
    
    async def save_call_audio(self, call_id, patient_audio_data, assistant_audio_data):
        """Save audio recordings for a call with proper WAV formatting"""
        try:
            # Create recordings directory
            os.makedirs("recordings", exist_ok=True)
            
            # Save patient audio
            if patient_audio_data:
                patient_audio_file = f"recordings/call_{call_id}_patient.wav"
                await self.save_audio_as_wav(patient_audio_data, patient_audio_file, "Patient")
                logger.info(f"Saved patient audio: {patient_audio_file}")
            
            # Save assistant audio
            if assistant_audio_data:
                assistant_audio_file = f"recordings/call_{call_id}_assistant.wav"
                await self.save_audio_as_wav(assistant_audio_data, assistant_audio_file, "Assistant")
                logger.info(f"Saved assistant audio: {assistant_audio_file}")
            
            # Create combined audio file
            if patient_audio_data and assistant_audio_data:
                combined_audio_file = f"recordings/call_{call_id}_combined.wav"
                await self.create_combined_audio(patient_audio_data, assistant_audio_data, combined_audio_file)
                logger.info(f"Saved combined audio: {combined_audio_file}")
                
        except Exception as e:
            logger.error(f"Error saving audio files: {e}")
            import traceback
            traceback.print_exc()
    
    async def create_combined_audio(self, patient_audio_data, assistant_audio_data, filename):
        """Create a combined audio file with both patient and assistant audio"""
        try:
            import wave
            import audioop
            
            # Decode patient audio
            patient_raw = b''
            for chunk in patient_audio_data:
                patient_raw += base64.b64decode(chunk)
            
            # Decode assistant audio
            assistant_raw = b''
            for chunk in assistant_audio_data:
                assistant_raw += base64.b64decode(chunk)
            
            if not patient_raw and not assistant_raw:
                logger.warning("No audio data to combine")
                return
            
            # Convert both to PCM
            patient_pcm = audioop.ulaw2lin(patient_raw, 2) if patient_raw else b''
            assistant_pcm = audioop.ulaw2lin(assistant_raw, 2) if assistant_raw else b''
            
            # Create combined audio (simple concatenation for now)
            combined_pcm = patient_pcm + assistant_pcm
            
            # Save as WAV
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz
                wav_file.writeframes(combined_pcm)
            
            logger.info(f"Successfully created combined audio: {filename}")
            
        except Exception as e:
            logger.error(f"Error creating combined audio: {e}")
            import traceback
            traceback.print_exc()
    
    async def save_audio_as_wav(self, audio_data, filename, audio_type):
        """Convert PCMU audio data to proper WAV format"""
        try:
            import wave
            import audioop
            
            # Decode all base64 chunks
            raw_audio = b''
            for chunk in audio_data:
                raw_audio += base64.b64decode(chunk)
            
            if not raw_audio:
                logger.warning(f"No audio data to save for {audio_type}")
                return
            
            # Convert PCMU (μ-law) to PCM
            # PCMU is 8-bit μ-law encoded audio at 8kHz sample rate
            try:
                pcm_audio = audioop.ulaw2lin(raw_audio, 2)  # Convert to 16-bit PCM
            except Exception as e:
                logger.warning(f"Could not convert PCMU to PCM: {e}, saving as raw")
                pcm_audio = raw_audio
            
            # Create WAV file with proper headers
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit (2 bytes per sample)
                wav_file.setframerate(8000)  # 8kHz sample rate (standard for telephony)
                wav_file.writeframes(pcm_audio)
            
            # Also create a higher quality version
            hq_filename = filename.replace('.wav', '_hq.wav')
            await self.create_high_quality_wav(pcm_audio, hq_filename, audio_type)
            
            logger.info(f"Successfully saved {audio_type} audio as WAV: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving {audio_type} audio as WAV: {e}")
            # Fallback: save as raw PCMU data
            try:
                with open(filename.replace('.wav', '_raw.pcmu'), 'wb') as f:
                    for chunk in audio_data:
                        f.write(base64.b64decode(chunk))
                logger.info(f"Saved {audio_type} audio as raw PCMU: {filename.replace('.wav', '_raw.pcmu')}")
            except Exception as fallback_error:
                logger.error(f"Fallback save also failed: {fallback_error}")
    
    async def create_high_quality_wav(self, pcm_audio, filename, audio_type):
        """Create a higher quality WAV file with upsampled audio"""
        try:
            import wave
            import audioop
            
            if not pcm_audio:
                return
            
            # Upsample from 8kHz to 44.1kHz for better quality
            try:
                # First convert to 16kHz, then to 44.1kHz
                upsampled_8k_to_16k = audioop.ratecv(pcm_audio, 2, 1, 8000, 16000, None)[0]
                upsampled_16k_to_44k = audioop.ratecv(upsampled_8k_to_16k, 2, 1, 16000, 44100, None)[0]
                
                # Create high quality WAV file
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(44100)  # 44.1kHz sample rate (CD quality)
                    wav_file.writeframes(upsampled_16k_to_44k)
                
                logger.info(f"Successfully created high quality {audio_type} audio: {filename}")
                
            except Exception as e:
                logger.warning(f"Could not create high quality version: {e}")
                # Fallback: save original quality
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(8000)
                    wav_file.writeframes(pcm_audio)
                
        except Exception as e:
            logger.error(f"Error creating high quality WAV: {e}")
    
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
        """Save full transcript in database and backup file."""
        try:
            # Save to database
            from .models import Call
            call_obj = Call.objects.get(id=call_id)
            transcript, created = CallTranscript.objects.update_or_create(
                call=call_obj,
                defaults={
                    'full_transcript': full_transcript,
                    'patient_transcript': patient_transcript,
                    'assistant_transcript': assistant_transcript,
                    'appointment_summary': appointment_summary,
                    'scheduling_outcome': scheduling_outcome
                }
            )
            action = "created" if created else "updated"
            logger.info(f"Transcript {action} in database for call {call_id}")
            
            # Save backup to file
            self.save_transcript_to_file(call_id, full_transcript, patient_transcript, assistant_transcript)
            
        except Call.DoesNotExist:
            logger.error(f"Call with ID {call_id} not found in database")
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def save_transcript_to_file(self, call_id, full_transcript, patient_transcript, assistant_transcript):
        """Save transcript backup to file."""
        try:
            # Create transcripts directory if it doesn't exist
            transcripts_dir = os.path.join(settings.BASE_DIR, 'transcripts')
            os.makedirs(transcripts_dir, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"call_{call_id}_{timestamp}.txt"
            filepath = os.path.join(transcripts_dir, filename)
            
            # Write transcript to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
                f.write(f"\n\n{'='*50}\n")
                f.write(f"PATIENT TRANSCRIPT:\n")
                f.write(f"{'='*50}\n")
                f.write(patient_transcript)
                f.write(f"\n\n{'='*50}\n")
                f.write(f"ASSISTANT TRANSCRIPT:\n")
                f.write(f"{'='*50}\n")
                f.write(assistant_transcript)
            
            
        except Exception as e:
            logger.error(f"Error saving transcript to file: {e}")
    
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

