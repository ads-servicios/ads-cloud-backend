from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.contact_email_content import InlineImage, OutboundEmail
from app.services.email_errors import EmailNotConfiguredError
from app.services.email_providers import assert_email_configured, build_mime_message, dispatch_email


PLAIN_EMAIL = OutboundEmail(
    to="to@example.com",
    subject="Test",
    body_text="Body",
    reply_to="reply@example.com",
)

HTML_EMAIL = OutboundEmail(
    to="visitor@example.com",
    subject="HTML Test",
    body_html="<p>Hello <img src='cid:ads-logo'></p>",
    inline_images=(InlineImage(cid="ads-logo", content=b"png-bytes", subtype="png"),),
)


def test_assert_email_configured_smtp_missing_password():
    with patch.object(settings, "email_provider", "smtp"), patch.object(
        settings, "smtp_user", "user"
    ), patch.object(settings, "smtp_password", ""):
        with pytest.raises(EmailNotConfiguredError):
            assert_email_configured()


def test_build_mime_message_plain():
    message = build_mime_message(PLAIN_EMAIL)

    assert isinstance(message, MIMEText)
    assert message.get_content_type() == "text/plain"
    assert message["To"] == "to@example.com"
    assert message["Reply-To"] == "reply@example.com"


def test_build_mime_message_html_with_inline_image():
    message = build_mime_message(HTML_EMAIL)

    assert isinstance(message, MIMEMultipart)
    assert message.get_content_subtype() == "related"
    parts = list(message.walk())
    assert any(part.get_content_type() == "text/html" for part in parts)
    assert any(part.get_content_type() == "image/png" for part in parts)


def test_dispatch_email_uses_ses():
    with patch.object(settings, "email_provider", "ses"), patch.object(
        settings, "contact_email_from", "from@example.com"
    ), patch.object(settings, "contact_email_to", "to@example.com"), patch(
        "app.services.email_providers.send_via_ses"
    ) as send_ses:
        dispatch_email(PLAIN_EMAIL)
        send_ses.assert_called_once_with(PLAIN_EMAIL)


def test_dispatch_email_uses_smtp():
    with patch.object(settings, "email_provider", "smtp"), patch.object(
        settings, "smtp_user", "user"
    ), patch.object(settings, "smtp_password", "secret"), patch(
        "app.services.email_providers.send_via_smtp"
    ) as send_smtp:
        dispatch_email(PLAIN_EMAIL)
        send_smtp.assert_called_once_with(PLAIN_EMAIL)


def test_send_via_smtp_calls_sendmail_with_recipient():
    smtp_server = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__ = MagicMock(return_value=smtp_server)
    smtp_context.__exit__ = MagicMock(return_value=False)
    with patch.object(settings, "smtp_host", "smtp.example.com"), patch.object(
        settings, "smtp_port", 587
    ), patch.object(settings, "smtp_use_tls", True), patch.object(
        settings, "smtp_user", "user"
    ), patch.object(settings, "smtp_password", "secret"), patch.object(
        settings, "contact_email_from", "from@example.com"
    ), patch("app.services.email_providers.smtplib.SMTP", return_value=smtp_context):
        from app.services.email_providers import send_via_smtp

        send_via_smtp(PLAIN_EMAIL)

        smtp_server.sendmail.assert_called_once()
        recipients = smtp_server.sendmail.call_args.args[1]
        assert recipients == ["to@example.com"]


def test_send_via_ses_calls_send_raw_email():
    ses_client = MagicMock()
    with patch.object(settings, "aws_region", "eu-north-1"), patch.object(
        settings, "contact_email_from", "from@example.com"
    ), patch("app.services.email_providers.boto3.client", return_value=ses_client) as boto_client:
        from app.services.email_providers import send_via_ses

        send_via_ses(PLAIN_EMAIL)

        boto_client.assert_called_once_with("ses", region_name="eu-north-1")
        ses_client.send_raw_email.assert_called_once()
        kwargs = ses_client.send_raw_email.call_args.kwargs
        assert kwargs["Destinations"] == ["to@example.com"]
