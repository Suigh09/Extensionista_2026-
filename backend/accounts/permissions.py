from rest_framework.permissions import BasePermission


class IsInstitutionalAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "ADMIN")


class IsAcademicStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role in {"ADMIN", "SECRETARIAT"})
