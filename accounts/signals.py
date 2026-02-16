from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.account.models import EmailAddress
from .models import Customer

@receiver(post_save, sender=EmailAddress)
def sync_email_address_to_customer(sender, instance, **kwargs):
    """
    When an EmailAddress is verified/unverified, update the corresponding Customer.
    """
    user = instance.user
    if hasattr(user, 'customer'):
        customer = user.customer
        if customer.is_email_verified != instance.verified:
            customer.is_email_verified = instance.verified
            customer.save(update_fields=['is_email_verified'])

@receiver(post_save, sender=Customer)
def sync_customer_to_email_address(sender, instance, **kwargs):
    """
    When a Admin toggles Customer.is_email_verified, update the Allauth EmailAddress.
    """
    user = instance.user
    # Avoid recursion: check if the state actually needs changing
    # We find the primary email or the one matching instance.email
    email_params = {'user': user, 'email': instance.email}
    
    # Try to find specific email, otherwise primary
    email_obj = EmailAddress.objects.filter(**email_params).first()
    if not email_obj:
        email_obj = EmailAddress.objects.filter(user=user, primary=True).first()
        
    if email_obj:
        if email_obj.verified != instance.is_email_verified:
            email_obj.verified = instance.is_email_verified
            email_obj.save()
            # If we just verified it, make sure we don't accidentally unverify others or get into loop
            # But here we just want 1-to-1 sync for the main email.
