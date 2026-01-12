from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Client, Message, Mailing, send_mailing, MailingAttempt
from .forms import ClientForm, MessageForm, MailingForm

from django.views.generic import TemplateView
from django.views.generic import View

from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin


# ========== Главная страница ==========
class HomePageView(TemplateView):
    template_name = 'mailing/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context['total_mailings'] = Mailing.objects.count()
        context['active_mailings'] = Mailing.objects.filter(
            start_time__lte=now,
            end_time__gte=now
        ).count()
        context['total_clients'] = Client.objects.count()
        return context


# ========== CLIENTS ==========
class ClientListView(ListView):
    model = Client
    template_name = 'mailing/client_list.html'
    context_object_name = 'clients'


class ClientCreateView(CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'
    success_url = reverse_lazy('mailing:client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Создание'
        return context


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'mailing/client_form.html'
    success_url = reverse_lazy('mailing:client_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Редактирование'
        return context


class ClientDeleteView(DeleteView):
    model = Client
    template_name = 'mailing/client_confirm_delete.html'
    success_url = reverse_lazy('mailing:client_list')


# ========== MESSAGES ==========
class MessageListView(ListView):
    model = Message
    template_name = 'mailing/message_list.html'
    context_object_name = 'messages'


class MessageCreateView(CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Создание'
        return context


class MessageUpdateView(UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Редактирование'
        return context


class MessageDeleteView(DeleteView):
    model = Message
    template_name = 'mailing/message_confirm_delete.html'
    success_url = reverse_lazy('mailing:message_list')


# ========== MAILINGS ==========
class MailingListView(ListView):
    model = Mailing
    template_name = 'mailing/mailing_list.html'
    context_object_name = 'mailings'


class MailingCreateView(CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Создание'
        return context


class MailingUpdateView(UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = self.model._meta.verbose_name
        context['action'] = 'Редактирование'
        return context


class MailingDeleteView(DeleteView):
    model = Mailing
    template_name = 'mailing/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailing:mailing_list')


class MailingSendView(View):
    def post(self, request, pk):
        mailing = Mailing.objects.get(pk=pk)
        now = timezone.now()

        if not (mailing.start_time <= now <= mailing.end_time):
            messages.error(
                request,
                f"Рассылку можно отправлять только с {mailing.start_time} по {mailing.end_time}."
            )
            return redirect('mailing:mailing_list')

        successes, failures = send_mailing(mailing)
        messages.success(request, f'Рассылка отправлена! Успешно: {successes}, Ошибок: {failures}')
        return redirect('mailing:mailing_list')


class UserReportView(LoginRequiredMixin, TemplateView):
    template_name = 'mailing/user_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Все рассылки пользователя
        user_mailings = Mailing.objects.filter(owner=user)

        # Все попытки по его рассылкам
        attempts = MailingAttempt.objects.filter(mailing__owner=user)

        # Статистика
        total_attempts = attempts.count()
        successful_attempts = attempts.filter(status='Успешно').count()
        failed_attempts = attempts.filter(status='Не успешно').count()

        # Уникальные получатели (все клиенты из всех его рассылок)
        unique_clients = Client.objects.filter(mailing__owner=user).distinct().count()

        context.update({
            'total_mailings': user_mailings.count(),
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': failed_attempts,
            'unique_clients': unique_clients,
            'success_rate': round(successful_attempts / total_attempts * 100, 1) if total_attempts > 0 else 0,
        })
        return context