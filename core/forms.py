from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Subject, Quiz, OpenQuestion, TestQuestion, TestAnswer


class StudentRegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Құпиясөз')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Құпиясөзді растаңыз')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'patronymic', 'email']
        labels = {
            'username': 'Пайдаланушы аты',
            'first_name': 'Аты',
            'last_name': 'Тегі',
            'patronymic': 'Әкесінің аты',
            'email': 'Email',
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Құпиясөздер сәйкес келмейді')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = User.ROLE_STUDENT
        if commit:
            user.save()
        return user


class TeacherRegisterForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label='Құпиясөз')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Құпиясөзді растаңыз')
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label='Пәндер',
        required=False
    )
    new_subject = forms.CharField(max_length=100, required=False, label='Жаңа пән қосу')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'patronymic', 'email']
        labels = {
            'username': 'Пайдаланушы аты',
            'first_name': 'Аты',
            'last_name': 'Тегі',
            'patronymic': 'Әкесінің аты',
            'email': 'Email',
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Құпиясөздер сәйкес келмейді')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = User.ROLE_TEACHER
        if commit:
            user.save()
            # Add existing subjects
            subjects = self.cleaned_data.get('subjects', [])
            user.subjects.set(subjects)
            # Add new subject if provided
            new_subj = self.cleaned_data.get('new_subject', '').strip()
            if new_subj:
                subj, _ = Subject.objects.get_or_create(name=new_subj)
                user.subjects.add(subj)
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Пайдаланушы аты')
    password = forms.CharField(widget=forms.PasswordInput, label='Құпиясөз')


class QuizBasicForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'passing_score']
        labels = {
            'title': 'Тест атауы',
            'passing_score': 'Өту балы (%)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Тест атауын енгізіңіз...'}),
        }


class QuizTheoryForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['theory_content', 'theory_image', 'theory_time_minutes']
        labels = {
            'theory_content': 'Теория мазмұны',
            'theory_image': 'Сурет (міндетті емес)',
            'theory_time_minutes': 'Оқуға уақыт (минут)',
        }
        widgets = {
            'theory_content': forms.Textarea(attrs={'rows': 12, 'placeholder': 'Теориялық материалды енгізіңіз...'}),
        }


class QuizBlock2Form(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['block2_time_minutes']
        labels = {
            'block2_time_minutes': '2-блокқа уақыт (минут)',
        }


class QuizBlock3Form(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['block3_time_minutes']
        labels = {
            'block3_time_minutes': '3-блокқа уақыт (минут)',
        }


class OpenQuestionForm(forms.ModelForm):
    class Meta:
        model = OpenQuestion
        fields = ['question_text']
        labels = {'question_text': 'Сұрақ мәтіні'}
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Сұрақты енгізіңіз...'}),
        }


class TestQuestionForm(forms.ModelForm):
    class Meta:
        model = TestQuestion
        fields = ['question_text', 'points']
        labels = {
            'question_text': 'Сұрақ мәтіні',
            'points': 'Балл',
        }
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Сұрақты енгізіңіз...'}),
        }


class GradeBlock2Form(forms.Form):
    score = forms.IntegerField(min_value=0, label='Балл')

    def __init__(self, *args, max_score=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['score'].max_value = max_score
        self.fields['score'].widget.attrs['max'] = max_score
        self.fields['score'].widget.attrs['min'] = 0
