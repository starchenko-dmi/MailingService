from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (CreateView, DeleteView, ListView,
                                  TemplateView, UpdateView, View)

from .forms import ClientForm, MailingForm, MessageForm
from .models import Client, Mailing, MailingAttempt, Message, send_mailing


# ========== Главная страница ==========
class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = "mailing/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cache_key = f"home_stats_user_{user.id}"
        stats = cache.get(cache_key)

        if stats is None:
            now = timezone.now()
            if user.groups.filter(name="Менеджер").exists():
                total_mailings = Mailing.objects.count()
                active_mailings = Mailing.objects.filter(
                    start_time__lte=now, end_time__gte=now
                ).count()
                total_clients = Client.objects.count()
            else:
                total_mailings = Mailing.objects.filter(owner=user).count()
                active_mailings = Mailing.objects.filter(
                    owner=user, start_time__lte=now, end_time__gte=now
                ).count()
                total_clients = Client.objects.filter(owner=user).count()

            stats = {
                "total_mailings": total_mailings,
                "active_mailings": active_mailings,
                "total_clients": total_clients,
            }
            cache.set(cache_key, stats, 300)  # 5 минут

        context.update(stats)
        return context


# ========== CLIENTS ==========
class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "mailing/client_list.html"
    context_object_name = "clients"

    def get_queryset(self):
        user = self.request.user
        cache_key = f"client_list_{user.id}"
        queryset = cache.get(cache_key)

        if queryset is None:
            if user.groups.filter(name="Менеджер").exists():
                queryset = list(Client.objects.all())
            else:
                queryset = list(Client.objects.filter(owner=user))
            cache.set(cache_key, queryset, 600)  # 10 минут

        return queryset


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        cache.delete(f"client_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Создание"
        return context


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "mailing/client_form.html"
    success_url = reverse_lazy("mailing:client_list")

    def get_queryset(self):
        return Client.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        cache.delete(f"client_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Редактирование"
        return context


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "mailing/client_confirm_delete.html"
    success_url = reverse_lazy("mailing:client_list")

    def get_queryset(self):
        return Client.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        cache.delete(f"client_list_{self.request.user.id}")
        return response


# ========== MESSAGES ==========
class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "mailing/message_list.html"
    context_object_name = "messages"

    def get_queryset(self):
        user = self.request.user
        cache_key = f"message_list_{user.id}"
        queryset = cache.get(cache_key)

        if queryset is None:
            if user.groups.filter(name="Менеджер").exists():
                queryset = list(Message.objects.all())
            else:
                queryset = list(Message.objects.filter(owner=user))
            cache.set(cache_key, queryset, 600)

        return queryset


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        cache.delete(f"message_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Создание"
        return context


class MessageUpdateView(LoginRequiredMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = "mailing/message_form.html"
    success_url = reverse_lazy("mailing:message_list")

    def get_queryset(self):
        return Message.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        cache.delete(f"message_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Редактирование"
        return context


class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "mailing/message_confirm_delete.html"
    success_url = reverse_lazy("mailing:message_list")

    def get_queryset(self):
        return Message.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        cache.delete(f"message_list_{self.request.user.id}")
        return response


# ========== MAILINGS ==========
class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = "mailing/mailing_list.html"
    context_object_name = "mailings"

    def get_queryset(self):
        user = self.request.user
        cache_key = f"mailing_list_{user.id}"
        queryset = cache.get(cache_key)

        if queryset is None:
            if user.groups.filter(name="Менеджер").exists():
                queryset = list(Mailing.objects.all())
            else:
                queryset = list(Mailing.objects.filter(owner=user))
            cache.set(cache_key, queryset, 600)

        return queryset


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        cache.delete(f"mailing_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Создание"
        return context


class MailingUpdateView(LoginRequiredMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = "mailing/mailing_form.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        cache.delete(f"mailing_list_{self.request.user.id}")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verbose_name"] = self.model._meta.verbose_name
        context["action"] = "Редактирование"
        return context


class MailingDeleteView(LoginRequiredMixin, DeleteView):
    model = Mailing
    template_name = "mailing/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing:mailing_list")

    def get_queryset(self):
        return Mailing.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        cache.delete(f"mailing_list_{self.request.user.id}")
        return response


class MailingSendView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if (
            mailing.owner != request.user
            and not request.user.groups.filter(name="Менеджер").exists()
        ):
            raise PermissionDenied("Вы не можете отправлять эту рассылку.")

        now = timezone.now()
        if not (mailing.start_time <= now <= mailing.end_time):
            messages.error(
                request,
                f"Рассылку можно отправлять только с {mailing.start_time.strftime('%d.%m.%Y %H:%M')} "
                f"по {mailing.end_time.strftime('%d.%m.%Y %H:%M')}.",
            )
            return redirect("mailing:mailing_list")

        successes, failures = send_mailing(mailing)
        messages.success(
            request, f"Рассылка отправлена! Успешно: {successes}, Ошибок: {failures}"
        )
        return redirect("mailing:mailing_list")


# ========== СТАТИСТИКА ==========
class UserReportView(LoginRequiredMixin, TemplateView):
    template_name = "mailing/user_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.groups.filter(name="Менеджер").exists():
            attempts = MailingAttempt.objects.all()
            mailings = Mailing.objects.all()
            unique_clients = Client.objects.count()
        else:
            attempts = MailingAttempt.objects.filter(mailing__owner=user)
            mailings = Mailing.objects.filter(owner=user)
            unique_clients = Client.objects.filter(owner=user).count()

        total_attempts = attempts.count()
        successful_attempts = attempts.filter(status="Успешно").count()
        failed_attempts = attempts.filter(status="Не успешно").count()

        context.update(
            {
                "total_mailings": mailings.count(),
                "total_attempts": total_attempts,
                "successful_attempts": successful_attempts,
                "failed_attempts": failed_attempts,
                "unique_clients": unique_clients,
                "success_rate": (
                    round(successful_attempts / total_attempts * 100, 1)
                    if total_attempts > 0
                    else 0
                ),
            }
        )
        return context
