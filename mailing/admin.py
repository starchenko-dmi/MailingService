from django.contrib import admin

from .models import Client, Mailing, MailingAttempt, Message

admin.site.register(Client)
admin.site.register(Message)
admin.site.register(Mailing)
admin.site.register(MailingAttempt)
