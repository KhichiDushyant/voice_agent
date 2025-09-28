"""
Django models for the Carematix healthcare scheduling system.
"""

import json
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta


class Patient(models.Model):
    """Patient model for storing patient information."""
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    medical_conditions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def get_medical_conditions_display(self):
        """Return medical conditions as a readable string."""
        if isinstance(self.medical_conditions, list):
            return ', '.join(self.medical_conditions)
        return str(self.medical_conditions)


class Nurse(models.Model):
    """Nurse model for storing nurse information."""
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.specialization})"


class PatientNurseAssignment(models.Model):
    """Assignment of nurses to patients."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='nurse_assignments')
    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='patient_assignments')
    assignment_date = models.DateField()
    is_primary = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['patient', 'nurse', 'assignment_date']
        ordering = ['-assignment_date', '-is_primary']

    def __str__(self):
        return f"{self.patient.name} - {self.nurse.name} ({self.assignment_date})"


class NurseAvailability(models.Model):
    """Regular availability schedule for nurses."""
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['nurse', 'day_of_week']

    def __str__(self):
        return f"{self.nurse.name} - {self.day_of_week} {self.start_time}-{self.end_time}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")


class NurseAvailabilityOverride(models.Model):
    """Override availability for specific dates."""
    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='availability_overrides')
    override_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    is_available = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['nurse', 'override_date']

    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.nurse.name} - {self.override_date} ({status})"


class Appointment(models.Model):
    """Appointment model for scheduling nurse meetings."""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    APPOINTMENT_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('routine', 'Routine'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='consultation')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']

    def __str__(self):
        return f"{self.patient.name} - {self.nurse.name} ({self.appointment_date} {self.appointment_time})"

    def get_end_time(self):
        """Calculate appointment end time."""
        start_datetime = datetime.combine(self.appointment_date, self.appointment_time)
        end_datetime = start_datetime + timedelta(minutes=self.duration_minutes)
        return end_datetime.time()

    def clean(self):
        if self.appointment_date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past.")


class Call(models.Model):
    """Call model for tracking voice calls."""
    CALL_DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]

    CALL_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('busy', 'Busy'),
        ('no_answer', 'No Answer'),
    ]

    call_sid = models.CharField(max_length=100, unique=True)
    patient_phone = models.CharField(max_length=20)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    call_direction = models.CharField(max_length=10, choices=CALL_DIRECTION_CHOICES, default='outbound')
    call_status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='initiated')
    call_duration = models.IntegerField(null=True, blank=True)  # Duration in seconds
    appointment_scheduled = models.BooleanField(default=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Call {self.call_sid} - {self.patient_phone} ({self.call_status})"

    def get_duration_display(self):
        """Return call duration in a readable format."""
        if self.call_duration:
            minutes, seconds = divmod(self.call_duration, 60)
            return f"{minutes}m {seconds}s"
        return "N/A"


class ConversationLog(models.Model):
    """Log individual conversation messages."""
    MESSAGE_TYPE_CHOICES = [
        ('transcript', 'Transcript'),
        ('action', 'Action'),
        ('database', 'Database'),
        ('system', 'System'),
    ]

    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='conversation_logs')
    speaker = models.CharField(max_length=20)  # patient, assistant, system
    message_text = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='transcript')
    intent = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.speaker}: {self.message_text[:50]}..."


class CallTranscript(models.Model):
    """Store complete call transcripts."""
    call = models.OneToOneField(Call, on_delete=models.CASCADE, related_name='transcript')
    full_transcript = models.TextField()
    patient_transcript = models.TextField()
    assistant_transcript = models.TextField()
    appointment_summary = models.TextField(blank=True, null=True)
    scheduling_outcome = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript for Call {self.call.call_sid}"


class Notification(models.Model):
    """Notification system for patients and nurses."""
    RECIPIENT_TYPE_CHOICES = [
        ('patient', 'Patient'),
        ('nurse', 'Nurse'),
    ]

    NOTIFICATION_TYPE_CHOICES = [
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('appointment_assigned', 'Appointment Assigned'),
        ('general', 'General'),
    ]

    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPE_CHOICES)
    recipient_id = models.CharField(max_length=100)  # Can be patient name, nurse name, etc.
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.TextField()
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient_type.title()}: {self.message[:50]}..."

    def mark_as_sent(self):
        """Mark notification as sent."""
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save()

