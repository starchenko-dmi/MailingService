from django.db import models
from django.core.validators import EmailValidator

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User


class Client(models.Model):
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        verbose_name="Email"
    )
    full_name = models.CharField(max_length=255, verbose_name="Ф. И. О.")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        verbose_name = "Получатель"
        verbose_name_plural = "Получатели"


class Message(models.Model):
    subject = models.CharField(max_length=255, verbose_name="Тема письма")
    body = models.TextField(verbose_name="Тело письма")

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"


class Mailing(models.Model):
    start_time = models.DateTimeField(verbose_name="Дата и время первой отправки")
    end_time = models.DateTimeField(verbose_name="Дата и время окончания отправки")
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name="Сообщение"
    )
    clients = models.ManyToManyField(
        Client,
        verbose_name="Получатели"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Владелец",
        null=True,  # временно, чтобы миграция прошла
        blank=True
    )

    def __str__(self):
        return f"Рассылка от {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def status(self):
        from django.utils import timezone
        now = timezone.now()
        if now < self.start_time:
            return 'Создана'
        elif now <= self.end_time:
            return 'Запущена'
        else:
            return 'Завершена'

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"


class MailingAttempt(models.Model):
    STATUS_CHOICES = [
        ('Успешно', 'Успешно'),
        ('Не успешно', 'Не успешно'),
    ]

    attempt_time = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время попытки")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Статус")
    server_response = models.TextField(blank=True, null=True, verbose_name="Ответ почтового сервера")
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        verbose_name="Рассылка"
    )

    def __str__(self):
        return f"Попытка {self.attempt_time} — {self.status}"

    class Meta:
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылок"


def send_mailing(mailing: Mailing):
    """
    Отправляет рассылку всем клиентам и сохраняет попытки.
    """
    successes = 0
    failures = 0

    for client in mailing.clients.all():
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                fail_silently=False,
            )
            MailingAttempt.objects.create(
                mailing=mailing,
                status='Успешно',
                server_response='Письмо отправлено успешно.'
            )
            successes += 1
        except Exception as e:
            MailingAttempt.objects.create(
                mailing=mailing,
                status='Не успешно',
                server_response=str(e)
            )
            failures += 1

    return successes, failures