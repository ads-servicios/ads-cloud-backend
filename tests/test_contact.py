from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.contact_email import send_contact_email
from app.services.email_errors import EmailDeliveryError


client = TestClient(app)

VALID_PAYLOAD = {
    "full_name": "Ana García",
    "email": "ana@example.com",
    "service_type": "vehicles_stock",
    "message": "Me interesa un vehículo del stock.",
    "privacy_policy_acceptance": True,
}


@pytest.fixture(autouse=True)
def mock_send_contact_email():
    with patch("app.api.routes.contact.send_contact_email") as mock:
        yield mock


def test_contact_success_returns_200(mock_send_contact_email):
    response = client.post("/contact", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"status": "email sent"}
    mock_send_contact_email.assert_called_once()


def test_contact_privacy_not_accepted_returns_400(mock_send_contact_email):
    payload = {**VALID_PAYLOAD, "privacy_policy_acceptance": False}
    response = client.post("/contact", json=payload)

    assert response.status_code == 400
    assert response.json() == {"message": "privacy policy must be accepted"}
    mock_send_contact_email.assert_not_called()


def test_contact_missing_required_fields_returns_400(mock_send_contact_email):
    response = client.post(
        "/contact",
        json={
            "full_name": "",
            "email": "not-an-email",
            "service_type": "vehicles_stock",
            "message": "",
            "privacy_policy_acceptance": True,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"message": "all required fields must be completed"}
    mock_send_contact_email.assert_not_called()


def test_contact_email_failure_returns_500(mock_send_contact_email):
    mock_send_contact_email.side_effect = EmailDeliveryError("something went wrong")
    response = client.post("/contact", json=VALID_PAYLOAD)

    assert response.status_code == 500
    assert response.json() == {"message": "something went wrong"}


def test_contact_visible_in_openapi():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/contact" in paths
    assert "post" in paths["/contact"]
