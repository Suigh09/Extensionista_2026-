from accounts.models import User
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    message = "Ação disponível somente para aluno ativo."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.STUDENT
            and hasattr(request.user, "student_profile")
        )


class IsProfessor(BasePermission):
    message = "Ação disponível somente para professor ativo."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.PROFESSOR
            and hasattr(request.user, "professor_profile")
        )
