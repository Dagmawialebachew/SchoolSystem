from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Document


@login_required
def document_list(request):
    documents = Document.objects.for_user(request.user)
    return render(request, 'documents/list.html', {'documents': documents})