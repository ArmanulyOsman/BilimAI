from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from .models import (
    User, Subject, Quiz, OpenQuestion, TestQuestion, TestAnswer,
    QuizAttempt, OpenAnswer, TestAnswerSubmission
)
from .forms import (
    StudentRegisterForm, TeacherRegisterForm, LoginForm,
    QuizBasicForm, QuizTheoryForm, QuizBlock2Form, QuizBlock3Form,
    OpenQuestionForm, TestQuestionForm, GradeBlock2Form
)


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_teacher:
        return redirect('teacher_dashboard')
    return redirect('student_dashboard')


def register_choose(request):
    return render(request, 'core/register_choose.html')


def register_student(request):
    if request.method == 'POST':
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('student_dashboard')
    else:
        form = StudentRegisterForm()
    return render(request, 'core/register_student.html', {'form': form})


def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegisterForm(request.POST)
        if form.is_valid():
            # 1. Пайдаланушыны базаға сақтаймыз
            user = form.save(commit=False)
            user.role = user.ROLE_TEACHER  # Ролін мұғалім деп орнатамыз
            user.save()
            
            # 2. Формадан таңдалған дайын пәндерді қосамыз (ID арқылы)
            selected_subject_ids = request.POST.getlist('subjects')
            if selected_subject_ids:
                user.subjects.add(*selected_subject_ids)
            
            # 3. JavaScript арқылы қосылған ЖАҢА пәндерді өңдейміз
            new_subjects_raw = request.POST.getlist('new_subjects[]')
            for sub_data in new_subjects_raw:
                # sub_data форматы: "📚 Математика"
                # Иконка мен атын бөліп аламыз
                try:
                    icon, name = sub_data.split(' ', 1)
                    # Базада мұндай пән болса аламыз, болмаса жаңадан жасаймыз
                    new_sub, created = Subject.objects.get_or_create(
                        name=name.strip(),
                        defaults={'icon': icon.strip()}
                    )
                    user.subjects.add(new_sub)
                except ValueError:
                    # Егер иконка таңдалмай тек аты келсе
                    new_sub, created = Subject.objects.get_or_create(name=sub_data.strip())
                    user.subjects.add(new_sub)

            login(request, user)
            return redirect('teacher_dashboard')
    else:
        form = TeacherRegisterForm()
    
    return render(request, 'core/register_teacher.html', {
        'form': form,
        'subjects': Subject.objects.all(),
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── STUDENT VIEWS ───────────────────────────────────────────────────────────

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return redirect('teacher_dashboard')
    subjects = Subject.objects.filter(quizzes__is_active=True).distinct()
    return render(request, 'core/student_dashboard.html', {'subjects': subjects})


@login_required
def subject_quizzes(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    quizzes = Quiz.objects.filter(subject=subject, is_active=True).select_related('teacher')
    # Annotate with attempt status
    attempts = {a.quiz_id: a for a in QuizAttempt.objects.filter(student=request.user)}
    quiz_list = []
    for q in quizzes:
        attempt = attempts.get(q.id)
        quiz_list.append({'quiz': q, 'attempt': attempt})
    return render(request, 'core/subject_quizzes.html', {
        'subject': subject,
        'quiz_list': quiz_list,
    })


@login_required
def quiz_start(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    attempt, created = QuizAttempt.objects.get_or_create(
        student=request.user, quiz=quiz,
        defaults={'current_block': 1}
    )
    if attempt.status == QuizAttempt.STATUS_COMPLETED:
        return redirect('quiz_results', attempt_id=attempt.id)
    return redirect('quiz_block', quiz_id=quiz_id, block=attempt.current_block)


@login_required
def quiz_block(request, quiz_id, block):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    attempt = get_object_or_404(QuizAttempt, student=request.user, quiz=quiz)

    if attempt.status == QuizAttempt.STATUS_COMPLETED:
        return redirect('quiz_results', attempt_id=attempt.id)

    if block == 1:
        return render(request, 'core/quiz_block1.html', {
            'quiz': quiz, 'attempt': attempt,
            'time_seconds': quiz.theory_time_minutes * 60,
        })

    elif block == 2:
        open_questions = quiz.open_questions.all()
        existing = {a.question_id: a for a in attempt.open_answers.all()}
        if request.method == 'POST':
            for q in open_questions:
                text = request.POST.get(f'q_{q.id}', '').strip()
                OpenAnswer.objects.update_or_create(
                    attempt=attempt, question=q,
                    defaults={'answer_text': text}
                )
            attempt.current_block = 3
            attempt.save()
            return redirect('quiz_block', quiz_id=quiz_id, block=3)
        return render(request, 'core/quiz_block2.html', {
            'quiz': quiz, 'attempt': attempt,
            'questions': open_questions, 'existing': existing,
            'time_seconds': quiz.block2_time_minutes * 60,
        })

    elif block == 3:
        test_questions = quiz.test_questions.prefetch_related('answers').all()
        existing = {s.question_id: s.selected_answer_id for s in attempt.test_submissions.all()}
        if request.method == 'POST':
            total_score = 0
            for q in test_questions:
                ans_id = request.POST.get(f'q_{q.id}')
                selected = None
                if ans_id:
                    try:
                        selected = TestAnswer.objects.get(id=ans_id, question=q)
                        if selected.is_correct:
                            total_score += q.points
                    except TestAnswer.DoesNotExist:
                        pass
                TestAnswerSubmission.objects.update_or_create(
                    attempt=attempt, question=q,
                    defaults={'selected_answer': selected}
                )
            attempt.block3_score = total_score
            attempt.status = QuizAttempt.STATUS_COMPLETED
            attempt.completed_at = timezone.now()
            attempt.save()
            return redirect('quiz_results', attempt_id=attempt.id)
        return render(request, 'core/quiz_block3.html', {
            'quiz': quiz, 'attempt': attempt,
            'questions': test_questions, 'existing': existing,
            'time_seconds': quiz.block3_time_minutes * 60,
        })


@login_required
def quiz_block1_done(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    attempt = get_object_or_404(QuizAttempt, student=request.user, quiz=quiz)
    attempt.current_block = 2
    attempt.save()
    return redirect('quiz_block', quiz_id=quiz_id, block=2)


@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=request.user)
    submissions = attempt.test_submissions.select_related('question', 'selected_answer').all()
    open_answers = attempt.open_answers.select_related('question').all()
    return render(request, 'core/quiz_results.html', {
        'attempt': attempt,
        'submissions': submissions,
        'open_answers': open_answers,
    })


# ─── TEACHER VIEWS ───────────────────────────────────────────────────────────

@login_required
def teacher_dashboard(request):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    subjects = request.user.subjects.prefetch_related('quizzes').all()
    return render(request, 'core/teacher_dashboard.html', {'subjects': subjects})


@login_required
def teacher_subject_quizzes(request, subject_id):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    subject = get_object_or_404(Subject, id=subject_id)
    quizzes = Quiz.objects.filter(subject=subject, teacher=request.user)
    return render(request, 'core/teacher_subject_quizzes.html', {
        'subject': subject, 'quizzes': quizzes,
    })


@login_required
def teacher_quiz_detail(request, quiz_id):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    attempts = QuizAttempt.objects.filter(
        quiz=quiz, status=QuizAttempt.STATUS_COMPLETED
    ).select_related('student')
    return render(request, 'core/teacher_quiz_detail.html', {
        'quiz': quiz, 'attempts': attempts,
    })


@login_required
def teacher_grade_attempt(request, attempt_id):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, quiz__teacher=request.user)
    open_answers = attempt.open_answers.select_related('question').all()
    max_score = open_answers.count() * 10

    if request.method == 'POST':
        total = 0
        for answer in open_answers:
            score = int(request.POST.get(f'score_{answer.id}', 0))
            score = max(0, min(score, 10))
            answer.score = score
            answer.save()
            total += score
        attempt.block2_score = total
        attempt.block2_graded = True
        attempt.save()
        messages.success(request, 'Баллдар сәтті сақталды!')
        return redirect('teacher_quiz_detail', quiz_id=attempt.quiz_id)

    return render(request, 'core/teacher_grade_attempt.html', {
        'attempt': attempt, 'open_answers': open_answers,
    })


# ─── QUIZ CREATION ───────────────────────────────────────────────────────────

@login_required
def quiz_create_step1(request, subject_id):
    if not request.user.is_teacher:
        return redirect('student_dashboard')
    subject = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST':
        form = QuizBasicForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = subject
            quiz.teacher = request.user
            quiz.save()
            return redirect('quiz_create_step2', quiz_id=quiz.id)
    else:
        form = QuizBasicForm()
    return render(request, 'core/quiz_create_step1.html', {'form': form, 'subject': subject})


@login_required
def quiz_create_step2(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    if request.method == 'POST':
        # request.FILES міндетті түрде қосылады
        form = QuizTheoryForm(request.POST, request.FILES, instance=quiz)
        if form.is_valid():
            form.save()
            return redirect('quiz_create_step3', quiz_id=quiz.id)
    else:
        form = QuizTheoryForm(instance=quiz)
    return render(request, 'core/quiz_create_step2.html', {'form': form, 'quiz': quiz})


@login_required
def quiz_create_step3(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    questions = quiz.open_questions.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_question':
            text = request.POST.get('question_text', '').strip()
            if text:
                order = questions.count() + 1
                OpenQuestion.objects.create(quiz=quiz, question_text=text, order=order)
        elif action == 'delete_question':
            qid = request.POST.get('question_id')
            OpenQuestion.objects.filter(id=qid, quiz=quiz).delete()
        elif action == 'next':
            time_min = int(request.POST.get('block2_time_minutes', 15))
            quiz.block2_time_minutes = time_min
            quiz.save()
            return redirect('quiz_create_step4', quiz_id=quiz.id)
        return redirect('quiz_create_step3', quiz_id=quiz.id)
    return render(request, 'core/quiz_create_step3.html', {
        'quiz': quiz, 'questions': questions,
    })


@login_required
def quiz_create_step4(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    test_questions = quiz.test_questions.prefetch_related('answers').all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_question':
            text = request.POST.get('question_text', '').strip()
            points = int(request.POST.get('points', 10))
            if text:
                order = test_questions.count() + 1
                q = TestQuestion.objects.create(quiz=quiz, question_text=text, order=order, points=points)
                # Add answers
                for i in range(1, 5):
                    ans_text = request.POST.get(f'answer_{i}', '').strip()
                    is_correct = request.POST.get('correct_answer') == str(i)
                    if ans_text:
                        TestAnswer.objects.create(question=q, answer_text=ans_text, is_correct=is_correct)
        elif action == 'delete_question':
            qid = request.POST.get('question_id')
            TestQuestion.objects.filter(id=qid, quiz=quiz).delete()
        elif action == 'next':
            time_min = int(request.POST.get('block3_time_minutes', 20))
            quiz.block3_time_minutes = time_min
            quiz.save()
            return redirect('quiz_create_step5', quiz_id=quiz.id)
        return redirect('quiz_create_step4', quiz_id=quiz.id)
    return render(request, 'core/quiz_create_step4.html', {
        'quiz': quiz, 'test_questions': test_questions,
    })


@login_required
def quiz_create_step5(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    share_url = request.build_absolute_uri(f'/quiz/{quiz.id}/start/')
    return render(request, 'core/quiz_create_step5.html', {
        'quiz': quiz, 'share_url': share_url,
    })


@login_required
def add_subject(request):
    if request.method == 'POST' and request.user.is_teacher:
        name = request.POST.get('name', '').strip()
        icon = request.POST.get('icon', '📚').strip()
        if name:
            subj, created = Subject.objects.get_or_create(name=name, defaults={'icon': icon})
            request.user.subjects.add(subj)
            return JsonResponse({'success': True, 'id': subj.id, 'name': subj.name})
    return JsonResponse({'success': False})
