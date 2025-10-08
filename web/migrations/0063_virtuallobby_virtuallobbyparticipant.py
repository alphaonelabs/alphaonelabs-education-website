# Generated migration for Virtual Lobby models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("web", "0062_update_waitingroom_for_sessions"),
    ]

    operations = [
        migrations.CreateModel(
            name="VirtualLobby",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Main Lobby", max_length=200)),
                ("description", models.TextField(blank=True, help_text="Description of the lobby")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "max_participants",
                    models.PositiveIntegerField(default=100, help_text="Maximum number of participants in the lobby"),
                ),
            ],
            options={
                "verbose_name": "Virtual Lobby",
                "verbose_name_plural": "Virtual Lobbies",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VirtualLobbyParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("last_active", models.DateTimeField(auto_now=True)),
                ("position_x", models.FloatField(default=400.0, help_text="X coordinate position in the lobby")),
                ("position_y", models.FloatField(default=300.0, help_text="Y coordinate position in the lobby")),
                (
                    "lobby",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="web.virtuallobby"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lobby_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Virtual Lobby Participant",
                "verbose_name_plural": "Virtual Lobby Participants",
                "ordering": ["-last_active"],
                "unique_together": {("lobby", "user")},
            },
        ),
    ]
