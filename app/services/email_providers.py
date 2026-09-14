from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from email import policy
from email.generator import BytesGenerator
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.contact_email_content import OutboundEmail
from app.services.email_errors import EmailDeliveryError, EmailNotConfiguredError

logger = logging.getLogger(__name__)


def assert_email_configured() -> None:
    if settings.email_provider == "ses":
        if not settings.contact_email_from or not settings.contact_email_to:
            raise EmailNotConfiguredError("email not configured")
        return

    if not settings.smtp_user or not settings.smtp_password:
        raise EmailNotConfiguredError("email not configured")


def build_mime_message(email: OutboundEmail) -> MIMEMultipart | MIMEText:
    if email.body_html:
        message = MIMEMultipart("related")
        if email.body_text:
            alternative = MIMEMultipart("alternative")
            alternative.attach(MIMEText(email.body_text, "plain", "utf-8"))
            alternative.attach(MIMEText(email.body_html, "html", "utf-8"))
            message.attach(alternative)
        else:
            message.attach(MIMEText(email.body_html, "html", "utf-8"))

        for image in email.inline_images:
            mime_image = MIMEImage(image.content, _subtype=image.subtype)
            mime_image.add_header("Content-ID", f"<{image.cid}>")
            mime_image.add_header("Content-Disposition", "inline", filename=f"{image.cid}.{image.subtype}")
            message.attach(mime_image)
    else:
        message = MIMEText(email.body_text or "", "plain", "utf-8")

    message["Subject"] = email.subject
    message["From"] = settings.contact_email_from
    message["To"] = email.to
    if email.reply_to:
        message["Reply-To"] = email.reply_to

    return message


def _mime_to_bytes(message: MIMEMultipart | MIMEText) -> bytes:
    buffer = BytesIO()
    generator = BytesGenerator(buffer, policy=policy.SMTP)
    generator.flatten(message)
    return buffer.getvalue()


def send_via_smtp(email: OutboundEmail) -> None:
    message = build_mime_message(email)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(
                settings.contact_email_from,
                [email.to],
                message.as_string(),
            )
    except Exception as exc:
        logger.exception("SMTP delivery failed (%s)", settings.smtp_host)
        raise EmailDeliveryError("something went wrong") from exc


def send_via_ses(email: OutboundEmail) -> None:
    message = build_mime_message(email)
    raw_message = _mime_to_bytes(message)
    client = boto3.client("ses", region_name=settings.aws_region)
    try:
        client.send_raw_email(
            Source=settings.contact_email_from,
            Destinations=[email.to],
            RawMessage={"Data": raw_message},
        )
    except (ClientError, BotoCoreError) as exc:
        logger.exception("SES API delivery failed (%s)", settings.aws_region)
        raise EmailDeliveryError("something went wrong") from exc


def dispatch_email(email: OutboundEmail) -> None:
    assert_email_configured()
    if settings.email_provider == "ses":
        send_via_ses(email)
    else:
        send_via_smtp(email)


def dispatch_contact_email(content, reply_to: str) -> None:
    """Backward-compatible wrapper for plain internal notifications."""
    from app.services.contact_email_content import ContactEmailContent

    if not isinstance(content, ContactEmailContent):
        raise TypeError("content must be ContactEmailContent")

    dispatch_email(
        OutboundEmail(
            to=settings.contact_email_to,
            subject=content.subject,
            body_text=content.body,
            reply_to=reply_to,
        )
    )
