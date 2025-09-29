"""
Management command to set up sample nurse availability data.
"""

from django.core.management.base import BaseCommand
from datetime import time
from carematix_app.models import Nurse, NurseAvailability


class Command(BaseCommand):
    help = 'Set up sample nurse availability data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample nurse availability data...')
        
        # Get all nurses
        nurses = Nurse.objects.all()
        
        if not nurses.exists():
            self.stdout.write(self.style.ERROR('No nurses found in database. Please create nurses first.'))
            return
        
        # Define availability for each day
        availability_schedule = {
            'Monday': (time(9, 0), time(17, 0)),    # 9 AM to 5 PM
            'Tuesday': (time(9, 0), time(17, 0)),   # 9 AM to 5 PM
            'Wednesday': (time(9, 0), time(17, 0)), # 9 AM to 5 PM
            'Thursday': (time(9, 0), time(17, 0)),  # 9 AM to 5 PM
            'Friday': (time(9, 0), time(17, 0)),    # 9 AM to 5 PM
            'Saturday': (time(10, 0), time(14, 0)), # 10 AM to 2 PM
            'Sunday': (time(10, 0), time(14, 0)),   # 10 AM to 2 PM
        }
        
        created_count = 0
        updated_count = 0
        
        for nurse in nurses:
            self.stdout.write(f'Setting up availability for {nurse.name}...')
            
            for day, (start_time, end_time) in availability_schedule.items():
                availability, created = NurseAvailability.objects.get_or_create(
                    nurse=nurse,
                    day_of_week=day,
                    defaults={
                        'start_time': start_time,
                        'end_time': end_time,
                        'is_available': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  Created availability for {day}: {start_time} - {end_time}')
                else:
                    # Update existing availability
                    availability.start_time = start_time
                    availability.end_time = end_time
                    availability.is_available = True
                    availability.save()
                    updated_count += 1
                    self.stdout.write(f'  Updated availability for {day}: {start_time} - {end_time}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up availability data. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
