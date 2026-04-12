from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_choose, name='register_choose'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/teacher/', views.register_teacher, name='register_teacher'),

    # Student
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('subject/<int:subject_id>/', views.subject_quizzes, name='subject_quizzes'),
    path('quiz/<int:quiz_id>/start/', views.quiz_start, name='quiz_start'),
    path('quiz/<int:quiz_id>/block/<int:block>/', views.quiz_block, name='quiz_block'),
    path('quiz/<int:quiz_id>/block1/done/', views.quiz_block1_done, name='quiz_block1_done'),
    path('quiz/results/<int:attempt_id>/', views.quiz_results, name='quiz_results'),

    # Teacher
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/subject/<int:subject_id>/manage/', views.teacher_subject_quizzes, name='teacher_subject_quizzes'),
    path('teacher/quiz/<int:quiz_id>/', views.teacher_quiz_detail, name='teacher_quiz_detail'),
    path('teacher/quiz/<int:quiz_id>/rename/', views.quiz_rename, name='quiz_rename'),
    path('teacher/grade/<int:attempt_id>/', views.teacher_grade_attempt, name='teacher_grade_attempt'),

    # Quiz creation
    path('teacher/subject/<int:subject_id>/create/', views.quiz_create_step1, name='quiz_create_step1'),
    path('teacher/quiz/<int:quiz_id>/create/step2/', views.quiz_create_step2, name='quiz_create_step2'),
    path('teacher/quiz/<int:quiz_id>/create/step3/', views.quiz_create_step3, name='quiz_create_step3'),
    path('teacher/quiz/<int:quiz_id>/create/step4/', views.quiz_create_step4, name='quiz_create_step4'),
    path('teacher/quiz/<int:quiz_id>/create/step5/', views.quiz_create_step5, name='quiz_create_step5'),

    # API
    path('api/add-subject/', views.add_subject, name='add_subject'),

    path('marketplace/', views.marketplace, name='marketplace'),
    path('marketplace/copy/<int:quiz_id>/', views.marketplace_copy, name='marketplace_copy'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
