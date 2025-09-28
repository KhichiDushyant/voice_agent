#!/usr/bin/env python
"""
Run the Django development server with ASGI support for WebSockets.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carematix.settings")
    django.setup()
    
    # Run migrations first
    print("Running database migrations...")
    execute_from_command_line(["manage.py", "migrate"])
    
    # Set up sample data if needed
    print("Setting up sample data...")
    execute_from_command_line(["manage.py", "setup_sample_data"])
    
    # Start the server
    print("Starting Django server with ASGI support...")
    execute_from_command_line(["manage.py", "runserver", "0.0.0.0:5000"])
