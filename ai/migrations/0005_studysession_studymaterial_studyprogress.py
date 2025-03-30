# Generated by Django 5.1.6 on 2025-03-29 10:07

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0004_alter_message_options_alter_progressrecord_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudySession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('duration_minutes', models.IntegerField(default=30)),
                ('scheduled_date', models.DateTimeField()),
                ('completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('study_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='ai.studyplan')),
            ],
            options={
                'ordering': ['scheduled_date'],
            },
        ),
        migrations.CreateModel(
            name='StudyMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('material_type', models.CharField(choices=[('text', 'Text'), ('video', 'Video'), ('quiz', 'Quiz'), ('exercise', 'Exercise')], max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('study_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='ai.studysession')),
            ],
        ),
        migrations.CreateModel(
            name='StudyProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed', models.BooleanField(default=False)),
                ('completion_date', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='study_progress', to=settings.AUTH_USER_MODEL)),
                ('study_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='ai.studysession')),
            ],
            options={
                'unique_together': {('user', 'study_session')},
            },
        ),
    ]
