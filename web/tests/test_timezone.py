"""
Tests for timezone functionality.
"""
from django.test import TestCase, Client
from django.urls import reverse
import json


class TimezoneViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_set_timezone_valid(self):
        """Test setting a valid timezone"""
        response = self.client.post(
            reverse('set_timezone'),
            {'timezone': 'America/New_York'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['timezone'], 'America/New_York')
        
        # Check that timezone is stored in session
        self.assertEqual(self.client.session.get('user_timezone'), 'America/New_York')

    def test_set_timezone_invalid(self):
        """Test setting an invalid timezone"""
        response = self.client.post(
            reverse('set_timezone'),
            {'timezone': 'Invalid/Timezone'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid timezone', data['message'])

    def test_set_timezone_no_timezone(self):
        """Test setting timezone without providing timezone parameter"""
        response = self.client.post(
            reverse('set_timezone'),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('No timezone provided', data['message'])

    def test_set_timezone_common_timezones(self):
        """Test setting various common timezones"""
        common_timezones = [
            'America/New_York',
            'America/Los_Angeles',
            'Europe/London',
            'Europe/Paris',
            'Asia/Tokyo',
            'Australia/Sydney',
            'UTC'
        ]
        
        for tz in common_timezones:
            response = self.client.post(
                reverse('set_timezone'),
                {'timezone': tz},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['timezone'], tz)
            self.assertEqual(self.client.session.get('user_timezone'), tz)
