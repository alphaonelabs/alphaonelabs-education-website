from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from web.models import Course, GroupEnrollment, GroupMember, Subject, Discount


class GroupEnrollmentTest(TestCase):
    def setUp(self):
        # Create a subject for the course
        self.subject = Subject.objects.create(
            name="Mathematics", slug="mathematics", description="Mathematics courses", icon="fas fa-calculator"
        )
        
        # Create a teacher
        self.teacher = User.objects.create_user(username="teacher1", password="pass", email="teacher1@example.com")
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a course
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
            tags="test,course",
        )

        # Create students
        self.student1 = User.objects.create_user(username="student1", password="pass", email="student1@example.com")
        self.student2 = User.objects.create_user(username="student2", password="pass", email="student2@example.com")
        self.student3 = User.objects.create_user(username="student3", password="pass", email="student3@example.com")

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
        self.assertTrue(GroupMember.objects.filter(group__name="Test Group", user=self.student1).exists())
        self.assertTrue(Discount.objects.filter(code__startswith="GROUP").exists())

    def test_join_group(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.student1,
            course=self.course,
            min_members=3
        )
        GroupMember.objects.create(group=group, user=self.student1)
        
        # Test joining the group
        self.client.login(username="student2", password="pass")
        url = reverse("join_group", args=[group.invitation_token])
        response = self.client.post(url)
        
        self.assertRedirects(response, reverse("group_detail", args=[group.id]))
        self.assertTrue(GroupMember.objects.filter(group=group, user=self.student2).exists())

    def test_group_discount(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.student1,
            course=self.course,
            min_members=3
        )
        
        # Add members
        GroupMember.objects.create(group=group, user=self.student1)
        GroupMember.objects.create(group=group, user=self.student2)
        GroupMember.objects.create(group=group, user=self.student3)
        
        # Check discount
        self.assertTrue(group.is_eligible_for_discount())
        self.assertEqual(group.discount.percentage, 10.00)  # 10% discount
        self.assertEqual(group.discount.apply_discount, 90.00)  # $100 - 10%

    def test_duplicate_group_membership(self):
        # Create a group
        group = GroupEnrollment.objects.create(
            name="Test Group",
            creator=self.student1,
            course=self.course,
            min_members=3
        )
        GroupMember.objects.create(group=group, user=self.student1)
        
        # Try to join the same group again
        self.client.login(username="student1", password="pass")
        url = reverse("join_group", args=[group.invitation_token])
        response = self.client.post(url)
        
        self.assertRedirects(response, reverse("group_detail", args=[group.id]))
        self.assertEqual(GroupMember.objects.filter(group=group, user=self.student1).count(), 1) 
