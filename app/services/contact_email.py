from app.core.config import settings
from app.schemas.contact import ContactRequest, ServiceType
from app.services.contact_confirmation_template import build_confirmation_html
from app.services.contact_email_content import ContactEmailContent, OutboundEmail
from app.services.email_errors import EmailDeliveryError
from app.services.email_providers import dispatch_email

__all__ = ["EmailDeliveryError", "ContactEmailContent", "build_contact_email", "send_contact_email"]


def _service_label(service_type: ServiceType) -> str:
    labels = {
        ServiceType.vehicles_stock: "Vehículos en stock",
        ServiceType.mechanics_workshop: "Taller mecánico",
        ServiceType.auction: "Subastas",
        ServiceType.other: "Otro",
    }
    return labels[service_type]


def build_contact_email(payload: ContactRequest) -> ContactEmailContent:
    service = _service_label(payload.service_type)
    body = (
        f"Nuevo mensaje de contacto desde la web\n\n"
        f"Nombre: {payload.full_name}\n"
        f"Email: {payload.email}\n"
        f"Servicio: {service}\n\n"
        f"Mensaje:\n{payload.message}\n"
    )
    return ContactEmailContent(subject="Contacto web ADS", body=body)


def build_internal_notification(payload: ContactRequest) -> OutboundEmail:
    content = build_contact_email(payload)
    return OutboundEmail(
        to=settings.contact_email_to,
        subject=content.subject,
        body_text=content.body,
        reply_to=payload.email,
    )


def build_confirmation_email(payload: ContactRequest) -> OutboundEmail:
    html, images = build_confirmation_html(payload.full_name)
    return OutboundEmail(
        to=str(payload.email),
        subject=settings.contact_confirmation_subject,
        body_html=html,
        inline_images=tuple(images),
    )


def send_contact_email(payload: ContactRequest) -> None:
    if not payload.privacy_policy_acceptance:
        raise ValueError("privacy policy must be accepted")

    dispatch_email(build_internal_notification(payload))
    dispatch_email(build_confirmation_email(payload))
