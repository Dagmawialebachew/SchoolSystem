from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Payment


@login_required
def payment_list(request):
    payments = Payment.objects.for_user(request.user)
    return render(request, 'fees/list.html', {'payments': payments})