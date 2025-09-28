# Carematix AI Voice Assistant - Healthcare Scheduling System

## Overview

Carematix is a professional healthcare scheduling system that uses AI voice assistance to help patients schedule calls with qualified nurses. The system is built with Django and integrates with OpenAI's Realtime API for voice processing and Twilio for phone call management. It provides a complete healthcare workflow including patient management, nurse scheduling, appointment booking, and real-time voice interactions through WebSockets.

The system enables patients to call in and speak with an AI assistant that can access the database in real-time to check nurse availability, schedule appointments, and manage healthcare workflows. All conversations are transcribed and stored for record-keeping and quality assurance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
The system uses Django as the main web framework with Django REST Framework for API endpoints. The architecture follows a traditional MVC pattern with additional WebSocket support for real-time communication.

**Core Components:**
- **Django Application:** Main web framework handling HTTP requests, database operations, and business logic
- **WebSocket Layer:** Django Channels provides WebSocket support for real-time voice communication
- **Database Models:** Comprehensive healthcare data models including Patient, Nurse, Appointment, Call logging, and availability management
- **Voice Integration:** Custom WebSocket consumer that bridges Twilio phone calls with OpenAI's Realtime API
- **Management Commands:** Automated setup and sample data generation

**Database Design:**
The system uses SQLite for development with PostgreSQL support for production. Key models include:
- Patient management with medical conditions and contact information
- Nurse profiles with specializations and license tracking
- Flexible availability system with overrides for schedule changes
- Comprehensive appointment and call logging
- Real-time conversation transcription storage

**WebSocket Architecture:**
The MediaStreamConsumer handles bidirectional communication between Twilio (phone calls) and OpenAI (AI processing). It manages audio streaming, conversation logging, and database integration during live calls.

**API Structure:**
RESTful API endpoints provide full CRUD operations for all healthcare entities, with specialized endpoints for scheduling, availability checking, and call management.

### Frontend Architecture
The system includes a modern dashboard built with vanilla JavaScript, providing a responsive interface for healthcare administrators.

**Dashboard Features:**
- Real-time data visualization with charts and metrics
- Patient and nurse management interfaces
- Appointment scheduling and tracking
- Call history and transcript viewing
- Analytics and reporting capabilities

**UI Framework:**
- Responsive CSS Grid and Flexbox layout
- Font Awesome icons for consistent visual language
- Modern color scheme optimized for healthcare environments
- Mobile-first responsive design

### Voice Processing Architecture
The voice system creates a seamless bridge between traditional phone calls and modern AI assistants.

**Voice Flow:**
1. Twilio receives phone calls and opens WebSocket connection
2. MediaStreamConsumer manages the connection and initializes database helper
3. OpenAI Realtime API processes voice input and generates responses
4. Database helper provides real-time access to patient/nurse data during conversations
5. All audio and text is logged for compliance and quality assurance

**Database Integration During Calls:**
The VoiceAgentDatabaseHelper class provides real-time database access during voice conversations, enabling the AI to check availability, schedule appointments, and retrieve patient information while speaking.

### Production Architecture
The system is designed to scale from development to production environments.

**Development Setup:**
- SQLite database for simplicity
- In-memory channel layers for WebSocket support
- Local file storage for audio recordings
- Built-in Django development server

**Production Configuration:**
- PostgreSQL database with connection pooling
- Redis-backed channel layers for multi-process WebSocket support
- Secure HTTPS configuration with proper security headers
- Static file serving optimization

## External Dependencies

### Core Framework Dependencies
- **Django 4.2+:** Web framework providing ORM, admin interface, and core functionality
- **Django REST Framework 3.14+:** API framework for RESTful endpoints and serialization
- **Django Channels 4.0+:** WebSocket support for real-time communication
- **Django CORS Headers:** Cross-origin resource sharing for frontend integration

### Voice and Communication Services
- **Twilio API:** Phone call management, SMS capabilities, and WebSocket media streaming
- **OpenAI Realtime API:** Voice processing, speech-to-text, text-to-speech, and conversation AI
- **WebSockets Library:** Real-time bidirectional communication between services

### Development and Deployment
- **Python-dotenv:** Environment variable management for configuration
- **SQLite:** Development database (included with Python)
- **PostgreSQL:** Production database (configured in production settings)

### Optional Production Dependencies
- **Redis:** Production channel layer backend for WebSocket scaling (commented out for development simplicity)
- **Channels-Redis:** Redis integration for Django Channels (optional)

### Third-Party Integrations
- **Twilio Voice API:** Handles incoming and outgoing phone calls with WebSocket streaming
- **OpenAI Realtime API:** Provides voice understanding and generation capabilities
- **Email Services:** Django's built-in email backend for notifications (configurable for production SMTP)

The system is designed to minimize external dependencies while providing robust healthcare scheduling capabilities. The modular architecture allows for easy scaling and integration with additional healthcare systems as needed.