"""
URL configuration for carematix_app.
"""

from django.urls import path, include
from . import views

urlpatterns = [
    # Health check and dashboard
    path('', views.index_page, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Testing
    path('test-openai/', views.test_openai_connection, name='test_openai'),
    
    # Call management
    path('make-call/', views.make_outbound_call, name='make_call'),
    path('incoming-call/', views.handle_incoming_call, name='incoming_call'),
    
    # Nurse management
    path('nurses/available/', views.get_available_nurses, name='available_nurses'),
    path('nurses/<int:nurse_id>/availability/', views.get_nurse_availability, name='nurse_availability'),
    path('calls/<int:call_id>/schedule/', views.schedule_nurse_call, name='schedule_nurse'),
    
    # Patient management
    path('patients/<str:patient_phone>/assigned-nurse/', views.get_patient_assigned_nurse, name='patient_assigned_nurse'),
    
    # Appointment management
    path('appointments/', views.get_appointments, name='appointments'),
    path('appointments/', views.create_appointment, name='create_appointment'),
    path('appointments/<int:appointment_id>/', views.get_appointment, name='appointment_detail'),
    
    # Notification management
    path('notifications/', views.create_notification, name='create_notification'),
    
    # Data access
    path('calls/history/', views.get_call_history, name='call_history'),
    path('calls/<int:call_id>/transcript/', views.get_call_transcript, name='call_transcript'),
    path('calls/<int:call_id>/details/', views.get_call_details, name='call_details'),
    path('transcripts/', views.get_all_transcripts, name='all_transcripts'),
    path('audio/<int:call_id>/<str:speaker>/', views.get_call_audio, name='call_audio'),
    
    # Testing endpoint for transcripts
    path('test-transcripts/', views.test_transcripts_page, name='test_transcripts'),
    
    # Dashboard API endpoints - RESTful design
    path('api/patients/', views.patients_api, name='patients_api'),
    path('api/patients/<int:patient_id>/', views.patient_detail_api, name='patient_detail_api'),
    path('api/nurses/', views.nurses_api, name='nurses_api'),
    path('api/nurses/<int:nurse_id>/', views.nurse_detail_api, name='nurse_detail_api'),
    path('api/appointments/', views.appointments_api, name='appointments_api'),
    path('api/appointments/<int:appointment_id>/', views.appointment_detail_api, name='appointment_detail_api'),
    path('api/calls/', views.get_all_calls, name='all_calls'),
    path('api/make-test-call/', views.make_test_call, name='make_test_call'),
    path('api/assign-nurse/', views.assign_nurse_to_patient, name='assign_nurse'),
    path('api/patients/<int:patient_id>/nurses/', views.get_patient_nurses, name='patient_nurses'),
    path('api/assign-nurse/<int:assignment_id>/', views.remove_nurse_assignment, name='remove_assignment'),
]

