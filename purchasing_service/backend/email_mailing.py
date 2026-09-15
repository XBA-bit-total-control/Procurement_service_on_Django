from django.core.mail import send_mail as django_message


def send_email(
        subject: str,
        recipient: str,
        content: str
) -> None:
    django_message(
        subject=subject,
        message=content,
        from_email=None,
        recipient_list=[recipient],
        fail_silently=False
    )
