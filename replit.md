# Carematix Healthcare AI Voice Assistant

## Overview

Carematix is a comprehensive healthcare scheduling platform that integrates AI voice assistance with traditional web interfaces. The system enables patients to schedule appointments with qualified nurses through natural voice conversations while providing healthcare administrators with a complete dashboard for managing patients, nurses, appointments, and call analytics. Built with Django and leveraging OpenAI's real-time voice API, the platform bridges the gap between modern AI technology and healthcare workflow management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Django 4.2+**: Chosen for its robust ORM, built-in admin interface, and excellent REST framework integration. Django provides rapid development capabilities with production-ready features out of the box.
- **Django REST Framework**: Powers the API endpoints for frontend-backend communication and external integrations.
- **Django Channels**: Enables WebSocket support for real-time communication between Twilio voice calls and OpenAI's voice API.

### Database Design
- **SQLite**: Used for development and small deployments, with PostgreSQL configuration available for production scaling.
- **Comprehensive Healthcare Models**: Patient, Nurse, PatientNurseAssignment, Appointment, Call tracking, and ConversationLog models provide complete healthcare workflow management.
- **Availability Management**: Complex scheduling system with NurseAvailability and NurseAvailabilityOverride models for flexible appointment scheduling.

### Real-time Communication Architecture
- **WebSocket Integration**: Custom MediaStreamConsumer handles bidirectional audio streaming between Twilio and OpenAI.
- **In-Memory Channel Layer**: Simplified development setup without Redis dependency, though Redis configuration is available for production scaling.
- **Voice Agent Database Helper**: Specialized database interface that allows the AI voice assistant to query and update appointment data in real-time during conversations.

### Frontend Architecture
- **Server-Side Templates**: Django templates with modern JavaScript for dashboard functionality.
- **Real-time Dashboard**: Live updates using AJAX polling with admin interface for data management.
- **Responsive Design**: Mobile-friendly interface using modern CSS grid and flexbox layouts.

### Voice Processing Pipeline
- **Twilio Integration**: Handles inbound/outbound phone calls and audio streaming.
- **OpenAI Real-time API**: Processes voice conversations with contextual healthcare knowledge.
- **Audio Recording**: Captures and stores complete conversation audio in WAV format.
- **Transcript Generation**: Automatic conversation transcription with speaker identification.

### Development vs Production Configuration
- **Settings Split**: Separate development and production settings with environment variable configuration.
- **Database Flexibility**: SQLite for development, PostgreSQL for production with automatic detection.
- **Security Settings**: Production-ready security configurations including HTTPS, HSTS, and secure cookies.

## External Dependencies

### Core Services
- **Twilio Voice API**: Telephony infrastructure for inbound/outbound calls and media streaming
- **OpenAI Real-time API**: AI voice processing and natural language understanding for appointment scheduling
- **OpenAI Standard API**: Fallback for text-based AI interactions and conversation analysis

### Python Packages
- **Django 4.2+**: Web framework and ORM
- **Django REST Framework**: API development and serialization
- **Django Channels**: WebSocket and async support
- **Django CORS Headers**: Cross-origin request handling
- **Twilio Python SDK**: Telephony integration
- **OpenAI Python Client**: AI service integration
- **WebSockets**: Real-time communication support
- **Python-dotenv**: Environment variable management

### Optional Production Dependencies
- **PostgreSQL**: Production database (configured but not required)
- **Redis**: Channel layer scaling and caching (configured but not required, uses in-memory alternatives)
- **Channels-Redis**: Redis integration for Django Channels (optional)

### Development Tools
- **Django Admin**: Built-in administrative interface for data management
- **Django Management Commands**: Custom commands for project initialization and sample data setup
- **Django Debug Toolbar**: Development debugging (available but not installed by default)