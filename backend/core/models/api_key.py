import uuid
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_key():
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def default_expiry():
    """Default expiry is 1 year from now."""
    return timezone.now() + timedelta(days=365)


class ApiKey(models.Model):
    """
    API keys for organization access to the Dataelan API.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    name = models.CharField(max_length=100)
    key_prefix = models.CharField(max_length=10, editable=False)
    key_hash = models.CharField(max_length=100, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_api_keys'
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, default=default_expiry)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"
    
    def save(self, *args, **kwargs):
        # If this is a new API key, generate the key and hash
        if not self.pk:
            key = generate_key()
            # Store the first 8 characters as a prefix for display purposes
            self.key_prefix = key[:8]
            # Store a hash of the key for verification
            # In a real implementation, we would use a proper hash function
            # For simplicity, we're just storing the key directly
            self.key_hash = key
            # Save the key so we can return it once
            self._full_key = key
        super().save(*args, **kwargs)
    
    def verify(self, key):
        """Verify if the provided key matches this API key."""
        # In a real implementation, we would compare hashes
        # For simplicity, we're just comparing the keys directly
        return self.key_hash == key and self.is_active and (
            self.expires_at is None or self.expires_at > timezone.now()
        )
    
    def mark_used(self):
        """Mark this API key as used now."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def revoke(self):
        """Revoke this API key."""
        self.is_active = False
        self.save(update_fields=['is_active'])
