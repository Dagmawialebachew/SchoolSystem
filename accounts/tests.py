from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from schools.models import School

User = get_user_model()


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test School",
            address="123 Test St",
            phone="123-456-7890",
            email="test@school.com"
        )
        
        # Create users with different roles
        self.super_admin = User.objects.create_user(
            username='superadmin',
            password='testpass123',
            role='SUPER_ADMIN'
        )
        
        self.school_admin = User.objects.create_user(
            username='schooladmin',
            password='testpass123',
            role='SCHOOL_ADMIN',
            school=self.school
        )
        
        self.teacher = User.objects.create_user(
            username='teacher',
            password='testpass123',
            role='TEACHER',
            school=self.school
        )
        
        self.parent = User.objects.create_user(
            username='parent',
            password='testpass123',
            role='PARENT',
            school=self.school
        )
    
    def test_login_redirects_super_admin(self):
        """Test that super admin is redirected to admin dashboard"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'superadmin',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/admin/')
    
    def test_login_redirects_school_admin(self):
        """Test that school admin is redirected to dashboard"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'schooladmin',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/dashboard/')
    
    def test_login_redirects_teacher(self):
        """Test that teacher is redirected to teacher dashboard"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'teacher',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/teacher-dashboard/')
    
    def test_login_redirects_parent(self):
        """Test that parent is redirected to parent dashboard"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'parent',
            'password': 'testpass123'
        })
        self.assertRedirects(response, '/parent-dashboard/')
    
    def test_unauthorized_access_school_admin_only(self):
        """Test that non-school-admin users cannot access school admin pages"""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('students:add'))
        self.assertEqual(response.status_code, 403)
    
    def test_authorized_access_school_admin(self):
        """Test that school admin can access admin pages"""
        self.client.login(username='schooladmin', password='testpass123')
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_teacher_can_view_students(self):
        """Test that teachers can view student lists"""
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 200)
    
    def test_parent_can_view_students(self):
        """Test that parents can view student lists (filtered to their children)"""
        self.client.login(username='parent', password='testpass123')
        response = self.client.get(reverse('students:list'))
        self.assertEqual(response.status_code, 200)