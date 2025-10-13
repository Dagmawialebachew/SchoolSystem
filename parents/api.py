from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import ParentProfile
import json

@csrf_exempt
def save_chat_id(request):
    try:
        data = json.loads(request.body)
        parent_id = data.get("parent_id")
        chat_id = data.get("chat_id")

        parent = ParentProfile.objects.filter(id=parent_id).first()
        if not parent:
            return JsonResponse({"status": "error", "message": "Parent not found"}, status=404)

        parent.telegram_chat_id = chat_id
        parent.save()

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
