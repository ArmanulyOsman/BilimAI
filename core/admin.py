from django.contrib import admin
from .models import OpenAnswer, OpenQuestion, Quiz, QuizAttempt, Subject, TestAnswer, TestAnswerSubmission, TestQuestion, User 

admin.site.register(User)
admin.site.register(Subject)
admin.site.register(Quiz)
admin.site.register(OpenQuestion)
admin.site.register(TestQuestion)
admin.site.register(TestAnswer)
admin.site.register(QuizAttempt)
admin.site.register(OpenAnswer)
admin.site.register(TestAnswerSubmission)
