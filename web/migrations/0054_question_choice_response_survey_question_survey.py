# Generated by Django 5.1.6 on 2025-04-06 18:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0053_goods_featured"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("mcq", "Multiple Choice"),
                            ("checkbox", "Checkbox (Multiple Answers)"),
                            ("text", "Text Answer"),
                            ("true_false", "True/False"),
                            ("scale", "Scale Rating"),
                        ],
                        default="mcq",
                        max_length=20,
                    ),
                ),
                ("required", models.BooleanField(default=True)),
                ("scale_min", models.IntegerField(default=1)),
                ("scale_max", models.IntegerField(default=5)),
            ],
        ),
        migrations.CreateModel(
            name="Choice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=200)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="web.question")),
            ],
        ),
        migrations.CreateModel(
            name="Response",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text_answer", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "choice",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="web.choice"
                    ),
                ),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="web.question")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Survey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="question",
            name="survey",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="web.survey"),
        ),
    ]
