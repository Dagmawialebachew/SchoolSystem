from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Attendance


@login_required
def attendance_list(request):
    attendance = Attendance.objects.for_user(request.user)
    return render(request, 'attendance/list.html', {'attendance': attendance})