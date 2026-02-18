"""
Email delivery via SMTP.

Uses TLS (STARTTLS on port 587) by default, compatible with Gmail, SendGrid SMTP,
Mailgun SMTP, and most other providers.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_newsletter(
    *,
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    plain_body: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    from_email: str,
    from_name: str,
) -> bool:
    """
    Send a newsletter email.  Returns True on success, False on failure.
    Both HTML and plain-text parts are attached (multipart/alternative).
    """
    if not smtp_username or not smtp_password:
        logger.warning("SMTP credentials not configured — email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg["X-Mailer"] = "MyDailyBrief/1.0"

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("Newsletter sent to %s", to_email)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", smtp_username)
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_email, exc)
    except OSError as exc:
        logger.error("Network error sending to %s: %s", to_email, exc)
    return False
