"""
Django management command to set up sample data for the Carematix system.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from carematix_app.models import (
    Patient, Nurse, PatientNurseAssignment, NurseAvailability, 
    NurseAvailabilityOverride, Appointment
)


class Command(BaseCommand):
    help = 'Set up sample data for the Carematix healthcare scheduling system'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample data...')
        
        # Create patients
        patients = self.create_patients()
        
        # Create nurses
        nurses = self.create_nurses()
        
        # Set up nurse availability
        self.setup_nurse_availability(nurses)
        
        # Assign nurses to patients
        self.assign_nurses_to_patients(patients, nurses)
        
        # Create sample appointments
        self.create_sample_appointments(patients, nurses)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up sample data!')
        )

    def create_patients(self):
        """Create sample patients."""
        patients_data = [
            {
                'name': 'John Smith',
                'phone': '+1234567890',
                'email': 'john.smith@email.com',
                'date_of_birth': '1980-05-15',
                'medical_conditions': ['Diabetes', 'Hypertension']
            },
            {
                'name': 'Sarah Johnson',
                'phone': '+1234567891',
                'email': 'sarah.johnson@email.com',
                'date_of_birth': '1975-08-22',
                'medical_conditions': ['Asthma', 'Allergies']
            },
            {
                'name': 'Robert Brown',
                'phone': '+1234567892',
                'email': 'robert.brown@email.com',
                'date_of_birth': '1965-12-10',
                'medical_conditions': ['Heart Disease', 'Arthritis']
            },
            {
                'name': 'Emily Davis',
                'phone': '+1234567893',
                'email': 'emily.davis@email.com',
                'date_of_birth': '1990-03-28',
                'medical_conditions': ['Anxiety', 'Depression']
            }
        ]
        
        patients = []
        for patient_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                phone=patient_data['phone'],
                defaults=patient_data
            )
            patients.append(patient)
            if created:
                self.stdout.write(f'Created patient: {patient.name}')
            else:
                self.stdout.write(f'Patient already exists: {patient.name}')
        
        return patients

    def create_nurses(self):
        """Create sample nurses."""
        nurses_data = [
            {
                'name': 'Dr. Alice Wilson',
                'phone': '+1987654321',
                'email': 'alice.wilson@carematix.com',
                'specialization': 'General Care',
                'license_number': 'RN001'
            },
            {
                'name': 'Dr. Michael Chen',
                'phone': '+1987654322',
                'email': 'michael.chen@carematix.com',
                'specialization': 'Cardiology',
                'license_number': 'RN002'
            },
            {
                'name': 'Dr. Lisa Rodriguez',
                'phone': '+1987654323',
                'email': 'lisa.rodriguez@carematix.com',
                'specialization': 'Pediatrics',
                'license_number': 'RN003'
            },
            {
                'name': 'Dr. James Thompson',
                'phone': '+1987654324',
                'email': 'james.thompson@carematix.com',
                'specialization': 'Geriatrics',
                'license_number': 'RN004'
            },
            {
                'name': 'Dr. Maria Garcia',
                'phone': '+1987654325',
                'email': 'maria.garcia@carematix.com',
                'specialization': 'Mental Health',
                'license_number': 'RN005'
            }
        ]
        
        nurses = []
        for nurse_data in nurses_data:
            nurse, created = Nurse.objects.get_or_create(
                license_number=nurse_data['license_number'],
                defaults=nurse_data
            )
            nurses.append(nurse)
            if created:
                self.stdout.write(f'Created nurse: {nurse.name}')
            else:
                self.stdout.write(f'Nurse already exists: {nurse.name}')
        
        return nurses

    def setup_nurse_availability(self, nurses):
        """Set up nurse availability schedules."""
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for nurse in nurses:
            # Weekday availability: 9 AM - 5 PM
            for day in days_of_week[:5]:  # Monday to Friday
                availability, created = NurseAvailability.objects.get_or_create(
                    nurse=nurse,
                    day_of_week=day,
                    defaults={
                        'start_time': '09:00',
                        'end_time': '17:00',
                        'is_available': True
                    }
                )
                if created:
                    self.stdout.write(f'Set weekday availability for {nurse.name}: {day}')
            
            # Weekend availability: 10 AM - 2 PM
            for day in days_of_week[5:]:  # Saturday and Sunday
                availability, created = NurseAvailability.objects.get_or_create(
                    nurse=nurse,
                    day_of_week=day,
                    defaults={
                        'start_time': '10:00',
                        'end_time': '14:00',
                        'is_available': True
                    }
                )
                if created:
                    self.stdout.write(f'Set weekend availability for {nurse.name}: {day}')

    def assign_nurses_to_patients(self, patients, nurses):
        """Assign nurses to patients based on medical conditions."""
        assignments = [
            (patients[0], nurses[0]),  # John Smith -> Dr. Alice Wilson (General Care)
            (patients[1], nurses[2]),  # Sarah Johnson -> Dr. Lisa Rodriguez (Pediatrics)
            (patients[2], nurses[1]),  # Robert Brown -> Dr. Michael Chen (Cardiology)
            (patients[3], nurses[4]),  # Emily Davis -> Dr. Maria Garcia (Mental Health)
        ]
        
        for patient, nurse in assignments:
            assignment, created = PatientNurseAssignment.objects.get_or_create(
                patient=patient,
                nurse=nurse,
                assignment_date=timezone.now().date(),
                defaults={
                    'is_primary': True,
                    'notes': f'Primary assignment based on medical conditions: {patient.medical_conditions}'
                }
            )
            if created:
                self.stdout.write(f'Assigned {nurse.name} to {patient.name}')
            else:
                self.stdout.write(f'Assignment already exists: {nurse.name} -> {patient.name}')

    def create_sample_appointments(self, patients, nurses):
        """Create sample appointments."""
        today = timezone.now().date()
        
        sample_appointments = [
            {
                'patient': patients[0],
                'nurse': nurses[0],
                'appointment_date': today + timedelta(days=1),
                'appointment_time': '10:00',
                'duration_minutes': 30,
                'appointment_type': 'consultation',
                'notes': 'Follow-up for diabetes management'
            },
            {
                'patient': patients[1],
                'nurse': nurses[2],
                'appointment_date': today + timedelta(days=2),
                'appointment_time': '14:00',
                'duration_minutes': 45,
                'appointment_type': 'consultation',
                'notes': 'Asthma management review'
            },
            {
                'patient': patients[2],
                'nurse': nurses[1],
                'appointment_date': today + timedelta(days=3),
                'appointment_time': '09:30',
                'duration_minutes': 60,
                'appointment_type': 'consultation',
                'notes': 'Cardiac health assessment'
            },
            {
                'patient': patients[3],
                'nurse': nurses[4],
                'appointment_date': today + timedelta(days=4),
                'appointment_time': '11:00',
                'duration_minutes': 45,
                'appointment_type': 'consultation',
                'notes': 'Mental health check-in'
            }
        ]
        
        for appointment_data in sample_appointments:
            appointment, created = Appointment.objects.get_or_create(
                patient=appointment_data['patient'],
                nurse=appointment_data['nurse'],
                appointment_date=appointment_data['appointment_date'],
                appointment_time=appointment_data['appointment_time'],
                defaults=appointment_data
            )
            if created:
                self.stdout.write(f'Created appointment: {appointment.patient.name} -> {appointment.nurse.name} on {appointment.appointment_date}')
            else:
                self.stdout.write(f'Appointment already exists: {appointment.patient.name} -> {appointment.nurse.name}')
