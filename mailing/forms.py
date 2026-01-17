from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Client, Mailing, Message


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["email", "full_name", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["subject", "body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
        }


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ["start_time", "end_time", "message", "clients"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "clients": forms.SelectMultiple(attrs={"size": 8}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Показываем только своих клиентов и сообщения
            self.fields["clients"].queryset = Client.objects.filter(owner=user)
            self.fields["message"].queryset = Message.objects.filter(owner=user)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_time")
        end = cleaned_data.get("end_time")

        if start and start < timezone.now():
            raise ValidationError("Время начала не может быть в прошлом.")
        if start and end and start >= end:
            raise ValidationError("Время начала должно быть раньше времени окончания.")
