"""
Email delivery via SMTP.

Uses TLS (STARTTLS on port 587) by default, compatible with Gmail, SendGrid SMTP,
Mailgun SMTP, and most other providers.

When pdf_bytes is provided the message structure becomes:
  multipart/mixed
    └── multipart/alternative
          ├── text/plain
          └── text/html
    └── application/pdf  (attachment)

Without a PDF it sends a simpler multipart/alternative message.
"""
import logging
import smtplib
from email.mime.application import MIMEApplication
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
    pdf_bytes: bytes | None = None,
    pdf_filename: str = "newsletter.pdf",
) -> bool:
    """
    Send a newsletter email.  Returns True on success, False on failure.

    If pdf_bytes is supplied the PDF is attached as a downloadable file.
    Both HTML and plain-text body parts are always included.
    """
    if not smtp_username or not smtp_password:
        logger.warning("SMTP credentials not configured — email not sent.")
        return False

    # Build the alternative (text + html) inner part
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_body, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))

    if pdf_bytes:
        # Wrap in mixed so we can attach the PDF alongside the body
        outer = MIMEMultipart("mixed")
        outer["Subject"] = subject
        outer["From"] = f"{from_name} <{from_email}>"
        outer["To"] = f"{to_name} <{to_email}>"
        outer["X-Mailer"] = "MyDailyBrief/1.0"
        outer.attach(alt)

        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment", filename=pdf_filename
        )
        outer.attach(pdf_part)
        msg = outer
    else:
        alt["Subject"] = subject
        alt["From"] = f"{from_name} <{from_email}>"
        alt["To"] = f"{to_name} <{to_email}>"
        alt["X-Mailer"] = "MyDailyBrief/1.0"
        msg = alt

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info("Newsletter sent to %s%s", to_email, " (with PDF)" if pdf_bytes else "")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for %s", smtp_username)
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_email, exc)
    except OSError as exc:
        logger.error("Network error sending to %s: %s", to_email, exc)
    return False
