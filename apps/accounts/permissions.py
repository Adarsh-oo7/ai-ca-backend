"""
Accounts App - Permissions
"""
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """Only allow access to the single student user."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_student


class IsAdminUser(BasePermission):
    """Only allow access to admin users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff
