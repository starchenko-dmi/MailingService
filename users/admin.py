from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_active", "get_groups")
    list_filter = ("is_active", "groups")
    actions = ["make_manager"]

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])

    get_groups.short_description = "Группы"

    @admin.action(description="Назначить менеджером")
    def make_manager(self, request, queryset):
        manager_group = Group.objects.get(name="Менеджер")
        for user in queryset:
            user.groups.add(manager_group)
        self.message_user(request, "Выбранные пользователи стали менеджерами.")
