"""
Database helper class for voice agent integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.db.models import Q
from .models import (
    Patient, Nurse, PatientNurseAssignment, NurseAvailability, 
    NurseAvailabilityOverride, Appointment, Call, Notification
)

logger = logging.getLogger('carematix.database_helper')


class VoiceAgentDatabaseHelper:
    """Helper class to provide database access to voice agent"""

    def __init__(self):
        self.current_call_id = None
        self.current_patient_phone = None
        self.current_patient_id = None
        self.current_patient_data = None
        self.current_nurse = None
    
    async def process_voice_agent_request(self, request_type: str, params: Dict) -> Dict:
        """Process requests from voice agent and return database data"""
        try:
            if request_type == "get_patient_info":
                return await self.get_patient_info(params.get("phone_number"))
            
            elif request_type == "get_assigned_nurse":
                return await self.get_assigned_nurse(params.get("patient_id"))
            
            elif request_type == "check_nurse_availability":
                return await self.check_nurse_availability(
                    params.get("nurse_id"),
                    params.get("date"),
                    params.get("time")
                )
            
            elif request_type == "get_available_times":
                return await self.get_available_times(
                    params.get("nurse_id"),
                    params.get("date")
                )
            
            elif request_type == "schedule_appointment":
                return await self.schedule_appointment(
                    params.get("patient_id"),
                    params.get("nurse_id"),
                    params.get("date"),
                    params.get("time"),
                    params.get("duration", 30)
                )
            
            else:
                return {"error": "Unknown request type"}
                
        except Exception as e:
            logger.error(f"Database helper error: {e}")
            return {"error": str(e)}
    
    async def get_patient_info(self, phone_number: str) -> Dict:
        """Get patient information by phone number"""
        # First check if we already have patient data
        if self.current_patient_data and self.current_patient_phone == phone_number:
            patient = self.current_patient_data
            return {
                "success": True,
                "patient": patient,
                "message": f"Hello {patient['name']}, I have your information from our system."
            }

        # Otherwise, look up from database
        try:
            patient = Patient.objects.get(phone=phone_number)
            patient_data = {
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone,
                'email': patient.email,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'medical_conditions': patient.medical_conditions
            }
            
            self.current_patient_id = patient.id
            self.current_patient_phone = phone_number
            self.current_patient_data = patient_data
            
            return {
                "success": True,
                "patient": patient_data,
                "message": f"Hello {patient.name}, I found your information in our system."
            }
        except Patient.DoesNotExist:
            return {
                "success": False,
                "message": "I don't have your information in our system. Let me help you get set up."
            }
    
    async def get_assigned_nurse(self, patient_id: int) -> Dict:
        """Get patient's assigned nurse"""
        # First check if we already have nurse data for this patient
        if self.current_nurse and self.current_patient_id == patient_id:
            nurse = self.current_nurse
            return {
                "success": True,
                "nurse": nurse,
                "message": f"Your assigned nurse is {nurse['name']}, who specializes in {nurse['specialization']}."
            }

        # Otherwise, look up from database
        try:
            assignment = PatientNurseAssignment.objects.filter(
                patient_id=patient_id,
                assignment_date=datetime.now().date(),
                is_primary=True
            ).select_related('nurse').first()
            
            if assignment:
                nurse_data = {
                    'id': assignment.nurse.id,
                    'name': assignment.nurse.name,
                    'specialization': assignment.nurse.specialization,
                    'phone': assignment.nurse.phone,
                    'email': assignment.nurse.email
                }
                self.current_nurse = nurse_data
                
                return {
                    "success": True,
                    "nurse": nurse_data,
                    "message": f"Your assigned nurse is {assignment.nurse.name}, who specializes in {assignment.nurse.specialization}."
                }
            else:
                return {
                    "success": False,
                    "message": "I don't see an assigned nurse for you today. Let me find an available nurse."
                }
        except Exception as e:
            logger.error(f"Error getting assigned nurse: {e}")
            return {
                "success": False,
                "message": "I don't see an assigned nurse for you today. Let me find an available nurse."
            }
    
    async def check_nurse_availability(self, nurse_id: int, date: str, time: str) -> Dict:
        """Check if nurse is available at specific time"""
        try:
            nurse = Nurse.objects.get(id=nurse_id)
            appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
            appointment_time = datetime.strptime(time, "%H:%M").time()
            
            # Check if nurse is available
            is_available = self._check_nurse_availability(nurse_id, appointment_date, appointment_time)
            
            if is_available:
                return {
                    "success": True,
                    "available": True,
                    "message": f"Great! {nurse.name} is available at {time} on {date}."
                }
            else:
                return {
                    "success": True,
                    "available": False,
                    "message": f"I'm sorry, {nurse.name} is not available at {time} on {date}."
                }
        except Exception as e:
            logger.error(f"Error checking nurse availability: {e}")
            return {
                "success": False,
                "message": "I'm sorry, I couldn't check the availability right now."
            }
    
    async def get_available_times(self, nurse_id: int, date: str) -> Dict:
        """Get all available times for a nurse on a specific date"""
        try:
            appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
            available_slots = self._get_nurse_available_slots(nurse_id, appointment_date)
            
            if available_slots:
                return {
                    "success": True,
                    "available_times": available_slots,
                    "message": f"Here are the available times: {', '.join(available_slots[:5])}"
                }
            else:
                return {
                    "success": False,
                    "message": "I'm sorry, there are no available times for today."
                }
        except Exception as e:
            logger.error(f"Error getting available times: {e}")
            return {
                "success": False,
                "message": "I'm sorry, I couldn't get the available times right now."
            }
    
    async def schedule_appointment(self, patient_id: int, nurse_id: int, date: str, time: str, duration: int = 30) -> Dict:
        """Schedule an appointment"""
        try:
            appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
            appointment_time = datetime.strptime(time, "%H:%M").time()
            
            # Check availability first
            if not self._check_nurse_availability(nurse_id, appointment_date, appointment_time, duration):
                return {
                    "success": False,
                    "message": "I'm sorry, the nurse is not available at that time."
                }
            
            # Create appointment
            patient = Patient.objects.get(id=patient_id)
            nurse = Nurse.objects.get(id=nurse_id)
            
            appointment = Appointment.objects.create(
                patient=patient,
                nurse=nurse,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                duration_minutes=duration
            )
            
            # Create notifications
            Notification.objects.create(
                recipient_type="patient",
                recipient_id=patient.name,
                notification_type="appointment_confirmed",
                message=f"Your appointment with {nurse.name} is scheduled for {appointment_date} at {appointment_time}",
                appointment=appointment
            )
            
            Notification.objects.create(
                recipient_type="nurse",
                recipient_id=nurse.name,
                notification_type="appointment_assigned",
                message=f"New appointment scheduled with {patient.name} on {appointment_date} at {appointment_time}",
                appointment=appointment
            )
            
            return {
                "success": True,
                "appointment_id": appointment.id,
                "appointment": {
                    "id": appointment.id,
                    "patient_name": patient.name,
                    "nurse_name": nurse.name,
                    "appointment_date": appointment_date.isoformat(),
                    "appointment_time": appointment_time.strftime("%H:%M"),
                    "duration_minutes": duration
                },
                "message": f"Perfect! I've scheduled your appointment with {nurse.name} for {appointment_date} at {appointment_time}. You'll both receive confirmation notifications."
            }
        except Exception as e:
            logger.error(f"Error scheduling appointment: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "I'm sorry, I couldn't schedule that appointment. Let me try again."
            }
    
    def _check_nurse_availability(self, nurse_id: int, date: datetime.date, time: datetime.time, duration: int = 30) -> bool:
        """Check if nurse is available at specific time"""
        day_of_week = date.strftime("%A")
        
        # Check for override first
        override = NurseAvailabilityOverride.objects.filter(
            nurse_id=nurse_id,
            override_date=date
        ).first()
        
        if override:
            if not override.is_available:
                return False
            if override.start_time and override.end_time:
                if not (override.start_time <= time <= override.end_time):
                    return False
        else:
            # Check regular availability
            availability = NurseAvailability.objects.filter(
                nurse_id=nurse_id,
                day_of_week=day_of_week,
                is_available=True
            ).first()
            
            if not availability:
                return False
            
            if not (availability.start_time <= time <= availability.end_time):
                return False
        
        # Check for conflicts with existing appointments
        end_time = (datetime.combine(date, time) + timedelta(minutes=duration)).time()
        
        conflicting_appointments = Appointment.objects.filter(
            nurse_id=nurse_id,
            appointment_date=date,
            appointment_time=time,
            status__in=['scheduled', 'confirmed']
        ).exists()
        
        return not conflicting_appointments
    
    def _get_nurse_available_slots(self, nurse_id: int, date: datetime.date, slot_duration: int = 30) -> List[str]:
        """Get available time slots for a nurse on a specific date"""
        day_of_week = date.strftime("%A")
        slots = []
        
        # Check for override first
        override = NurseAvailabilityOverride.objects.filter(
            nurse_id=nurse_id,
            override_date=date
        ).first()
        
        if override:
            if not override.is_available:
                return []
            if override.start_time and override.end_time:
                start_time = override.start_time
                end_time = override.end_time
            else:
                return []
        else:
            # Check regular availability
            availability = NurseAvailability.objects.filter(
                nurse_id=nurse_id,
                day_of_week=day_of_week,
                is_available=True
            ).first()
            
            if not availability:
                return []
            
            start_time = availability.start_time
            end_time = availability.end_time
        
        # Generate time slots
        current_time = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)
        
        while current_time + timedelta(minutes=slot_duration) <= end_datetime:
            slot_time = current_time.time()
            if self._check_nurse_availability(nurse_id, date, slot_time, slot_duration):
                slots.append(slot_time.strftime("%H:%M"))
            current_time += timedelta(minutes=slot_duration)
        
        return slots

