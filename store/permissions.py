from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUserOrReadOnly(BasePermission):
    """
    Admin (is_staff) users have full access.
    Others have read-only access.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class IsReviewOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.customer.user == request.user or request.user.is_staff
