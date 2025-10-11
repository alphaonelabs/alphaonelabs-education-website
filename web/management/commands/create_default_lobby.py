"""Management command to create a default virtual lobby."""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from web.models import VirtualLobby


class Command(BaseCommand):
    help = 'Create a default virtual lobby for testing'

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )

        # Create default lobby if it doesn't exist
        lobby, created = VirtualLobby.objects.get_or_create(
            name='Main Lobby',
            defaults={
                'description': 'Welcome to the main virtual lobby! Join us to connect, collaborate, and learn together.',
                'max_users': 100,
                'is_public': True,
                'created_by': admin_user
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created default lobby: {lobby.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Default lobby already exists: {lobby.name}')
            )

        self.stdout.write(
            self.style.SUCCESS('Default lobby setup complete!')
        )
