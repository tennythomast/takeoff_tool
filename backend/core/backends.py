from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend to allow users to log in with their email address.
    """
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            # Try to find a user with the given email address
            user = User.objects.get(email=email)
            
            # Check if the password is correct
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            # No user with this email address
            return None
        
        return None
