from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.db import transaction
from .models import User, Organization, Membership


def create_personal_org(user):
    """Create a personal organization for a new user"""
    base_name = f"{user.full_name}'s Organization" if user.full_name else f"{user.email.split('@')[0]}'s Organization"
    name = base_name
    slug = slugify(name)
    counter = 1

    # Ensure unique slug
    while Organization.objects.filter(slug=slug).exists():
        name = f"{base_name} {counter}"
        slug = slugify(name)
        counter += 1

    with transaction.atomic():
        # Create organization
        org = Organization.objects.create(
            name=name,
            slug=slug,
            org_type=Organization.OrgType.SOLO
        )

        # Create membership with owner role
        Membership.objects.create(
            user=user,
            organization=org,
            role=Membership.Role.OWNER
        )


    return org


@receiver(post_save, sender=User)
def create_user_organization(sender, instance, created, **kwargs):
    """
    Signal to create a personal organization when a new user is created
    """
    if created and not instance.default_org:
        create_personal_org(instance)
