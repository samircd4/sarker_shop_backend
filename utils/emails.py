from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import os

def send_order_email(order, template_name, subject):
    """
    Base function to send order related emails.
    """
    recipient_email = order.email or (order.customer.user.email if order.customer and order.customer.user else None)
    if not recipient_email:
        print(f"No email found for order {order.id}")
        return

    # Determine frontend URL from settings (set via FRONTEND_URL in .env)
    frontend_url = settings.FRONTEND_URL

    context = {
        'order': order,
        'full_name': order.full_name or (order.customer.name if order.customer else 'Valued Customer'),
        'items': order.items.all(),
        'total_amount': order.total_amount,
        'tracking_url': f"{frontend_url}/order-tracking/{order.id}",
        'feedback_url': f"{frontend_url}/reviews/{order.id}", # Link to reviews page
        'frontend_url': frontend_url
    }

    html_content = render_to_string(f'emails/{template_name}', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Optional: Attach logo if needed for the template's cid
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        from email.mime.image import MIMEImage
        with open(logo_path, 'rb') as f:
            logo_data = f.read()
        logo = MIMEImage(logo_data)
        logo.add_header('Content-ID', '<logo_image>')
        email.attach(logo)

    # 🔥 Attach Invoice PDF
    try:
        from utils.pdf import generate_invoice_pdf
        pdf_content = generate_invoice_pdf(order)
        if pdf_content:
            email.attach(f"invoice_{order.id}.pdf", pdf_content, "application/pdf")
    except Exception as e:
        print(f"Error attaching invoice PDF: {e}")

    try:
        email.send()
        print(f"Email sent successfully for order {order.id} with subject: {subject}")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_order_placed_email(order):
    subject = f"Order Placed Successfully - #{order.id} | Sarker Shop"
    send_order_email(order, 'order_placed_email.html', subject)

def send_order_status_update_email(order):
    status_name = order.order_status.display_name if order.order_status else "Updated"
    subject = f"Order #{order.id} Status Update: {status_name} | Sarker Shop"
    send_order_email(order, 'order_status_update_email.html', subject)

def send_feedback_request_email(order):
    subject = f"We'd love your feedback! Order #{order.id} | Sarker Shop"
    send_order_email(order, 'order_feedback_email.html', subject)
