# email_utils.py

from django.core.mail import send_mail
from django.conf import settings

# email_utils.py is a generic utility module. Its job is to send an email to whatever address it's given
def send_notification_email(subject, message, recipient_list):
    """
    Sends a plain text email notification.

    :param subject: Email subject line
    :param message: Main content of the email
    :param recipient_list: List of recipient email addresses
    """
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        print(f"📧 Email sent to: {', '.join(recipient_list)}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
