"""
Management command to set up nurse availability data.
"""
from django.core.management.base import BaseCommand
from carematix_app.models import Nurse, NurseAvailability
from datetime import time


class Command(BaseCommand):
    help = 'Set up default nurse availability for all nurses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--extended',
            action='store_true',
            help='Set up extended availability (24/7)',
        )

    def handle(self, *args, **options):
        extended = options['extended']
        
        # Get all active nurses
        nurses = Nurse.objects.filter(is_active=True)
        
        if not nurses.exists():
            self.stdout.write(
                self.style.WARNING('No active nurses found. Please add nurses first.')
            )
            return
        
        # Days of the week
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Set up availability for each nurse
        for nurse in nurses:
            self.stdout.write(f'Setting up availability for {nurse.name}...')
            
            for day in days:
                # Check if availability already exists
                if NurseAvailability.objects.filter(nurse=nurse, day_of_week=day).exists():
                    self.stdout.write(f'  {day}: Already exists, skipping')
                    continue
                
                if extended:
                    # 24/7 availability
                    start_time = time(0, 0)  # Midnight
                    end_time = time(23, 59)  # 11:59 PM
                else:
                    # Regular business hours with some variation
                    if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                        start_time = time(8, 0)   # 8:00 AM
                        end_time = time(17, 0)   # 5:00 PM
                    elif day == 'Saturday':
                        start_time = time(9, 0)   # 9:00 AM
                        end_time = time(15, 0)   # 3:00 PM
                    else:  # Sunday
                        start_time = time(10, 0)  # 10:00 AM
                        end_time = time(14, 0)   # 2:00 PM
                
                NurseAvailability.objects.create(
                    nurse=nurse,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    is_available=True
                )
                
                self.stdout.write(f'  {day}: {start_time} - {end_time}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully set up availability for {nurses.count()} nurses')
        )
