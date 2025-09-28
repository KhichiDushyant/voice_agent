# Carematix Django Project Structure

## 📁 Project Structure

```
carematix/
├── manage.py                          # Django management script
├── run_server.py                      # Custom server startup script
├── requirements.txt                   # Python dependencies
├── README.md                          # Project documentation
├── env.example                        # Environment variables example
├── PROJECT_STRUCTURE.md               # This file
│
├── carematix/                         # Django project settings
│   ├── __init__.py
│   ├── settings.py                    # Development settings
│   ├── settings_production.py         # Production settings
│   ├── urls.py                        # Main URL configuration
│   ├── wsgi.py                        # WSGI configuration
│   └── asgi.py                        # ASGI configuration for WebSockets
│
├── carematix_app/                     # Main Django app
│   ├── __init__.py
│   ├── apps.py                        # App configuration
│   ├── models.py                      # Database models
│   ├── views.py                       # API views
│   ├── urls.py                        # App URL configuration
│   ├── admin.py                       # Django admin configuration
│   ├── consumers.py                   # WebSocket consumers
│   ├── routing.py                     # WebSocket routing
│   ├── database_helper.py             # Database helper for voice agent
│   ├── tests.py                       # Test cases
│   └── management/
│       └── commands/
│           ├── __init__.py
│           ├── setup_sample_data.py   # Sample data setup
│           └── init_project.py        # Project initialization
│
├── templates/                         # Django templates
│   └── dashboard.html                 # Main dashboard template
│
└── static/                           # Static files
    ├── css/
    │   └── dashboard.css              # Dashboard styles
    ├── js/
    │   └── dashboard.js               # Dashboard JavaScript
    └── images/                        # Static images (empty)
```

## 🗄️ Database Models

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

## 🔌 API Endpoints

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

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

3. **Initialize project**:
   ```bash
   python manage.py init_project --create-superuser
   ```

4. **Start server**:
   ```bash
   python run_server.py
   ```

## 🔧 Management Commands

- `python manage.py init_project` - Initialize project with migrations and sample data
- `python manage.py setup_sample_data` - Set up sample data
- `python manage.py runserver` - Start development server
- `python manage.py test` - Run tests
- `python manage.py migrate` - Run database migrations

## 🌐 WebSocket Support

The project uses Django Channels for WebSocket support:
- **Twilio Integration**: Receives audio data from Twilio
- **OpenAI Integration**: Sends audio to OpenAI and receives responses
- **Real-time Processing**: Processes audio in real-time
- **Database Integration**: Updates database during conversation

## 📊 Admin Interface

Access the Django admin at `/admin/` to manage:
- Patients
- Nurses
- Appointments
- Calls
- Notifications
- All other data

## 🧪 Testing

Run the test suite:
```bash
python manage.py test
```

The test suite includes:
- Model tests
- API endpoint tests
- Database helper tests
- WebSocket functionality tests
- Integration tests

## 🔒 Security

- Environment variables for sensitive data
- CORS configuration
- CSRF protection
- Production security settings
- HTTPS support

## 📈 Monitoring

- Comprehensive logging
- Call tracking
- Conversation logging
- Database monitoring
- Error tracking

## 🚀 Deployment

For production deployment:
1. Use `settings_production.py`
2. Set up PostgreSQL database
3. Configure Redis for WebSockets
4. Set up proper environment variables
5. Use a production WSGI server like Gunicorn
6. Set up reverse proxy with Nginx

## 📝 Notes

- All FastAPI code has been converted to Django
- WebSocket support via Django Channels
- Real-time database integration maintained
- All original functionality preserved
- Better admin interface and management tools
- Comprehensive test suite
- Production-ready configuration
