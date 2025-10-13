from django.contrib import messages

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, "role", None) == "PARENT":
            if user.check_password("1234"):
                messages.warning(
                    request,
                    "You’re using the default password (1234). Please change it."
                )
        return self.get_response(request)
