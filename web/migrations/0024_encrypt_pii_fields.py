from django.db import migrations
from web.fields import EncryptedTextField, EncryptedCharField

class Migration(migrations.Migration):
    dependencies = [
        ('web', '0023_donation'),
    ]

    operations = [
        # Profile Model
        migrations.AlterField(
            model_name='profile',
            name='bio',
            field=EncryptedTextField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name='profile',
            name='expertise',
            field=EncryptedCharField(blank=True, max_length=200),
        ),
        
        # WebRequest Model
        migrations.AlterField(
            model_name='webrequest',
            name='ip_address',
            field=EncryptedCharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='webrequest',
            name='user',
            field=EncryptedCharField(blank=True, default='', max_length=150),
        ),
        migrations.AlterField(
            model_name='webrequest',
            name='agent',
            field=EncryptedTextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='webrequest',
            name='referer',
            field=EncryptedCharField(blank=True, default='', max_length=255),
        ),
        
        # Order Model
        migrations.AlterField(
            model_name='order',
            name='tracking_number',
            field=EncryptedCharField(blank=True, max_length=100),
        ),
        
        # Donation Model
        migrations.AlterField(
            model_name='donation',
            name='email',
            field=EncryptedCharField(max_length=254),
        ),
        migrations.AlterField(
            model_name='donation',
            name='message',
            field=EncryptedTextField(blank=True),
        ),
        
        # Payment Model
        migrations.AlterField(
            model_name='payment',
            name='stripe_payment_intent_id',
            field=EncryptedCharField(max_length=100, unique=True),
        ),
        
        # Enrollment Model
        migrations.AlterField(
            model_name='enrollment',
            name='payment_intent_id',
            field=EncryptedCharField(blank=True, default='', max_length=100),
        ),
        
        # SessionEnrollment Model
        migrations.AlterField(
            model_name='sessionenrollment',
            name='payment_intent_id',
            field=EncryptedCharField(blank=True, default='', max_length=100),
        ),
    ] 