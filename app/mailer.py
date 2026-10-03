import os
import smtplib
from email.message import EmailMessage


class Mailer:
    def send(self, recipient: str, subject: str, body: str) -> None:
        host = os.environ.get("SMTP_HOST")

        if not host:
            print(f"[mail not configured] To: {recipient}\nSubject: {subject}\n\n{body}\n")
            return

        message = EmailMessage()
        message["From"] = os.environ.get("SMTP_FROM", "no-reply@arquila.local")
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as server:
            server.starttls()

            user = os.environ.get("SMTP_USER")

            if user:
                server.login(user, os.environ.get("SMTP_PASSWORD", ""))

            server.send_message(message)


def get_mailer() -> Mailer:
    return Mailer()
