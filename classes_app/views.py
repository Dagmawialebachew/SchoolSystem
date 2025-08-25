from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ClassProgram


@login_required
def class_list(request):
    classes = ClassProgram.objects.for_user(request.user)
    return render(request, 'classes_app/list.html', {'classes': classes})