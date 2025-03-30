# Generated by Django 5.1.6 on 2025-03-29 10:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0006_achievement_groupdiscussion_discussionreply_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='discussionreply',
            name='discussion',
        ),
        migrations.RemoveField(
            model_name='discussionreply',
            name='user',
        ),
        migrations.RemoveField(
            model_name='groupdiscussion',
            name='group',
        ),
        migrations.RemoveField(
            model_name='groupdiscussion',
            name='user',
        ),
        migrations.AlterUniqueTogether(
            name='learninganalytics',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='learninganalytics',
            name='user',
        ),
        migrations.RemoveField(
            model_name='studygroup',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='studygroup',
            name='members',
        ),
        migrations.RemoveField(
            model_name='studymaterial',
            name='study_session',
        ),
        migrations.AlterUniqueTogether(
            name='studyprogress',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='studyprogress',
            name='study_session',
        ),
        migrations.RemoveField(
            model_name='studyprogress',
            name='user',
        ),
        migrations.RemoveField(
            model_name='studysession',
            name='study_plan',
        ),
        migrations.RemoveField(
            model_name='teacherprofile',
            name='user',
        ),
        migrations.RemoveField(
            model_name='teachersession',
            name='teacher',
        ),
        migrations.RemoveField(
            model_name='teachersession',
            name='students',
        ),
        migrations.DeleteModel(
            name='Achievement',
        ),
        migrations.DeleteModel(
            name='DiscussionReply',
        ),
        migrations.DeleteModel(
            name='GroupDiscussion',
        ),
        migrations.DeleteModel(
            name='LearningAnalytics',
        ),
        migrations.DeleteModel(
            name='StudyGroup',
        ),
        migrations.DeleteModel(
            name='StudyMaterial',
        ),
        migrations.DeleteModel(
            name='StudyProgress',
        ),
        migrations.DeleteModel(
            name='StudySession',
        ),
        migrations.DeleteModel(
            name='TeacherProfile',
        ),
        migrations.DeleteModel(
            name='TeacherSession',
        ),
    ]
