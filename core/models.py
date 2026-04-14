from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Пән атауы')
    icon = models.CharField(max_length=10, default='📚')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пән'
        verbose_name_plural = 'Пәндер'

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_STUDENT = 'student'
    ROLE_TEACHER = 'teacher'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Оқушы'),
        (ROLE_TEACHER, 'Мұғалім'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    patronymic = models.CharField(max_length=150, blank=True, verbose_name='Әкесінің аты')

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join(p for p in parts if p)

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def __str__(self):
        return self.full_name or self.username


class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name='Тест атауы')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quizzes')
    passing_score = models.IntegerField(default=60, verbose_name='Өту балы (%)')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    copied_from = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='copies',
        verbose_name='Көшірілген тесттен'
    )

    # Block 1: Theory
    theory_content = models.TextField(blank=True, verbose_name='Теория мазмұны')
    theory_time_minutes = models.IntegerField(default=10, verbose_name='Теорияға уақыт (мин)')
    theory_image = models.ImageField(upload_to='theory_images/', null=True, blank=True, verbose_name='Теория суреті')
    theory_image = CloudinaryField('theory_image')

    # Block 2: Text answers
    block2_time_minutes = models.IntegerField(default=15, verbose_name='2-блокқа уақыт (мин)')

    # Block 3: Test
    block3_time_minutes = models.IntegerField(default=20, verbose_name='3-блокқа уақыт (мин)')

    class Meta:
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесттер'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_share_url(self):
        from django.urls import reverse
        return f"/quiz/{self.id}/start/"

    @property
    def max_score(self):
        test_questions = self.test_questions.count()
        return test_questions * 10 if test_questions else 100


class OpenQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='open_questions')
    question_text = models.TextField(verbose_name='Сұрақ')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.quiz.title} - сұрақ {self.order}"


class TestQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='test_questions')
    question_text = models.TextField(verbose_name='Сұрақ')
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=10)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.quiz.title} - тест сұрағы {self.order}"


class TestAnswer(models.Model):
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.answer_text


class QuizAttempt(models.Model):
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'Орындалуда'),
        (STATUS_COMPLETED, 'Аяқталды'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    current_block = models.IntegerField(default=1)  # 1=theory, 2=open, 3=test
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    block2_score = models.IntegerField(null=True, blank=True)  # teacher grades this
    block3_score = models.IntegerField(default=0)
    block2_graded = models.BooleanField(default=False)

    class Meta:
        unique_together = ['student', 'quiz']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student} - {self.quiz}"

    @property
    def total_score(self):
        # b2 = self.block2_score or 0
        b3 = self.block3_score or 0
        # return b2 + b3 open queestion score added
        return b3

    @property
    def passed(self):
        max_s = self.quiz.max_score
        if max_s == 0:
            return True
        return (self.total_score / max_s * 100) >= self.quiz.passing_score


class OpenAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='open_answers')
    question = models.ForeignKey(OpenQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    score = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['attempt', 'question']


class TestAnswerSubmission(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='test_submissions')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(TestAnswer, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ['attempt', 'question']
