from unittest.mock import patch

import pytest

from app.core.config import settings
from app.schemas.contact import ContactRequest
from app.services.contact_confirmation_template import build_confirmation_html
from app.services.contact_email import (
    build_confirmation_email,
    build_internal_notification,
    send_contact_email,
)
from app.services.email_errors import EmailDeliveryError

PAYLOAD = ContactRequest(
    full_name="Ana García",
    email="ana@example.com",
    service_type="vehicles_stock",
    message="Me interesa un vehículo.",
    privacy_policy_acceptance=True,
)


def test_build_confirmation_html_includes_required_copy():
    html, images = build_confirmation_html("Ana García")

    assert "Confirmación de Contacto" in html
    assert "Estimado/a" in html
    assert "Ana García" in html
    assert "Hemos recibido su solicitud correctamente" in html
    assert "asesor especializado" in html
    assert "soluciones automotrices profesionales" in html
    assert "Visitar nuestro sitio web" in html
    assert "Esto es un correo no monitorizado, por favor no responder" in html
    assert html.index("Esto es un correo no monitorizado") < html.index("Saludos cordiales")
    assert "El equipo de ADS Inversiones" in html
    assert "Servicios Integrales" in html
    assert settings.contact_footer_email in html
    assert settings.contact_footer_website.rstrip("/") in html
    assert settings.contact_public_website_url.rstrip("/") in html
    assert len(images) == 1
    assert images[0].cid == "ads-logo"


def test_build_confirmation_email_uses_visitor_address():
    email = build_confirmation_email(PAYLOAD)

    assert email.to == "ana@example.com"
    assert email.subject == settings.contact_confirmation_subject
    assert email.body_html is not None
    assert email.reply_to is None


def test_build_internal_notification_uses_business_inbox():
    email = build_internal_notification(PAYLOAD)

    assert email.to == settings.contact_email_to
    assert email.body_text is not None
    assert email.reply_to == "ana@example.com"


@patch("app.services.contact_email.dispatch_email")
def test_send_contact_email_dispatches_twice(mock_dispatch):
    send_contact_email(PAYLOAD)

    assert mock_dispatch.call_count == 2
    internal = mock_dispatch.call_args_list[0].args[0]
    confirmation = mock_dispatch.call_args_list[1].args[0]
    assert internal.to == settings.contact_email_to
    assert confirmation.to == "ana@example.com"


@patch("app.services.contact_email.dispatch_email")
def test_send_contact_email_propagates_failure_on_first_send(mock_dispatch):
    mock_dispatch.side_effect = EmailDeliveryError("something went wrong")

    with pytest.raises(EmailDeliveryError):
        send_contact_email(PAYLOAD)

    mock_dispatch.assert_called_once()


@patch("app.services.contact_email.dispatch_email")
def test_send_contact_email_propagates_failure_on_confirmation(mock_dispatch):
    mock_dispatch.side_effect = [None, EmailDeliveryError("something went wrong")]

    with pytest.raises(EmailDeliveryError):
        send_contact_email(PAYLOAD)

    assert mock_dispatch.call_count == 2
