from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import School


@login_required
def school_list(request):
    schools = School.objects.all()
    return render(request, 'schools/list.html', {'schools': schools})