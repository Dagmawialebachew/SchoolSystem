# notifications/forms.py
from django import forms

from classes_app.models import ClassProgram, Division
from .models import Announcement, DELIVERY_CHOICES

class AnnouncementForm(forms.ModelForm):
    delivery_channels = forms.MultipleChoiceField(
        choices=DELIVERY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Delivery Channels"
    )
    attachments = forms.FileField(
        widget=forms.ClearableFileInput,
        required=False,
        label="Attachments"
    )
    classes = forms.ModelMultipleChoiceField(
        queryset=ClassProgram.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "hidden"})  # hide the default
    )
    division = forms.ModelMultipleChoiceField(
        queryset=Division.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "hidden"})  # hide the default
    )
    
    class Meta:
        model = Announcement
        fields = [
            "title", "message",
            "priority", "pinned",
            "target", "division", "classes",   # 👈 include division if model has it
            "publish_at", "expires_at",
            "delivery_channels",
            "links", "videos",
            "category", "attachments"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "e.g. School reopening on Monday"
            }),
            "message": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "e.g. Dear parents, classes will resume on Monday at 8:00 AM sharp..."
            }),
            "publish_at": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "placeholder": "e.g. 2025-09-30 08:00"
            }),
            "expires_at": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "placeholder": "e.g. 2025-10-05 18:00"
            }),
            "links": forms.URLInput(attrs={
                "placeholder": "e.g. https://schoolportal.com/updates"
            }),
            "videos": forms.URLInput(attrs={
                "placeholder": "e.g. https://youtube.com/watch?v=12345"
            }),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'school'):
            self.fields['division'].queryset = Division.objects.filter(school=user.school)
            self.fields['classes'].queryset = ClassProgram.objects.filter(school=user.school)
        else:
            self.fields['division'].queryset = Division.objects.none()
            self.fields['classes'].queryset = ClassProgram.objects.none()

        self.fields['division'].label_from_instance = lambda obj: obj.name
        self.fields['classes'].label_from_instance = lambda obj: f"{obj.name}"

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get("target")
        classes = cleaned.get("classes")
        division = cleaned.get("division")

        if target == "CLASS" and (not classes or classes.count() == 0):
            self.add_error("classes", "Select at least one class for CLASS-targeted announcements.")

        if target == "DIVISION" and not division:
            self.add_error("division", "Select a division for DIVISION-targeted announcements.")

        return cleaned
