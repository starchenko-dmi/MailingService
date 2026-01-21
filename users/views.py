from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import ListView

from .forms import CustomUserCreationForm


# ====== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======
def is_manager(user):
    return user.groups.filter(name="Менеджер").exists()


# ====== ПРЕДСТАВЛЕНИЯ ======
@method_decorator(user_passes_test(is_manager), name="dispatch")
class UserListView(ListView):
    model = User
    template_name = "users/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.filter(is_superuser=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем флаг is_manager для каждого пользователя
        users_with_roles = []
        for user in context["users"]:
            users_with_roles.append(
                {
                    "user": user,
                    "is_manager": user.groups.filter(name="Менеджер").exists(),
                }
            )
        context["users_with_roles"] = users_with_roles
        return context


@user_passes_test(is_manager)
def promote_to_manager(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user or user.is_superuser:
        messages.warning(request, "Недопустимое действие.")
        return redirect("users:user_list")

    try:
        manager_group = Group.objects.get(name="Менеджер")
        user.groups.add(manager_group)
        messages.success(request, f"Пользователь {user.username} теперь менеджер.")
    except Group.DoesNotExist:
        messages.error(
            request, 'Группа "Менеджер" не найдена. Обратитесь к администратору.'
        )

    return redirect("users:user_list")


@user_passes_test(is_manager)
def demote_from_manager(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user or user.is_superuser:
        messages.warning(request, "Недопустимое действие.")
        return redirect("users:user_list")

    try:
        manager_group = Group.objects.get(name="Менеджер")
        user.groups.remove(manager_group)
        messages.info(request, f"Пользователь {user.username} больше не менеджер.")
    except Group.DoesNotExist:
        messages.error(request, 'Группа "Менеджер" не найдена.')

    return redirect("users:user_list")


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                user_group = Group.objects.get(name="Пользователь")
                user.groups.add(user_group)
            except Group.DoesNotExist:
                messages.warning(
                    request,
                    'Группа "Пользователь" не найдена. Выполните команду create_groups.',
                )

            current_site = get_current_site(request)
            mail_subject = "Активируйте ваш аккаунт"
            message = render_to_string(
                "users/acc_active_email.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": default_token_generator.make_token(user),
                },
            )
            to_email = form.cleaned_data.get("email")
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.send()

            messages.success(
                request,
                "Пожалуйста, подтвердите свой email для завершения регистрации.",
            )
            return redirect("mailing:home")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active:
            messages.info(request, "Ваш аккаунт уже активирован.")
        else:
            user.is_active = True
            user.save()
            messages.success(
                request, "Ваш аккаунт успешно активирован. Теперь вы можете войти."
            )
        return redirect("users:login")
    else:
        messages.error(request, "Ссылка активации недействительна.")
        return redirect("mailing:home")


def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None and user.is_active:
                login(request, user)
                return redirect("mailing:home")
            else:
                messages.error(request, "Аккаунт не активирован. Проверьте email.")
        else:
            messages.error(request, "Неверное имя пользователя или пароль.")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect("mailing:home")


@user_passes_test(is_manager)
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user or user.is_superuser:
        messages.error(request, "Нельзя заблокировать себя или суперпользователя.")
        return redirect("users:user_list")

    user.is_active = False
    user.save()
    messages.warning(request, f"Пользователь {user.username} заблокирован.")
    return redirect("users:user_list")


@user_passes_test(is_manager)
def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user or user.is_superuser:
        messages.error(request, "Нельзя разблокировать себя или суперпользователя.")
        return redirect("users:user_list")

    user.is_active = True
    user.save()
    messages.success(request, f"Пользователь {user.username} разблокирован.")
    return redirect("users:user_list")
