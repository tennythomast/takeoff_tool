import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.apps import apps


class BaseModel(models.Model):
    """Abstract base model with UUID primary key and timestamp fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeletableManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted_only(self):
        return super().get_queryset().filter(is_active=False)


class SoftDeletableMixin(BaseModel):
    """Abstract mixin that adds soft delete functionality."""
    is_active = models.BooleanField(
        _('active'),
        default=True,
        db_index=True,
        help_text=_('Designates whether this record should be treated as active. '
                  'Unselect this instead of deleting.')
    )
    deactivated_at = models.DateTimeField(_('deactivated at'), null=True, blank=True)

    class Meta(BaseModel.Meta):
        abstract = True

    def soft_delete(self):
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.save()

    def restore(self):
        self.is_active = True
        self.deactivated_at = None
        self.save()


class Organization(SoftDeletableMixin):
    class OrgType(models.TextChoices):
        SOLO = 'SOLO', _('Solo User')
        TEAM = 'TEAM', _('Team')
        ENTERPRISE = 'ENTERPRISE', _('Enterprise')

    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    org_type = models.CharField(
        max_length=20,
        choices=OrgType.choices,
        default=OrgType.SOLO,
        db_index=True
    )
    api_key_strategy = models.CharField(
        max_length=20,
        choices=[
            ('DATAELAN', 'Use Dataelan API Keys'),
            ('BYOK', 'Bring Your Own Keys'),  # Bring Your Own Keys
            ('HYBRID', 'Mixed Strategy')
        ],
        default='DATAELAN',
        help_text=_('Strategy for managing API keys across LLM providers')
    )
    monthly_ai_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monthly AI spending budget in USD'
    )
    
    ai_usage_alerts = models.BooleanField(
        default=True,
        help_text='Send alerts when approaching budget limits'
    )
    
    # Caching settings
    default_cache_enabled = models.BooleanField(
        default=True,
        help_text='Enable response caching by default for all agents in this organization'
    )
    default_cache_ttl_hours = models.PositiveIntegerField(
        default=24,
        help_text='Default time-to-live for cached responses in hours'
    )
    
    # Routing preferences
    default_optimization_strategy = models.CharField(
        max_length=20,
        choices=[
            ('cost_first', 'Cost First'),
            ('balanced', 'Balanced'),
            ('quality_first', 'Quality First'),
            ('performance_first', 'Performance First'),
        ],
        default='balanced'
    )

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['is_active', 'slug'])
        ]

    def __str__(self):
        status = 'Inactive' if not self.is_active else 'Active'
        return f'{self.name} [{status}]'

    def delete(self, using=None, keep_parents=False):
        """Override delete method to prevent actual deletion"""
        self.soft_delete()
        return True
    
    def get_current_month_ai_spend(self):
        """Get current month AI spending"""
        # Use lazy import to avoid circular dependency
        ModelMetrics = apps.get_model('modelhub', 'ModelMetrics')
        
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = ModelMetrics.objects.filter(
            organization=self,
            timestamp__gte=start_of_month
        ).aggregate(
            total_cost=models.Sum('cost')
        )
        
        return result['total_cost'] or Decimal('0.00')
    
    def is_approaching_budget(self, threshold=0.8):
        """Check if organization is approaching budget limit"""
        if not self.monthly_ai_budget:
            return False
            
        current_spend = self.get_current_month_ai_spend()
        return current_spend >= (self.monthly_ai_budget * Decimal(str(threshold)))


class CustomUserManager(BaseUserManager, SoftDeletableManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, SoftDeletableMixin):
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        error_messages={
            'unique': _('A user with that email already exists.'),
        },
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        db_index=True,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        db_index=True,
        help_text=_('Designates whether this user has verified their email address.'),
    )
    # Note: default_org field removed as users can only belong to one organization
    # Instead, we use the organization property to get the user's single organization
    last_login_ip = models.GenericIPAddressField(
        _('last login IP'),
        null=True,
        blank=True,
        help_text=_('The IP address of the last successful login.')
    )
    
    @property
    def default_org(self):
        """
        Backward compatibility property that returns the user's single organization.
        This allows existing code to continue working without modification.
        """
        return self.organization

    objects = CustomUserManager()
    all_objects = models.Manager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'email']),
            models.Index(fields=['is_active', 'created_at'])
        ]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def has_role(self, org: 'Organization', role: str) -> bool:
        """Check if user has the specified role or higher in the organization."""
        membership = self.memberships.filter(organization=org).first()
        return membership.has_role(role) if membership else False

    def is_owner(self, org: 'Organization') -> bool:
        """Check if user is owner of the organization."""
        return self.has_role(org, Membership.Role.OWNER)

    def is_admin(self, org: 'Organization') -> bool:
        """Check if user is admin or higher in the organization."""
        return self.has_role(org, Membership.Role.ADMIN)

    def is_member(self, org: 'Organization') -> bool:
        """Check if user is a member of the organization."""
        return self.has_role(org, Membership.Role.MEMBER)

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        if not self.first_name and not self.last_name:
            # If no name is provided, use the part before @ in the email as first name
            self.first_name = self.email.split('@')[0]
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name if full_name else self.email

    def __str__(self):
        return self.full_name

    def update_last_login_ip(self, ip_address):
        """Update the last login IP address"""
        self.last_login_ip = ip_address
        self.save(update_fields=['last_login_ip'])

    def delete(self, using=None, keep_parents=False):
        """Override delete method to prevent actual deletion"""
        self.soft_delete()
        return True

    @property
    def organization(self):
        """
        Get the user's organization.
        Since a user can only be a member of one organization, this returns that organization.
        """
        # Get the user's organization from their membership
        membership = self.memberships.select_related('organization').filter(
            organization__is_active=True
        ).first()
        return membership.organization if membership else None
        

    def get_organizations(self):
        """
        Get the user's organization as a queryset.
        Since a user can only be a member of one organization, this returns a queryset with at most one item.
        """
        org = self.organization
        if org:
            return Organization.objects.filter(id=org.id)
        return Organization.objects.none()

    def get_membership(self, organization):
        """Get user's membership for a specific organization."""
        return self.memberships.filter(organization=organization).first()

    def has_org_permission(self, organization, min_role='MEMBER'):
        """
        Check if user has minimum role in organization.
        Uses the existing role hierarchy from Membership model.
        """
        membership = self.get_membership(organization)
        if not membership:
            return False
        
        return membership.has_role(min_role)

    def set_default_organization(self, organization):
        """
        This method is maintained for backward compatibility.
        Since users can only belong to one organization, this method
        simply verifies the user is a member of the specified organization.
        Returns True if user is a member, False otherwise.
        """
        if not organization.is_active:
            return False
            
        membership = self.get_membership(organization)
        return membership is not None

    def get_role_in_org(self, organization):
        """Get user's role in a specific organization."""
        membership = self.get_membership(organization)
        return membership.role if membership else None

