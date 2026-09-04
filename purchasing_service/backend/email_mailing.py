import smtplib
from email.message import EmailMessage

from purchasing_service.settings import (
    EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
    EMAIL_HOST, EMAIL_PORT
)


def send_email(
        subject: str,
        recipient: str,
        content: str
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL_HOST_USER
    message["To"] = recipient
    message.set_content(content)

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

    server.send_message(message)
    server.quit()
