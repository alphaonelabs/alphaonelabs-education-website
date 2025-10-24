# Generated migration for Virtual Classroom models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0062_update_waitingroom_for_sessions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VirtualClassroom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(help_text="Classroom session title", max_length=200)),
                ("rows", models.PositiveIntegerField(default=5, help_text="Number of rows in the classroom")),
                ("columns", models.PositiveIntegerField(default=6, help_text="Number of columns in the classroom")),
                ("is_active", models.BooleanField(default=True, help_text="Whether the classroom is currently active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="virtual_classrooms",
                        to="web.session",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="taught_virtual_classrooms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Virtual Classroom",
                "verbose_name_plural": "Virtual Classrooms",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ClassroomSeat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row", models.PositiveIntegerField()),
                ("column", models.PositiveIntegerField()),
                ("is_occupied", models.BooleanField(default=False)),
                (
                    "is_speaking",
                    models.BooleanField(default=False, help_text="Whether this student is currently speaking"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="seats", to="web.virtualclassroom"
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="classroom_seats",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Classroom Seat",
                "verbose_name_plural": "Classroom Seats",
                "ordering": ["classroom", "row", "column"],
                "unique_together": {("classroom", "row", "column")},
            },
        ),
        migrations.CreateModel(
            name="RaisedHand",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True, help_text="Whether the hand is still raised")),
                (
                    "selected_at",
                    models.DateTimeField(
                        blank=True, help_text="When teacher selected this student to speak", null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="raised_hands", to="web.virtualclassroom"
                    ),
                ),
                (
                    "seat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="raised_hands", to="web.classroomseat"
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="raised_hands",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Raised Hand",
                "verbose_name_plural": "Raised Hands",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="UpdateRound",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Daily Update Round", max_length=200)),
                (
                    "duration_seconds",
                    models.PositiveIntegerField(default=120, help_text="Duration for each student update in seconds"),
                ),
                ("is_active", models.BooleanField(default=False, help_text="Whether the round is currently running")),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="update_rounds", to="web.virtualclassroom"
                    ),
                ),
                (
                    "current_speaker",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="current_update_rounds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Update Round",
                "verbose_name_plural": "Update Rounds",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UpdateRoundParticipant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("has_spoken", models.BooleanField(default=False)),
                ("spoken_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.PositiveIntegerField(default=0, help_text="Speaking order")),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="update_round_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "update_round",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="web.updateround"
                    ),
                ),
            ],
            options={
                "verbose_name": "Update Round Participant",
                "verbose_name_plural": "Update Round Participants",
                "ordering": ["order"],
                "unique_together": {("update_round", "student")},
            },
        ),
        migrations.CreateModel(
            name="ScreenShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=200)),
                (
                    "screenshot",
                    models.ImageField(help_text="Uploaded screenshot", upload_to="classroom_screenshots/%Y/%m/%d/"),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "is_visible_to_teacher",
                    models.BooleanField(default=True, help_text="Whether the teacher can see this screen share"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "classroom",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="screen_shares", to="web.virtualclassroom"
                    ),
                ),
                (
                    "seat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="screen_shares", to="web.classroomseat"
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="screen_shares",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Screen Share",
                "verbose_name_plural": "Screen Shares",
                "ordering": ["-created_at"],
            },
        ),
    ]
