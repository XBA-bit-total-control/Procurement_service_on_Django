from celery import shared_task
from django.core.mail import send_mail as django_message


@shared_task
def send_email(
        subject: str,
        recipient: str,
        content: str
) -> bool:
    django_message(
        subject=subject,
        message=content,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False
    )
    return True
