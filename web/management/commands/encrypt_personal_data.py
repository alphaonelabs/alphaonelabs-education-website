"""
Management command to encrypt existing personal data in the database.

This command handles the migration of plaintext personal data to encrypted format.
It's designed to be idempotent - can be run multiple times safely.
"""

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand

from web.models import Donation, FeatureVote, Order, Profile, WebRequest


class Command(BaseCommand):
    help = "Encrypts existing personal data in the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without making changes to the database",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))

        # Get encryption key
        key = settings.FIELD_ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode("utf-8")
        fernet = Fernet(key)

        # Track statistics
        stats = {
            "profile": 0,
            "webrequest": 0,
            "donation": 0,
            "order": 0,
            "featurevote": 0,
        }

        # Encrypt Profile data
        self.stdout.write("Processing Profile records...")
        profiles = Profile.objects.all()
        for profile in profiles:
            updated = False

            # Check and encrypt discord_username
            if profile.discord_username:
                try:
                    # Try to decrypt - if it succeeds, it's already encrypted
                    fernet.decrypt(profile.discord_username.encode("utf-8"))
                except Exception:
                    # Not encrypted, need to encrypt
                    if not dry_run:
                        # The field will auto-encrypt when we save
                        updated = True

            # Similar for other fields
            if profile.slack_username:
                try:
                    fernet.decrypt(profile.slack_username.encode("utf-8"))
                except Exception:
                    updated = True

            if profile.github_username:
                try:
                    fernet.decrypt(profile.github_username.encode("utf-8"))
                except Exception:
                    updated = True

            if profile.stripe_account_id:
                try:
                    fernet.decrypt(profile.stripe_account_id.encode("utf-8"))
                except Exception:
                    updated = True

            if updated and not dry_run:
                profile.save()
                stats["profile"] += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {stats['profile']} Profile records"))

        # Encrypt WebRequest data
        self.stdout.write("Processing WebRequest records...")
        webrequests = WebRequest.objects.all()
        for webrequest in webrequests:
            if webrequest.ip_address:
                try:
                    fernet.decrypt(webrequest.ip_address.encode("utf-8"))
                except Exception:
                    if not dry_run:
                        webrequest.save()
                        stats["webrequest"] += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {stats['webrequest']} WebRequest records"))

        # Encrypt Donation data
        self.stdout.write("Processing Donation records...")
        donations = Donation.objects.all()
        for donation in donations:
            if donation.email:
                try:
                    fernet.decrypt(donation.email.encode("utf-8"))
                except Exception:
                    if not dry_run:
                        donation.save()
                        stats["donation"] += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {stats['donation']} Donation records"))

        # Encrypt Order data
        self.stdout.write("Processing Order records...")
        orders = Order.objects.all()
        for order in orders:
            if order.shipping_address:
                try:
                    # Check if already encrypted by trying to decrypt
                    if isinstance(order.shipping_address, str):
                        fernet.decrypt(order.shipping_address.encode("utf-8"))
                except Exception:
                    if not dry_run:
                        order.save()
                        stats["order"] += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {stats['order']} Order records"))

        # Encrypt FeatureVote data
        self.stdout.write("Processing FeatureVote records...")
        featurevotes = FeatureVote.objects.all()
        for featurevote in featurevotes:
            if featurevote.ip_address:
                try:
                    fernet.decrypt(featurevote.ip_address.encode("utf-8"))
                except Exception:
                    if not dry_run:
                        featurevote.save()
                        stats["featurevote"] += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {stats['featurevote']} FeatureVote records"))

        # Summary
        self.stdout.write(self.style.SUCCESS("\n=== Encryption Summary ==="))
        for model, count in stats.items():
            self.stdout.write(f"{model}: {count} records encrypted")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN completed - no changes were saved"))
        else:
            self.stdout.write(self.style.SUCCESS("\nAll personal data has been encrypted successfully!"))
