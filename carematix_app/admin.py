"""
Django admin configuration for Carematix models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Patient, Nurse, PatientNurseAssignment, NurseAvailability, 
    NurseAvailabilityOverride, Appointment, Call, ConversationLog, 
    CallTranscript, Notification
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'date_of_birth', 'created_at']
    list_filter = ['created_at', 'date_of_birth']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['specialization', 'is_active', 'created_at']
    search_fields = ['name', 'specialization', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PatientNurseAssignment)
class PatientNurseAssignmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'nurse', 'assignment_date', 'is_primary', 'created_at']
    list_filter = ['assignment_date', 'is_primary', 'created_at']
    search_fields = ['patient__name', 'nurse__name']
    readonly_fields = ['created_at']


@admin.register(NurseAvailability)
class NurseAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['nurse', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available', 'nurse__specialization']
    search_fields = ['nurse__name']


@admin.register(NurseAvailabilityOverride)
class NurseAvailabilityOverrideAdmin(admin.ModelAdmin):
    list_display = ['nurse', 'override_date', 'start_time', 'end_time', 'is_available', 'reason']
    list_filter = ['override_date', 'is_available', 'nurse__specialization']
    search_fields = ['nurse__name', 'reason']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'nurse', 'appointment_date', 'appointment_time', 'status', 'appointment_type']
    list_filter = ['status', 'appointment_type', 'appointment_date', 'nurse__specialization']
    search_fields = ['patient__name', 'nurse__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'appointment_date'


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['call_sid', 'patient_phone', 'patient', 'call_direction', 'call_status', 'call_duration', 'start_time']
    list_filter = ['call_direction', 'call_status', 'appointment_scheduled', 'start_time']
    search_fields = ['call_sid', 'patient_phone', 'patient__name']
    readonly_fields = ['start_time', 'end_time']
    date_hierarchy = 'start_time'

    def get_duration_display(self, obj):
        if obj.call_duration:
            minutes, seconds = divmod(obj.call_duration, 60)
            return f"{minutes}m {seconds}s"
        return "N/A"
    get_duration_display.short_description = 'Duration'


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ['call', 'speaker', 'message_type', 'timestamp']
    list_filter = ['speaker', 'message_type', 'timestamp']
    search_fields = ['call__call_sid', 'message_text']
    readonly_fields = ['timestamp']


@admin.register(CallTranscript)
class CallTranscriptAdmin(admin.ModelAdmin):
    list_display = ['call', 'scheduling_outcome', 'created_at']
    list_filter = ['scheduling_outcome', 'created_at']
    search_fields = ['call__call_sid']
    readonly_fields = ['created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient_type', 'recipient_id', 'notification_type', 'is_sent', 'created_at']
    list_filter = ['recipient_type', 'notification_type', 'is_sent', 'created_at']
    search_fields = ['recipient_id', 'message']
    readonly_fields = ['created_at', 'sent_at']

