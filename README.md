# Carematix AI Voice Assistant - Django Version

A professional healthcare scheduling system that uses AI voice assistance to help patients schedule calls with qualified nurses. Built with Django, Django REST Framework, Django Channels, Twilio, and OpenAI with real-time database integration.

## 🏥 Features

- **AI Voice Assistant**: Professional Carematix healthcare assistant for nurse scheduling
- **OpenAI Voice Only**: All voice processing handled by OpenAI, no Twilio voice dependencies
- **Full Call Transcription**: Complete conversation capture and storage in SQLite database
- **Direct OpenAI Integration**: Seamless real-time AI communication via WebSockets
- **Nurse Management**: Complete database of nurses with specializations and availability
- **Call Logging**: Comprehensive database logging for all calls and conversations
- **Real-time Scheduling**: Live availability checking and appointment scheduling
- **Appointment Scheduling Workflow**: Complete automated appointment scheduling between patients and nurses
- **Patient-Nurse Assignment**: Automatic assignment of nurses to patients
- **Availability Management**: Nurse availability schedules with overrides and conflicts checking
- **Notification System**: Automated notifications for both patients and nurses
- **Database Integration**: Real-time database access during voice conversations
- **REST API**: Full API for integration with other systems
- **Django Admin**: Complete admin interface for data management
- **WebSocket Support**: Real-time communication with Twilio and OpenAI

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Twilio account with phone number
- OpenAI API key with Realtime API access
- ~~Redis server~~ (No longer required - using in-memory channel layer)

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd self_speech_call
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**:
   Create a `.env` file with your credentials:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
   OPENAI_API_KEY=your_openai_api_key
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   REDIS_URL=redis://127.0.0.1:6379/1
   NGROK_URL=your_ngrok_url
   ```

5. **Run migrations and setup sample data**:
   ```bash
   python manage.py migrate
   python manage.py setup_sample_data
   ```

### Running the Application

1. **Start the Django server** (Redis no longer required):
   ```bash
   python run_server.py
   ```
   
   Or manually:
   ```bash
   python manage.py migrate
   python manage.py setup_sample_data
   python manage.py runserver 0.0.0.0:8000
   ```

3. **Access the admin interface**:
   - URL: http://localhost:8000/admin/
   - Create a superuser: `python manage.py createsuperuser`

## 📊 Database Schema

The system uses Django ORM with SQLite database. All models are defined in `carematix_app/models.py`:

### Core Models

- **Patient**: Patient information and medical conditions
- **Nurse**: Nurse information and specializations
- **PatientNurseAssignment**: Assignment of nurses to patients
- **NurseAvailability**: Regular availability schedules
- **NurseAvailabilityOverride**: Override availability for specific dates
- **Appointment**: Scheduled appointments between patients and nurses
- **Call**: Voice call tracking and logging
- **ConversationLog**: Individual conversation messages
- **CallTranscript**: Complete call transcripts
- **Notification**: Notification system for patients and nurses

## 🔧 API Endpoints

### Health and Dashboard
- `GET /` - Health check endpoint
- `GET /dashboard/` - Dashboard HTML page

### Call Management
- `POST /make-call/` - Initiate outbound call
- `GET /incoming-call/` - Handle incoming calls
- `WebSocket /ws/media-stream/` - Real-time audio streaming

### Nurse Management
- `GET /nurses/available/` - Get available nurses
- `GET /nurses/{id}/availability/` - Get nurse availability
- `POST /calls/{id}/schedule/` - Schedule nurse for call

### Patient Management
- `GET /patients/{phone}/assigned-nurse/` - Get patient's assigned nurse

### Appointment Management
- `GET /appointments/` - Get appointments with filters
- `POST /appointments/` - Create new appointment
- `GET /appointments/{id}/` - Get appointment details

### Data Access
- `GET /calls/history/` - Get call history
- `GET /calls/{id}/transcript/` - Get call transcript
- `GET /calls/{id}/details/` - Get call details
- `GET /transcripts/` - Get all transcripts

### Testing
- `GET /test-openai/` - Test OpenAI connection

## 🎯 AI Assistant Capabilities

The Carematix AI assistant is specifically designed for healthcare scheduling with real-time database integration:

- **OpenAI Voice Processing**: All voice generation handled by OpenAI
- **Professional Healthcare Focus**: Specialized in nurse scheduling and patient care
- **Real-time Database Access**: Looks up patient information, nurse assignments, and availability
- **Specialization Matching**: Identifies appropriate nurse based on patient needs
- **Availability Checking**: Real-time nurse availability verification
- **Appointment Scheduling**: Books confirmed appointments with nurses
- **Empathetic Communication**: Caring, professional tone for healthcare context
- **Comprehensive Logging**: Detailed conversation and action logging

## 📅 Appointment Scheduling Workflow

The voice agent follows a structured workflow for appointment scheduling:

1. **Call Initiation**: Voice agent calls the patient
2. **Patient Identification**: Gets patient's phone number and looks up information
3. **Nurse Assignment**: Finds patient's assigned nurse from database
4. **Time Preference Collection**: Asks patient what time they prefer
5. **Availability Checking**: Verifies nurse's availability for requested time
6. **Scheduling or Alternatives**: Confirms appointment or suggests alternatives
7. **Confirmation Process**: Repeats appointment details back to patient
8. **Notification System**: Creates notifications for patient and nurse
9. **Call Completion**: Ends call professionally

## 🔄 WebSocket Integration

The system uses Django Channels for WebSocket support:

- **Twilio Integration**: Receives audio data from Twilio
- **OpenAI Integration**: Sends audio to OpenAI and receives responses
- **Real-time Processing**: Processes audio in real-time
- **Database Integration**: Updates database during conversation
- **Conversation Logging**: Logs all conversation parts

## 🧪 Testing

### Run Tests
```bash
python manage.py test
```

### Test Coverage
The test suite includes:
- Model tests
- API endpoint tests
- Database helper tests
- WebSocket functionality tests
- Integration tests

## 🛠️ Management Commands

### Setup Sample Data
```bash
python manage.py setup_sample_data
```

This creates:
- 4 sample patients with different medical conditions
- 5 nurses with different specializations
- Availability schedules (Mon-Fri 9AM-5PM, Sat-Sun 10AM-2PM)
- Patient-nurse assignments
- Sample appointments

## 📱 Sample Data

The system comes pre-loaded with sample data:

- **4 Patients** with different medical conditions:
  - John Smith (Diabetes, Hypertension)
  - Sarah Johnson (Asthma, Allergies)
  - Robert Brown (Heart Disease, Arthritis)
  - Emily Davis (Anxiety, Depression)

- **5 Nurses** with different specializations:
  - Dr. Alice Wilson (General Care)
  - Dr. Michael Chen (Cardiology)
  - Dr. Lisa Rodriguez (Pediatrics)
  - Dr. James Thompson (Geriatrics)
  - Dr. Maria Garcia (Mental Health)

## 🔧 Configuration

### Environment Variables
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `OPENAI_API_KEY`: Required for AI voice processing
- `TWILIO_ACCOUNT_SID`: Twilio account identifier
- `TWILIO_AUTH_TOKEN`: Twilio authentication token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number
- ~~`REDIS_URL`~~: ~~Redis server URL~~ (No longer required - using in-memory)
- `NGROK_URL`: Ngrok URL for webhook callbacks

### Database Configuration
- Database: SQLite (default)
- Auto-migration on first run
- Sample data creation included

## 🔒 Security Considerations

- Store sensitive credentials in `.env` file
- Use HTTPS in production
- Implement proper authentication for API endpoints
- Regular database backups recommended
- Follow healthcare data privacy regulations (HIPAA compliance)

## 📈 Monitoring and Logging

### Call Logging
- All calls logged with timestamps and duration
- Conversation transcripts stored
- Call success/failure tracking
- Nurse assignment logging
- Real-time status updates

### Database Monitoring
- Appointment creation and updates
- Nurse availability changes
- Patient-nurse assignments
- Notification delivery status

## 🚨 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check Django Channels configuration
   - Verify ASGI application is properly configured

2. **OpenAI Connection Error**
   - Verify OPENAI_API_KEY is correct
   - Check API key has Realtime API access

4. **Twilio Call Failed**
   - Verify Twilio credentials
   - Check webhook URL configuration

### Debug Commands

```bash
# Check server health
curl http://localhost:8000/

# Test OpenAI connection
curl http://localhost:8000/test-openai/

# Check available nurses
curl "http://localhost:8000/nurses/available/?date=2024-01-15"

# Check patient assignment
curl "http://localhost:8000/patients/+1234567890/assigned-nurse/"

# Check appointments
curl "http://localhost:8000/appointments/"
```

## 🔮 Future Enhancements

1. **SMS Notifications**: Send SMS confirmations to patients and nurses
2. **Calendar Integration**: Sync with Google Calendar or Outlook
3. **Recurring Appointments**: Support for recurring appointment schedules
4. **Waitlist Management**: Handle appointment waitlists
5. **Telehealth Integration**: Support for video call appointments
6. **Multi-language Support**: Support for multiple languages
7. **Advanced Analytics**: Detailed reporting and analytics dashboard
8. **Mobile App**: Native mobile application for patients and nurses
9. **AI Improvements**: Enhanced natural language understanding
10. **Integration APIs**: Connect with EHR systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python manage.py test`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the server health endpoint
- Review API documentation
- Run test suite for diagnostics
- Check logs for error details
- Review this documentation

---

**Carematix AI Voice Assistant - Django Version** - Professional healthcare scheduling made simple and efficient with real-time database integration.