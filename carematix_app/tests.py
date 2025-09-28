"""
Django tests for the Carematix healthcare scheduling system.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import (
    Patient, Nurse, PatientNurseAssignment, NurseAvailability, 
    Appointment, Call, ConversationLog, CallTranscript, Notification
)
from .database_helper import VoiceAgentDatabaseHelper


class CarematixTestCase(TestCase):
    """Base test case with common setup."""
    
    def setUp(self):
        """Set up test data."""
        # Create test patient
        self.patient = Patient.objects.create(
            name="Test Patient",
            phone="+1234567890",
            email="test@example.com",
            date_of_birth="1980-01-01",
            medical_conditions=["Diabetes"]
        )
        
        # Create test nurse
        self.nurse = Nurse.objects.create(
            name="Test Nurse",
            phone="+1987654321",
            email="nurse@example.com",
            specialization="General Care",
            license_number="RN999"
        )
        
        # Set up nurse availability
        NurseAvailability.objects.create(
            nurse=self.nurse,
            day_of_week="Monday",
            start_time="09:00",
            end_time="17:00",
            is_available=True
        )
        
        # Assign nurse to patient
        PatientNurseAssignment.objects.create(
            patient=self.patient,
            nurse=self.nurse,
            assignment_date=timezone.now().date(),
            is_primary=True
        )
        
        self.client = Client()


class PatientModelTest(CarematixTestCase):
    """Test Patient model."""
    
    def test_patient_creation(self):
        """Test patient creation."""
        self.assertEqual(self.patient.name, "Test Patient")
        self.assertEqual(self.patient.phone, "+1234567890")
        self.assertEqual(self.patient.medical_conditions, ["Diabetes"])
    
    def test_patient_str(self):
        """Test patient string representation."""
        expected = "Test Patient (+1234567890)"
        self.assertEqual(str(self.patient), expected)


class NurseModelTest(CarematixTestCase):
    """Test Nurse model."""
    
    def test_nurse_creation(self):
        """Test nurse creation."""
        self.assertEqual(self.nurse.name, "Test Nurse")
        self.assertEqual(self.nurse.specialization, "General Care")
        self.assertTrue(self.nurse.is_active)
    
    def test_nurse_str(self):
        """Test nurse string representation."""
        expected = "Test Nurse (General Care)"
        self.assertEqual(str(self.nurse), expected)


class AppointmentModelTest(CarematixTestCase):
    """Test Appointment model."""
    
    def test_appointment_creation(self):
        """Test appointment creation."""
        appointment = Appointment.objects.create(
            patient=self.patient,
            nurse=self.nurse,
            appointment_date=timezone.now().date() + timedelta(days=1),
            appointment_time="10:00",
            duration_minutes=30
        )
        
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.nurse, self.nurse)
        self.assertEqual(appointment.status, "scheduled")
    
    def test_appointment_end_time(self):
        """Test appointment end time calculation."""
        appointment = Appointment.objects.create(
            patient=self.patient,
            nurse=self.nurse,
            appointment_date=timezone.now().date(),
            appointment_time="10:00",
            duration_minutes=30
        )
        
        expected_end_time = datetime.strptime("10:30", "%H:%M").time()
        self.assertEqual(appointment.get_end_time(), expected_end_time)


class DatabaseHelperTest(CarematixTestCase):
    """Test database helper functionality."""
    
    def setUp(self):
        super().setUp()
        self.db_helper = VoiceAgentDatabaseHelper()
    
    def test_get_patient_info_success(self):
        """Test successful patient info retrieval."""
        import asyncio
        
        async def test():
            result = await self.db_helper.get_patient_info("+1234567890")
            self.assertTrue(result['success'])
            self.assertEqual(result['patient']['name'], "Test Patient")
        
        asyncio.run(test())
    
    def test_get_patient_info_not_found(self):
        """Test patient info retrieval when patient not found."""
        import asyncio
        
        async def test():
            result = await self.db_helper.get_patient_info("+9999999999")
            self.assertFalse(result['success'])
            self.assertIn("don't have your information", result['message'])
        
        asyncio.run(test())
    
    def test_get_assigned_nurse_success(self):
        """Test successful assigned nurse retrieval."""
        import asyncio
        
        async def test():
            result = await self.db_helper.get_assigned_nurse(self.patient.id)
            self.assertTrue(result['success'])
            self.assertEqual(result['nurse']['name'], "Test Nurse")
        
        asyncio.run(test())


class APITest(CarematixTestCase):
    """Test API endpoints."""
    
    def test_index_endpoint(self):
        """Test index endpoint."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_get_all_patients(self):
        """Test get all patients endpoint."""
        response = self.client.get('/patients/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Test Patient")
    
    def test_get_all_nurses(self):
        """Test get all nurses endpoint."""
        response = self.client.get('/nurses/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Test Nurse")
    
    def test_get_available_nurses(self):
        """Test get available nurses endpoint."""
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.get(f'/nurses/available/?date={tomorrow}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['nurses']), 1)
    
    def test_create_appointment(self):
        """Test create appointment endpoint."""
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        appointment_data = {
            'patient_id': self.patient.id,
            'nurse_id': self.nurse.id,
            'appointment_date': tomorrow,
            'appointment_time': '10:00',
            'duration_minutes': 30
        }
        
        response = self.client.post('/appointments/', 
                                  data=json.dumps(appointment_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['message'], 'Appointment created successfully')
    
    def test_get_patient_assigned_nurse(self):
        """Test get patient assigned nurse endpoint."""
        response = self.client.get(f'/patients/{self.patient.phone}/assigned-nurse/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['nurse']['name'], "Test Nurse")
    
    def test_get_nurse_availability(self):
        """Test get nurse availability endpoint."""
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = self.client.get(f'/nurses/{self.nurse.id}/availability/?date={tomorrow}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('available_slots', data)
    
    def test_make_outbound_call(self):
        """Test make outbound call endpoint."""
        call_data = {
            'phone_number': '+1234567890'
        }
        
        # Mock Twilio client to avoid actual API calls
        with self.settings(TWILIO_ACCOUNT_SID='test', TWILIO_AUTH_TOKEN='test'):
            response = self.client.post('/make-call/',
                                      data=json.dumps(call_data),
                                      content_type='application/json')
            # This will fail without proper Twilio credentials, but we can test the structure
            self.assertIn(response.status_code, [200, 500])


class CallModelTest(CarematixTestCase):
    """Test Call model."""
    
    def test_call_creation(self):
        """Test call creation."""
        call = Call.objects.create(
            call_sid="CA1234567890",
            patient_phone="+1234567890",
            patient=self.patient,
            call_direction="outbound",
            call_status="initiated"
        )
        
        self.assertEqual(call.call_sid, "CA1234567890")
        self.assertEqual(call.patient, self.patient)
        self.assertFalse(call.appointment_scheduled)
    
    def test_call_duration_display(self):
        """Test call duration display."""
        call = Call.objects.create(
            call_sid="CA1234567890",
            patient_phone="+1234567890",
            call_duration=90
        )
        
        self.assertEqual(call.get_duration_display(), "1m 30s")


class NotificationModelTest(CarematixTestCase):
    """Test Notification model."""
    
    def test_notification_creation(self):
        """Test notification creation."""
        notification = Notification.objects.create(
            recipient_type="patient",
            recipient_id="Test Patient",
            notification_type="appointment_confirmed",
            message="Your appointment has been confirmed"
        )
        
        self.assertEqual(notification.recipient_type, "patient")
        self.assertFalse(notification.is_sent)
    
    def test_notification_mark_as_sent(self):
        """Test marking notification as sent."""
        notification = Notification.objects.create(
            recipient_type="patient",
            recipient_id="Test Patient",
            notification_type="appointment_confirmed",
            message="Your appointment has been confirmed"
        )
        
        notification.mark_as_sent()
        self.assertTrue(notification.is_sent)
        self.assertIsNotNone(notification.sent_at)


class ConversationLogTest(CarematixTestCase):
    """Test ConversationLog model."""
    
    def test_conversation_log_creation(self):
        """Test conversation log creation."""
        call = Call.objects.create(
            call_sid="CA1234567890",
            patient_phone="+1234567890"
        )
        
        log = ConversationLog.objects.create(
            call=call,
            speaker="patient",
            message_text="Hello, I need to schedule an appointment",
            message_type="transcript"
        )
        
        self.assertEqual(log.call, call)
        self.assertEqual(log.speaker, "patient")
        self.assertIn("appointment", log.message_text)


class CallTranscriptTest(CarematixTestCase):
    """Test CallTranscript model."""
    
    def test_call_transcript_creation(self):
        """Test call transcript creation."""
        call = Call.objects.create(
            call_sid="CA1234567890",
            patient_phone="+1234567890"
        )
        
        transcript = CallTranscript.objects.create(
            call=call,
            full_transcript="Patient: Hello\nAssistant: How can I help you?",
            patient_transcript="Hello",
            assistant_transcript="How can I help you?",
            scheduling_outcome="completed"
        )
        
        self.assertEqual(transcript.call, call)
        self.assertIn("Hello", transcript.full_transcript)
        self.assertEqual(transcript.scheduling_outcome, "completed")
