
class PermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_teacher_dashboard_accessible_to_authenticated_user(self):
        response = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_course_create_accessible_to_authenticated_user(self):
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 200)

    def test_teacher_reports_accessible_to_authenticated_user(self):
        response = self.client.get(reverse('teacher_reports'))
        self.assertEqual(response.status_code, 200)
