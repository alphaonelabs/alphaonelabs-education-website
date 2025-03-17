import os
from django.core.management.base import BaseCommand
from django.db import transaction
from cryptography.fernet import Fernet
from web.models import Profile, WebRequest, Order  # Add other models with encrypted fields
from web.crypto import encrypt, decrypt

class Command(BaseCommand):
    help = 'Rotate the encryption key for all encrypted data'

    def handle(self, *args, **options):
        # Generate a new key
        new_key = Fernet.generate_key()
        old_key = os.environ.get('ENCRYPTION_KEY')
        
        if not old_key:
            self.stdout.write(self.style.ERROR('No old encryption key found. Cannot rotate.'))
            return
            
        self.stdout.write(self.style.WARNING('Starting key rotation...'))
        self.stdout.write(self.style.WARNING('This may take a while for large datasets.'))
        
        # We'll need to manually decrypt with old key and re-encrypt with new key
        with transaction.atomic():
            # Update each model with encrypted fields
            # Example for Profile
            for profile in Profile.objects.all():
                if profile.bio:
                    try:
                        # Decrypt with old key
                        decrypted_bio = decrypt(profile.bio)
                        if decrypted_bio:
                            # Encrypt with new key
                            profile.bio = encrypt(decrypted_bio)
                            profile.save()
                            self.stdout.write(f'Rotated bio for Profile {profile.id}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error rotating bio for Profile {profile.id}: {e}'))
                
                if profile.expertise:
                    try:
                        decrypted_expertise = decrypt(profile.expertise)
                        if decrypted_expertise:
                            profile.expertise = encrypt(decrypted_expertise)
                            profile.save()
                            self.stdout.write(f'Rotated expertise for Profile {profile.id}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error rotating expertise for Profile {profile.id}: {e}'))
            
            # Update WebRequest model
            for request in WebRequest.objects.all():
                fields_to_rotate = ['ip_address', 'user', 'agent', 'referer']
                for field in fields_to_rotate:
                    value = getattr(request, field)
                    if value:
                        try:
                            decrypted_value = decrypt(value)
                            if decrypted_value:
                                setattr(request, field, encrypt(decrypted_value))
                                self.stdout.write(f'Rotated {field} for WebRequest {request.id}')
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Error rotating {field} for WebRequest {request.id}: {e}'))
                request.save()
            
            # Update Order model
            for order in Order.objects.all():
                if order.tracking_number:
                    try:
                        decrypted_tracking = decrypt(order.tracking_number)
                        if decrypted_tracking:
                            order.tracking_number = encrypt(decrypted_tracking)
                            order.save()
                            self.stdout.write(f'Rotated tracking number for Order {order.id}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error rotating tracking number for Order {order.id}: {e}'))
            
        self.stdout.write(self.style.SUCCESS(f'Key rotation complete! New key: {new_key.decode()}'))
        self.stdout.write(self.style.WARNING('Make sure to update your ENCRYPTION_KEY environment variable with this new key.')) 