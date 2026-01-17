from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Создаёт группы "Пользователь" и "Менеджер" с правами'

    def handle(self, *args, **options):
        # Группа "Пользователь"
        user_group, created = Group.objects.get_or_create(name="Пользователь")
        if created:
            self.stdout.write('Создана группа "Пользователь"')

        # Права для пользователя
        user_permissions = [
            # Клиенты
            "add_client",
            "change_client",
            "delete_client",
            "view_client",
            # Сообщения
            "add_message",
            "change_message",
            "delete_message",
            "view_message",
            # Рассылки
            "add_mailing",
            "change_mailing",
            "delete_mailing",
            "view_mailing",
            # Попытки — только просмотр своих
            "view_mailingattempt",
        ]

        for perm_codename in user_permissions:
            try:
                perm = Permission.objects.get(codename=perm_codename)
                user_group.permissions.add(perm)
            except Permission.DoesNotExist:
                self.stdout.write(f"Право {perm_codename} не найдено")

        # Группа "Менеджер"
        manager_group, created = Group.objects.get_or_create(name="Менеджер")
        if created:
            self.stdout.write('Создана группа "Менеджер"')

        # Права менеджера — все права + управление пользователями
        manager_permissions = list(Permission.objects.all())
        manager_group.permissions.set(manager_permissions)

        self.stdout.write(self.style.SUCCESS("Группы успешно созданы и настроены."))
