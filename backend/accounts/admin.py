from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditEvent, User


@admin.register(User)
class InstitutionalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Institucional", {"fields": ("role",)}),)
    list_display = ("username", "first_name", "last_name", "role", "is_active")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id")
    readonly_fields = (
        "id",
        "actor",
        "action",
        "object_type",
        "object_id",
        "changed_fields",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
