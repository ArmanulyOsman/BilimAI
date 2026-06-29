from django.test import TestCase
from django.urls import reverse

from .models import User, Subject, Quiz, QuizAttempt


class HomeViewTests(TestCase):

    def test_redirect_anonymous_to_login(self):
        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('login'))

    def test_redirect_teacher_to_dashboard(self):
        teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.client.login(username='teacher', password='123456')

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('teacher_dashboard'))

    def test_redirect_student_to_dashboard(self):
        student = User.objects.create_user(
            username='student',
            password='123456',
            role=User.ROLE_STUDENT
        )

        self.client.login(username='student', password='123456')

        response = self.client.get(reverse('home'))

        self.assertRedirects(response, reverse('student_dashboard'))

class StudentDashboardTests(TestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username='student',
            password='123456',
            role=User.ROLE_STUDENT
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.subject = Subject.objects.create(
            name='Math',
            icon='📚'
        )

        Quiz.objects.create(
            title='Quiz 1',
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

    def test_student_can_open_dashboard(self):
        self.client.login(username='student', password='123456')

        response = self.client.get(
            reverse('student_dashboard')
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Math')

    def test_teacher_redirected_to_teacher_dashboard(self):
        self.client.login(username='teacher', password='123456')

        response = self.client.get(
            reverse('student_dashboard')
        )

        self.assertRedirects(
            response,
            reverse('teacher_dashboard')
        )

class QuizStartTests(TestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username='student',
            password='123456',
            role=User.ROLE_STUDENT
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.subject = Subject.objects.create(
            name='Math',
            icon='📚'
        )

        self.quiz = Quiz.objects.create(
            title='Quiz',
            subject=self.subject,
            teacher=self.teacher,
            is_active=True
        )

    def test_create_attempt_on_first_start(self):
        self.client.login(
            username='student',
            password='123456'
        )

        response = self.client.get(
            reverse('quiz_start', args=[self.quiz.id])
        )

        attempt = QuizAttempt.objects.get(
            student=self.student,
            quiz=self.quiz
        )

        self.assertEqual(attempt.current_block, 1)

        self.assertRedirects(
            response,
            reverse(
                'quiz_block',
                kwargs={
                    'quiz_id': self.quiz.id,
                    'block': 1
                }
            )
        )

    def test_completed_attempt_redirects_to_results(self):
        attempt = QuizAttempt.objects.create(
            student=self.student,
            quiz=self.quiz,
            status=QuizAttempt.STATUS_COMPLETED
        )

        self.client.login(
            username='student',
            password='123456'
        )

        response = self.client.get(
            reverse('quiz_start', args=[self.quiz.id])
        )

        self.assertRedirects(
            response,
            reverse(
                'quiz_results',
                kwargs={'attempt_id': attempt.id}
            )
        )

class TeacherDashboardTests(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.student = User.objects.create_user(
            username='student',
            password='123456',
            role=User.ROLE_STUDENT
        )

    def test_teacher_can_open_dashboard(self):
        self.client.login(
            username='teacher',
            password='123456'
        )

        response = self.client.get(
            reverse('teacher_dashboard')
        )

        self.assertEqual(response.status_code, 200)

    def test_student_redirected(self):
        self.client.login(
            username='student',
            password='123456'
        )

        response = self.client.get(
            reverse('teacher_dashboard')
        )

        self.assertRedirects(
            response,
            reverse('student_dashboard')
        )

class TeacherAddSubjectTests(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.subject = Subject.objects.create(
            name='Physics',
            icon='⚛️'
        )

    def test_add_existing_subject(self):
        self.client.login(
            username='teacher',
            password='123456'
        )

        self.client.post(
            reverse('teacher_add_subject'),
            {
                'subject_id': self.subject.id
            }
        )

        self.assertTrue(
            self.teacher.subjects.filter(
                id=self.subject.id
            ).exists()
        )

    def test_create_new_subject(self):
        self.client.login(
            username='teacher',
            password='123456'
        )

        self.client.post(
            reverse('teacher_add_subject'),
            {
                'new_name': 'Biology',
                'icon': '🧬'
            }
        )

        self.assertTrue(
            Subject.objects.filter(
                name='Biology'
            ).exists()
        )

class MarketplaceCopyTests(TestCase):

    def setUp(self):
        self.author = User.objects.create_user(
            username='author',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            password='123456',
            role=User.ROLE_TEACHER
        )

        self.subject = Subject.objects.create(
            name='Math',
            icon='📚'
        )

        self.quiz = Quiz.objects.create(
            title='Original Quiz',
            subject=self.subject,
            teacher=self.author,
            is_active=True
        )

    def test_copy_quiz(self):
        self.client.login(
            username='teacher',
            password='123456'
        )

        self.client.get(
            reverse(
                'marketplace_copy',
                args=[self.quiz.id]
            )
        )

        copied = Quiz.objects.filter(
            teacher=self.teacher,
            copied_from=self.quiz
        ).first()

        self.assertIsNotNone(copied)
        self.assertEqual(
            copied.title,
            'Original Quiz (көшірме)'
        )

