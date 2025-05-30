from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Test email functionality'

    def handle(self, *args, **kwargs):
        # Test email settings
        subject = 'Test Email from Django'
        message = 'This is a test email to confirm that email notifications are working.'
        from_email = settings.EMAIL_HOST_USER  # Sender's email (from settings)
        recipient_list = ['test@example.com']  # Replace with your email address for testing

        try:
            # Send the test email
            send_mail(subject, message, from_email, recipient_list)
            self.stdout.write(self.style.SUCCESS('Test email sent successfully!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error sending test email: {e}'))
