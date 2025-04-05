# Generated by Django 5.1.6 on 2025-04-04 19:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0053_goods_featured"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="achievement",
            name="badge_type",
            field=models.CharField(
                choices=[("traditional", "Traditional Badge"), ("nft", "NFT Badge")],
                default="traditional",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="achievement",
            name="teacher",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="awarded_by",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="wallet_address",
            field=models.CharField(
                blank=True, help_text="Student's Ethereum wallet address for receiving NFT badges", max_length=42
            ),
        ),
        migrations.CreateModel(
            name="NFTBadge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "blockchain",
                    models.CharField(
                        choices=[("ethereum", "Ethereum"), ("polygon", "Polygon"), ("solana", "Solana")],
                        default="polygon",
                        max_length=20,
                    ),
                ),
                ("token_id", models.CharField(blank=True, max_length=100)),
                ("contract_address", models.CharField(blank=True, max_length=100)),
                ("transaction_hash", models.CharField(blank=True, max_length=100)),
                ("metadata_uri", models.URLField(blank=True)),
                ("minted_at", models.DateTimeField(blank=True, null=True)),
                ("wallet_address", models.CharField(blank=True, max_length=42)),
                ("icon_url", models.URLField(blank=True)),
                (
                    "achievement",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="nft_badge", to="web.achievement"
                    ),
                ),
            ],
        ),
    ]
