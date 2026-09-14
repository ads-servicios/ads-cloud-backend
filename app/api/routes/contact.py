import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.schemas.contact import ContactRequest, ContactSuccessResponse
from app.services.contact_email import EmailDeliveryError, send_contact_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["contact"])


@router.post(
    "/contact",
    response_model=ContactSuccessResponse,
    responses={
        400: {"content": {"application/json": {"example": {"message": "privacy policy must be accepted"}}}},
        500: {"content": {"application/json": {"example": {"message": "something went wrong"}}}},
    },
    summary="Submit contact form",
    description="Send a contact message from the public website by email.",
)
async def submit_contact(payload: ContactRequest):
    if not payload.privacy_policy_acceptance:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "privacy policy must be accepted"},
        )

    try:
        send_contact_email(payload)
    except EmailDeliveryError as exc:
        logger.exception("Contact email delivery failed")
        content: dict[str, str] = {"message": "something went wrong"}
        if settings.is_development and exc.__cause__ is not None:
            content["detail"] = str(exc.__cause__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )
    return ContactSuccessResponse(status="email sent")
