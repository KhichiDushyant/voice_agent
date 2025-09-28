# Carematix AI Voice Assistant - Healthcare Scheduling System

## 📋 Project Overview
A professional healthcare AI voice assistant that calls patients to schedule appointments with qualified nurses. The system uses Django, OpenAI Realtime API, Twilio, and real-time database integration to provide complete conversation transcripts and call management.

## 🏥 Core Features
- **AI Voice Calling**: Automated calls to patients for nurse appointment scheduling
- **Complete Transcript Storage**: Full conversation recording with call-by-call transcripts
- **Patient Information Access**: Real-time patient data lookup during calls
- **Nurse Availability System**: Live availability checking and scheduling
- **Real-time Database**: Patient, nurse, appointment, and call management
- **Professional Dashboard**: Complete healthcare management interface

## 🚀 Current Setup Status
- ✅ **Django Server**: Running on port 5000 with ASGI/WebSocket support
- ✅ **Database**: SQLite with complete sample data (4 patients, 5 nurses)
- ✅ **Frontend Dashboard**: Professional healthcare interface working perfectly  
- ✅ **API Endpoints**: All REST endpoints functional for scheduling and transcripts
- ✅ **Sample Data**: Patients, nurses, and appointments ready for testing
- ⚠️ **Voice Calling**: Requires OpenAI API key to enable voice functionality
- ⚠️ **Twilio Integration**: Requires Twilio credentials for phone calling

## 🔧 Required API Keys for Voice Calling
To enable the voice calling functionality, you need:

1. **OpenAI API Key**: For Realtime voice processing
   - Used for: AI voice conversations with patients
   - Required for: Voice scheduling and transcript generation

2. **Twilio Credentials**: For making phone calls
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN  
   - TWILIO_PHONE_NUMBER
   - Used for: Actual phone calls to patients

## 📊 Sample Data Ready
- **Patients**: John Smith, Sarah Johnson, Robert Brown, Emily Davis
- **Nurses**: Dr. Alice Wilson, Dr. Michael Chen, Dr. Lisa Rodriguez, Dr. James Thompson, Dr. Maria Garcia
- **Appointments**: 4 scheduled appointments with nurse assignments
- **Medical Conditions**: Diabetes, asthma, heart disease, mental health coverage

## 🎯 How Voice Calling Works
1. **Patient Call**: System calls patient phone number using Twilio
2. **AI Assistant**: OpenAI Realtime API handles voice conversation
3. **Patient Data Lookup**: System accesses patient info and assigned nurse
4. **Availability Check**: Real-time nurse availability verification
5. **Appointment Scheduling**: Books confirmed appointments in database
6. **Transcript Storage**: Complete conversation saved with call logs
7. **Notifications**: Both patient and nurse receive confirmations

## 🛠️ Technical Architecture
- **Backend**: Django 5.2+ with Django REST Framework
- **WebSockets**: Django Channels for real-time communication
- **Database**: SQLite with comprehensive healthcare models
- **Voice**: OpenAI Realtime API for voice processing
- **Calling**: Twilio for phone operations
- **Frontend**: Modern JavaScript dashboard with real-time updates

## 📱 Dashboard Features
- **Real-time Statistics**: Patient, nurse, appointment, and call metrics
- **Call History**: Complete call logs with transcripts
- **Appointment Management**: Schedule and track nurse meetings
- **Patient Records**: Medical conditions and contact information
- **Nurse Scheduling**: Availability management and assignment tracking

## 🔒 Security & Privacy
- **HIPAA Considerations**: All conversations and data properly logged
- **Secure Storage**: Patient data protected with proper access controls
- **API Security**: Environment variables for sensitive credentials
- **Transcript Logging**: Complete audit trail for all interactions

## 🚀 Recent Changes
- **2025-09-28**: Initial Replit setup completed
- **Voice Integration**: OpenAI integration added and configured
- **Dashboard Fixed**: JavaScript errors resolved, full functionality
- **Database Setup**: Sample healthcare data loaded and verified
- **Deployment Ready**: Autoscale deployment configured

## 📞 Ready to Test
Once you add your OpenAI API key:
1. Navigate to `/dashboard/` to see the management interface
2. Use the `/make-call/` endpoint to initiate patient calls
3. Monitor real-time transcripts in the call history
4. Track appointments and nurse scheduling

## 🔮 Next Steps
1. Add OpenAI API key to enable voice calling
2. Configure Twilio credentials for phone operations  
3. Test voice calling with sample patients
4. Monitor transcript generation and storage
5. Deploy to production when ready

---
**System Status**: ✅ Ready for voice calling (pending API keys)