class Membership(BaseModel):
    class Role(models.TextChoices):
        OWNER = 'OWNER', _('Owner')
        ADMIN = 'ADMIN', _('Admin')
        MEMBER = 'MEMBER', _('Member')

    # Role hierarchies for permission checking
    ADMIN_ROLES = {Role.ADMIN, Role.OWNER}
    ALL_ROLES = {Role.MEMBER, Role.ADMIN, Role.OWNER}

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='memberships',
        limit_choices_to={'is_active': True}
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
        limit_choices_to={'is_active': True}
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        db_index=True
    )

    class Meta:
        verbose_name = _('membership')
        verbose_name_plural = _('memberships')
        # Enforce one organization per user by making the user field unique
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_membership')
        ]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['organization', 'role']),
            models.Index(fields=['created_at'])
        ]

    def __str__(self):
        return f'{self.user.email} - {self.organization.name} ({self.role})'

    def is_owner(self) -> bool:
        """Check if the membership has owner role."""
        return self.role == self.Role.OWNER

    def is_admin(self) -> bool:
        """Check if the membership has admin or higher role."""
        return self.role in self.ADMIN_ROLES

    def is_member(self) -> bool:
        """Check if the membership has any valid role."""
        return self.role in self.ALL_ROLES

    def has_role(self, role: str) -> bool:
        """Check if the membership has the specified role or higher."""
        if role == self.Role.MEMBER:
            return self.is_member()
        elif role == self.Role.ADMIN:
            return self.is_admin()
        elif role == self.Role.OWNER:
            return self.is_owner()
        return False