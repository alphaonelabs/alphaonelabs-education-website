from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.text import slugify

from web.models import Course, GroupEnrollment, GroupMember, Subject, Discount


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class BaseGroupEnrollmentTest(TestCase):
    """Base test class for group enrollment tests with common setup"""
    
    def setUp(self):
        # Create a subject for the course
        self.subject = Subject.objects.create(
            name="Mathematics",
            slug="mathematics",
            description="Mathematics courses",
            icon="fas fa-calculator"
        )
        
        # Create a teacher with profile
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="testpass123"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a course with standard fields
        self.course = Course.objects.create(
            title="Test Course",
            slug=slugify("Test Course"),
            teacher=self.teacher,
            description="A test course",
            learning_objectives="Learn testing",
            prerequisites="None",
            price=100.00,
            allow_individual_sessions=False,
            invite_only=False,
            max_students=30,
            subject=self.subject,
            level="beginner",
            tags="test,course"
        )

        # Create test students with consistent naming
        self.students = []
        for i in range(1, 4):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="testpass123"
            )
            self.students.append(student)


class GroupEnrollmentTest(BaseGroupEnrollmentTest):
    """Test class for group enrollment functionality"""
    
    def setUp(self):
        super().setUp()
        # Add any additional setup specific to group enrollment tests

    def test_create_group_enrollment(self):
        self.client.login(username="student1", password="pass")
        url = reverse("create_group_enrollment", args=[self.course.id])
        data = {
            "name": "Test Group",
            "min_members": 3
        }
        response = self.client.post(url, data)
        
        new_group = GroupEnrollment.objects.get(name="Test Group")
        self.assertRedirects(response, reverse("group_detail", args=[new_group.id]))
        self.assertTrue(GroupEnrollment.objects.filter(name="Test Group").exists())
        self.assertTrue(GroupMember.objects.filter(group__name="Test Group", user=self.students[0]).exists())
        self.assertTrue(Discount.objects.filter(code__startswith="GROUP").exists())

    def test_join_group(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.students[0],
            course=self.course,
            min_members=3
        )
        GroupMember.objects.create(group=group, user=self.students[0])
        
        # Test joining the group
        self.client.login(username="student2", password="pass")
        url = reverse("join_group", args=[group.invitation_token])
        response = self.client.post(url)
        
        self.assertRedirects(response, reverse("group_detail", args=[group.id]))
        self.assertTrue(GroupMember.objects.filter(group=group, user=self.students[1]).exists())

    def test_group_discount(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.students[0],
            course=self.course,
            min_members=3
        )
        
        # Add members
        GroupMember.objects.create(group=group, user=self.students[0])
        GroupMember.objects.create(group=group, user=self.students[1])
        GroupMember.objects.create(group=group, user=self.students[2])
        
        # Check discount
        self.assertTrue(group.is_eligible_for_discount())
        self.assertEqual(group.discount.percentage, 10.00)  # 10% discount
        self.assertEqual(group.discount.apply_discount, 90.00)  # $100 - 10%

    def test_duplicate_group_membership(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.students[0],
            course=self.course,
            min_members=3
        )
        GroupMember.objects.create(group=group, user=self.students[0])
        
        # Try to join the same group again
        self.client.login(username="student1", password="pass")
        url = reverse("join_group", args=[group.invitation_token])
        response = self.client.post(url)
        
        self.assertRedirects(response, reverse("group_detail", args=[group.id]))
        self.assertEqual(GroupMember.objects.filter(group=group, user=self.students[0]).count(), 1) 
