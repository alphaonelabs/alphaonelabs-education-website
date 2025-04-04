"""
Script to encrypt all PII data in the database.
Run this script directly after applying migrations to encrypt existing data.
"""

import os

import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

# Now import models and crypto functions
from web.crypto_utils import encrypt_value  # noqa: E402
from web.models import Donation, FeatureVote, PeerMessage, Profile, WebRequest  # noqa: E402


def encrypt_existing_data():
    """Encrypt all PII data in the database."""

    # Encrypt Profile model fields
    print("Encrypting Profile data...")
    profiles = Profile.objects.all()  # type: ignore[attr-defined]
    profile_count = profiles.count()

    for i, profile in enumerate(profiles, 1):
        if i % 10 == 0 or i == profile_count:
            print(f"  Processing profile {i} of {profile_count}")

        # Skip fields that are already encrypted
        if profile.bio and not profile.bio.startswith("gAAAAA"):
            profile.bio = encrypt_value(profile.bio)

        if profile.expertise and not profile.expertise.startswith("gAAAAA"):
            profile.expertise = encrypt_value(profile.expertise)

        if profile.discord_username and not profile.discord_username.startswith("gAAAAA"):
            profile.discord_username = encrypt_value(profile.discord_username)

        if profile.github_username and not profile.github_username.startswith("gAAAAA"):
            profile.github_username = encrypt_value(profile.github_username)

        if profile.slack_username and not profile.slack_username.startswith("gAAAAA"):
            profile.slack_username = encrypt_value(profile.slack_username)

        profile.save()

    # Encrypt WebRequest model fields
    print("\nEncrypting WebRequest data...")
    web_requests = WebRequest.objects.all()  # type: ignore[attr-defined]
    wr_count = web_requests.count()

    for i, web_request in enumerate(web_requests, 1):
        if i % 10 == 0 or i == wr_count:
            print(f"  Processing web request {i} of {wr_count}")

        if web_request.ip_address and not web_request.ip_address.startswith("gAAAAA"):
            web_request.ip_address = encrypt_value(web_request.ip_address)

        if web_request.user and not web_request.user.startswith("gAAAAA"):
            web_request.user = encrypt_value(web_request.user)

        web_request.save()

    # Encrypt PeerMessage model fields
    print("\nEncrypting PeerMessage data...")
    messages = PeerMessage.objects.all()  # type: ignore[attr-defined]
    msg_count = messages.count()

    for i, message in enumerate(messages, 1):
        if i % 10 == 0 or i == msg_count:
            print(f"  Processing message {i} of {msg_count}")

        if message.content and not message.content.startswith("gAAAAA"):
            message.content = encrypt_value(message.content)

        message.save()

    # Encrypt Donation model fields
    print("\nEncrypting Donation data...")
    donations = Donation.objects.all()  # type: ignore[attr-defined]
    don_count = donations.count()

    for i, donation in enumerate(donations, 1):
        if i % 10 == 0 or i == don_count:
            print(f"  Processing donation {i} of {don_count}")

        if donation.email and not donation.email.startswith("gAAAAA"):
            donation.email = encrypt_value(donation.email)

        donation.save()

    # Encrypt FeatureVote model fields
    print("\nEncrypting FeatureVote data...")
    votes = FeatureVote.objects.all()  # type: ignore[attr-defined]
    vote_count = votes.count()

    for i, vote in enumerate(votes, 1):
        if i % 10 == 0 or i == vote_count:
            print(f"  Processing vote {i} of {vote_count}")

        if vote.ip_address and not str(vote.ip_address).startswith("gAAAAA"):
            vote.ip_address = encrypt_value(str(vote.ip_address))

        vote.save()

    print("\nEncryption of existing data completed!")


if __name__ == "__main__":
    encrypt_existing_data()
