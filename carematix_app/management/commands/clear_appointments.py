from django.core.management.base import BaseCommand
from carematix_app.models import Appointment

class Command(BaseCommand):
    help = 'Clear all appointments from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all appointments',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING('This will delete ALL appointments from the database!')
            )
            self.stdout.write('Use --confirm flag to proceed')
            return

        # Count appointments before deletion
        appointment_count = Appointment.objects.count()
        
        if appointment_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No appointments found in the database')
            )
            return

        # Delete all appointments
        Appointment.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {appointment_count} appointments')
        )
