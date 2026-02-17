from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from utils.emails import send_order_placed_email, send_order_status_update_email, send_feedback_request_email

@receiver(pre_save, sender=Order)
def track_status_change(sender, instance, **kwargs):
    """
    Track the old status before saving.
    """
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status_id = old_order.order_status_id
        except Order.DoesNotExist:
            instance._old_status_id = None
    else:
        instance._old_status_id = None

@receiver(post_save, sender=Order)
def trigger_order_emails(sender, instance, created, **kwargs):
    """
    Signal to send emails when an order is created or its status is updated.
    """
    if created:
        # 🔥 For new orders, use on_commit to ensure items are created first
        from django.db import transaction

        def send_placed_email():
            # Refresh from DB to get the latest items and total_amount
            instance.refresh_from_db()
            try:
                send_order_placed_email(instance)
            except Exception as e:
                print(f"Error sending order placed email for #{instance.id}: {e}")

        transaction.on_commit(send_placed_email)
    else:
        # Detect status change
        old_status_id = getattr(instance, '_old_status_id', None)
        if old_status_id and old_status_id != instance.order_status_id:
            try:
                send_order_status_update_email(instance)
                
                # If newly delivered, also send feedback request
                if instance.order_status and instance.order_status.status_code == 'delivered':
                    send_feedback_request_email(instance)
            except Exception as e:
                print(f"Error sending update/feedback email for #{instance.id}: {e}")
