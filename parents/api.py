from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json

from parents.models import ParentProfile

@csrf_exempt
def save_chat_id(request):
    try:
        data = json.loads(request.body)
        parent_id = data.get("parent_id")
        chat_id = data.get("chat_id")

        parent = ParentProfile.objects.filter(id=parent_id).first()
        if not parent:
            return JsonResponse({"success": False, "message": "Parent not found."}, status=404)

        parent.telegram_chat_id = chat_id
        parent.save()

        return JsonResponse({"success": True, "message": "Chat ID saved successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def disconnect_chat_id(request):
    print("📩 Raw body:", request.body)
    print("📩 Content type:", request.content_type)

    try:
        # Parse incoming data based on content type
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "message": "Invalid or empty JSON data."}, status=400)
        else:
            data = request.POST or request.GET

        parent_id = data.get("parent_id")
        if not parent_id:
            return JsonResponse({"success": False, "message": "Missing parent_id."}, status=400)

        parent = ParentProfile.objects.filter(id=parent_id).first()
        if not parent:
            return JsonResponse({"success": False, "message": "Parent not found."}, status=404)

        parent.telegram_chat_id = None
        parent.save()

        return JsonResponse({"success": True, "message": "Telegram disconnected successfully."})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Unexpected error: {str(e)}"}, status=500)
