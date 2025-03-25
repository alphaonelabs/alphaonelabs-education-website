# Generated by Django 5.1.6 on 2025-03-25 12:00

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import ProgrammingError, connections, migrations, models
from django.db.migrations.operations.special import SeparateDatabaseAndState
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    MembershipPlan = apps.get_model("web", "MembershipPlan")
    for plan in MembershipPlan.objects.all():
        plan.slug = slugify(plan.name)
        plan.save()


def check_slug_column_exists(apps, schema_editor):
    """Check if slug column already exists in membershipplan table and log its status"""
    # Get the database connection
    connection = connections[schema_editor.connection.alias]
    cursor = connection.cursor()

    # Check if the column exists in the table
    try:
        # Different SQL syntax depending on the database backend
        if connection.vendor == 'mysql':
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'web_membershipplan' AND column_name = 'slug'"
            )
        elif connection.vendor == 'sqlite':
            cursor.execute('PRAGMA table_info(web_membershipplan)')
            columns = [column[1] for column in cursor.fetchall()]
            slug_exists = 'slug' in columns
            # Print result for SQLite before returning
            print(f"Slug column exists in web_membershipplan: {slug_exists}")
            return
        else:
            # PostgreSQL
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'web_membershipplan' AND column_name = 'slug'"
            )

        # For MySQL and PostgreSQL, get the result
        if connection.vendor != 'sqlite':
            slug_exists = cursor.fetchone()[0] > 0

        # If the column doesn't exist, we do nothing - the migration will add it
        # If it exists, we'll modify later migrations or ignore this one
        print(f"Slug column exists in web_membershipplan: {slug_exists}")

    except ProgrammingError:
        # If table doesn't exist yet, we do nothing
        pass


class Migration(migrations.Migration):
    """
    This migration consolidates all migrations from 0001 to 0047, including:
    - Badge and user badge models
    - Peer challenge functionality
    - Profile updates
    - Course material enhancements
    - Note history
    - Challenge submissions and reviews
    - Avatar customization
    - Study group improvements
    - Membership plan functionality
    - Fix for duplicate slug migration
    """

    dependencies = [
        ("web", "0001_initial"),  # Using the initial migration as our base
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Badge and UserBadge
        SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Badge",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=100)),
                        ("description", models.TextField()),
                        ("image", models.ImageField(upload_to="badges/")),
                        (
                            "badge_type",
                            models.CharField(
                                choices=[
                                    ("challenge", "Challenge Completion"),
                                    ("course", "Course Completion"),
                                    ("achievement", "Special Achievement"),
                                    ("teacher_awarded", "Teacher Awarded"),
                                ],
                                max_length=20,
                            ),
                        ),
                        ("is_active", models.BooleanField(default=True)),
                        ("criteria", models.JSONField(blank=True, default=dict)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "challenge",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="badges",
                                to="web.challenge",
                            ),
                        ),
                        (
                            "course",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="badges",
                                to="web.course",
                            ),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="created_badges",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["badge_type", "name"],
                    },
                ),
                migrations.CreateModel(
                    name="UserBadge",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        (
                            "award_method",
                            models.CharField(
                                choices=[
                                    ("challenge_completion", "Challenge Completion"),
                                    ("course_completion", "Course Completion"),
                                    ("teacher_awarded", "Teacher Awarded"),
                                    ("system_awarded", "System Awarded"),
                                ],
                                max_length=20,
                            ),
                        ),
                        ("awarded_at", models.DateTimeField(auto_now_add=True)),
                        ("award_message", models.TextField(blank=True)),
                        (
                            "awarded_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="awarded_badges",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "badge",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE, related_name="awarded_to", to="web.badge"
                            ),
                        ),
                        (
                            "challenge_submission",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="badges",
                                to="web.challengesubmission",
                            ),
                        ),
                        (
                            "course_enrollment",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="badges",
                                to="web.enrollment",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE, related_name="badges", to=settings.AUTH_USER_MODEL
                            ),
                        ),
                    ],
                ),
            ],
        ),
        
        # Add MembershipPlan slug check (from 0047)
        migrations.RunPython(
            check_slug_column_exists,
            reverse_code=migrations.RunPython.noop
        ),
        
        # Add slug generation function
        migrations.RunPython(
            generate_slugs,
            reverse_code=migrations.RunPython.noop
        ),
    ] 