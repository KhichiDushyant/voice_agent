"""
Django management command to initialize the project.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Initialize the Carematix project with migrations and sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations',
        )
        parser.add_argument(
            '--skip-sample-data',
            action='store_true',
            help='Skip setting up sample data',
        )
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser account',
        )

    def handle(self, *args, **options):
        self.stdout.write('Initializing Carematix project...')
        
        # Run migrations
        if not options['skip_migrations']:
            self.stdout.write('Running database migrations...')
            call_command('migrate', verbosity=0)
            self.stdout.write(self.style.SUCCESS('Migrations completed'))
        
        # Set up sample data
        if not options['skip_sample_data']:
            self.stdout.write('Setting up sample data...')
            call_command('setup_sample_data', verbosity=0)
            self.stdout.write(self.style.SUCCESS('Sample data setup completed'))
        
        # Create superuser
        if options['create_superuser']:
            self.stdout.write('Creating superuser account...')
            if not User.objects.filter(is_superuser=True).exists():
                call_command('createsuperuser', interactive=False, username='admin', email='admin@carematix.com')
                self.stdout.write(self.style.SUCCESS('Superuser created: admin/admin'))
            else:
                self.stdout.write(self.style.WARNING('Superuser already exists'))
        
        self.stdout.write(self.style.SUCCESS('Project initialization completed!'))
        self.stdout.write('You can now run: python manage.py runserver')
