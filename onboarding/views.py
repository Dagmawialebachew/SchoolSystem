from django.contrib import messages
from django.views.generic import FormView
from django.urls import reverse_lazy
from .forms import SchoolForm, DivisionForm,FeeStructureForm, DivisionFormSet
from django.shortcuts import render, redirect
from fees.models import FeeStructure
from classes_app.models import Division
from django.forms import formset_factory
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View

class OnboardingBaseView(FormView):
    """Base view to inject step into context automatically."""
    step = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["step"] = self.step
        return context

class SchoolSetupView(OnboardingBaseView):
    template_name = "onboarding/school_setup.html"
    form_class = SchoolForm
    success_url = reverse_lazy("onboarding:division_setup")
    step = "school"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 'school'
        context['progress'] = '35%'
        return context
        
    def form_valid(self, form):
        school = form.save(commit=False)
        school.owner = self.request.user
        school.in_progress = True
        school.save()
        self.request.user.school = school
        self.request.user.save()
        return super().form_valid(form)
    
@method_decorator(login_required, name="dispatch")
class DivisionSetupView(OnboardingBaseView):
    template_name = "onboarding/division_setup.html"
    step = "division"

    GENERAL_DIVISIONS = [
        ("KINDERGARTEN", "Kindergarten"),
        ("PRIMARY_1_4", "Primary (Grades 1–4)"),
        ("PRIMARY_5_8", "Primary (Grades 5–8)"),
        ("SECONDARY_9_12", "Secondary (Grades 9–12)"),
    ]
    
    def get(self, request):
        # Ensure the user has a school first
        if not hasattr(request.user, "school") or request.user.school is None:
            return redirect("onboarding:school_setup")

        existing_divisions = Division.objects.filter(school=request.user.school)
        preselected_general = [
            div.name for div in existing_divisions if div.name in dict(self.GENERAL_DIVISIONS)
        ]

        return render(request, self.template_name, {
            "step": self.step,
            "progress": "70%", 
            "general_divisions": self.GENERAL_DIVISIONS,
            "existing_divisions": existing_divisions,
            "preselected_general": preselected_general,
        })

    def post(self, request):
        if not hasattr(request.user, "school") or request.user.school is None:
            return redirect("onboarding:school_setup")

        school = request.user.school

        # ---- Collect all selected divisions ----
        selected_names = set(request.POST.getlist("general_divisions"))

        custom_divisions = []
        for key in request.POST:
            if key.startswith("custom_name_"):
                idx = key.split("_")[-1]
                name = request.POST.get(f"custom_name_{idx}")
                description = request.POST.get(f"custom_description_{idx}", "")
                if name:
                    custom_divisions.append((name, description))
                    selected_names.add(name)  # Track for syncing

        # ---- Remove divisions that are no longer selected ----
        Division.objects.filter(school=school).exclude(name__in=selected_names).delete()

        # ---- Add or update selected general divisions ----
        for name in request.POST.getlist("general_divisions"):
            Division.objects.get_or_create(
                school=school,
                name=name,
                defaults={"in_progress": True},
            )

        # ---- Add or update custom divisions ----
        for name, description in custom_divisions:
            Division.objects.update_or_create(
                school=school,
                name=name,
                defaults={"description": description, "in_progress": True},
            )

        return redirect("onboarding:fees_setup")

@method_decorator(login_required, name="dispatch")
class FeeSetupView(View):
    template_name = "onboarding/fees_setup.html"
    step = "fees"

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, "has_completed_onboarding", False):
            messages.warning(request, "You have already completed onboarding. Changes are not allowed.")
            return redirect("accounts:pending_approval")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        school = request.user.school
        divisions = Division.objects.filter(school=school)
        fee_types = FeeStructure.FEE_TYPES
        existing_fees = FeeStructure.objects.filter(school=school)

        # Map (division_id, name) -> Fee instance
        fee_map = {}
        for fee in existing_fees:
            fee_map[(fee.division_id, fee.name)] = fee

        return render(request, self.template_name, {
            "step": self.step,
            "progress": "100%",
            "divisions": divisions,
            "fee_types": fee_types,
            "existing_fees": fee_map,
        })

    def post(self, request):
        school = request.user.school
        divisions = Division.objects.filter(school=school)
        fee_types = dict(FeeStructure.FEE_TYPES)

        for div in divisions:
            for ft_key in fee_types.keys():
                key = f"fee_{div.id}_{ft_key}"
                desc_key = f"description_{div.id}_{ft_key}"

                amount = request.POST.get(key)
                description = request.POST.get(desc_key, "")

                if amount and amount.strip():
                    FeeStructure.objects.update_or_create(
                        school=school,
                        division=div,
                        class_program=None,
                        name=ft_key,  # <-- switched back to name
                        defaults={
                            "amount": amount,
                            "description": description if ft_key == FeeStructure.OTHER else "",
                            "in_progress": True,
                        }
                    )

        # Finalize onboarding
        request.user.has_completed_onboarding = True
        school.in_progress = False
        school.save()
        divisions.update(in_progress=False)
        request.user.save()

        messages.success(request, "Onboarding completed successfully! 🎉")
        messages.error(request, "Your account is not yet verified by the Super Admin.")
        return redirect("accounts:pending_approval")