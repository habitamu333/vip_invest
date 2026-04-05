from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        # Use the User's phone if it exists, otherwise empty string
        phone = getattr(instance, "phone", "")
        Profile.objects.create(user=instance, phone=phone)