# Overview

Carematix is a Django-based healthcare scheduling platform that uses AI voice assistance to help patients schedule calls with qualified nurses. The system integrates OpenAI's Realtime API for voice processing, Twilio for telecommunications, and provides a comprehensive healthcare management solution with real-time WebSocket communication, appointment scheduling, and complete call transcription capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
Built on Django 4.2+ with Django REST Framework for API endpoints. Uses Django Channels for WebSocket support to handle real-time communication between Twilio and OpenAI. The system follows a standard Django app structure with `carematix` as the main project and `carematix_app` containing all business logic.

## Database Design
Uses SQLite for development (easily switchable to PostgreSQL for production). Core models include Patient, Nurse, PatientNurseAssignment, NurseAvailability, Appointment, Call, and CallTranscript. The database helper (`database_helper.py`) provides voice agent integration for real-time database access during calls.

## Real-time Communication
WebSocket architecture using Django Channels with in-memory channel layers for development (Redis-ready for production scaling). The `MediaStreamConsumer` handles bidirectional communication between Twilio and OpenAI, managing audio streaming and conversation logging.

## Voice Processing
Integrates OpenAI's Realtime API for all voice processing, eliminating Twilio voice dependencies. Audio data flows through WebSockets for real-time conversation handling with complete transcription storage.

## Authentication & Security
Uses Django's built-in authentication system with CORS headers configured for API access. Production settings include comprehensive security headers and HTTPS configuration.

## Frontend Architecture
Single-page application using vanilla JavaScript with a modern healthcare dashboard. Responsive design with real-time data updates and comprehensive patient/nurse/appointment management interfaces.

## API Structure
RESTful API endpoints for all CRUD operations on patients, nurses, appointments, and calls. Includes specialized endpoints for nurse availability checking, appointment scheduling, and call transcript retrieval.

# External Dependencies

## Core Services
- **OpenAI**: Realtime API for voice processing and AI conversation handling
- **Twilio**: Telecommunications service for phone call management and WebSocket media streaming

## Database
- **SQLite**: Default development database (production-ready PostgreSQL configuration available)

## Real-time Communication
- **Django Channels**: WebSocket support for real-time communication
- **In-memory Channel Layer**: Development WebSocket backend (Redis configuration available for production scaling)

## Python Libraries
- **Django 4.2+**: Web framework
- **Django REST Framework**: API development
- **python-dotenv**: Environment variable management
- **websockets**: WebSocket client support
- **django-cors-headers**: CORS handling for API access

## Frontend Dependencies
- **Font Awesome**: Icon library
- **Google Fonts (Inter)**: Typography
- **Chart.js**: Dashboard analytics and visualization

## Production Considerations
Redis configuration is available but commented out for simplified development setup. The system is designed to scale with Redis for multi-process deployments and persistent caching.