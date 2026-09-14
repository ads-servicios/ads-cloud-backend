from unittest.mock import patch
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.schemas.auth import UserCreate
from app.services.role_seed import ensure_system_roles
from app.services.users import create_user


@pytest_asyncio.fixture
async def web_vehicles_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await ensure_system_roles(session)
        await create_user(
            session,
            UserCreate(email="admin@example.com", password="adminpass1", role="administrator"),
        )
        await create_user(
            session,
            UserCreate(email="common@example.com", password="commonpass1", role="common"),
        )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


async def _login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _payload(**overrides):
    payload = {
        "title": "Peugeot Bipper",
        "description": "<div><p>Disponible proximamente.</p></div>",
        "slug": "peugeot-bipper-2009",
        "brand": "Peugeot",
        "model": "Bipper",
        "year": 2009,
        "odometer": 192736,
        "price": 4990.0,
        "currency": "EUR",
        "saleStatus": "available",
        "motorType": "1.4 HDI de 68 CV",
        "driveType": "manual",
        "fuelType": "diesel",
        "firstRegistrationDate": "2009-04-01",
        "images": ["images/stock/18/frontal_copiloto.jpg"],
        "rebu": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_list_web_vehicles_is_public_and_empty(web_vehicles_client: AsyncClient):
    response = await web_vehicles_client.get("/web_vehicles")
    assert response.status_code == 200
    assert response.json() == {"vehicles": []}


@pytest.mark.asyncio
async def test_create_requires_authentication(web_vehicles_client: AsyncClient):
    response = await web_vehicles_client.post("/web_vehicles", json=_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_common_user_cannot_mutate_web_vehicles(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "common@example.com", "commonpass1")
    headers = {"Authorization": f"Bearer {token}"}

    response = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_list_get_patch_put_and_delete_web_vehicle(
    web_vehicles_client: AsyncClient,
):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    created = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["_id"] == "stock-peugeot-bipper-2009"
    assert body["uid"] == 1
    assert body["saleStatus"] == "available"
    assert body["images"] == ["images/stock/18/frontal_copiloto.jpg"]
    assert len(body["imageUrls"]) == 1
    assert "images/stock/18/frontal_copiloto.jpg" in body["imageUrls"][0]
    UUID(body["uuid"])

    listed = await web_vehicles_client.get("/web_vehicles")
    assert listed.status_code == 200
    assert len(listed.json()["vehicles"]) == 1

    fetched = await web_vehicles_client.get(f"/web_vehicles/{body['uuid']}")
    assert fetched.status_code == 200
    assert fetched.json()["slug"] == "peugeot-bipper-2009"

    patched = await web_vehicles_client.patch(
        f"/web_vehicles/{body['uuid']}",
        headers=headers,
        json={"price": 4500.0, "saleStatus": "sold"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["price"] == 4500.0
    assert patched.json()["saleStatus"] == "sold"

    replaced = await web_vehicles_client.put(
        f"/web_vehicles/{body['uuid']}",
        headers=headers,
        json=_payload(title="Peugeot Bipper Restyled", price=4300.0, saleStatus="available"),
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["title"] == "Peugeot Bipper Restyled"
    assert replaced.json()["price"] == 4300.0

    deleted = await web_vehicles_client.delete(f"/web_vehicles/{body['uuid']}", headers=headers)
    assert deleted.status_code == 204

    listed_after = await web_vehicles_client.get("/web_vehicles")
    assert listed_after.status_code == 200
    assert listed_after.json() == {"vehicles": []}


@pytest.mark.asyncio
async def test_list_uses_public_media_base_for_image_urls(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}
    created = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert created.status_code == 201, created.text

    with patch(
        "app.services.web_vehicle_media.settings.web_vehicles_public_media_base_url",
        "https://cdn.example.test",
    ), patch(
        "app.services.web_vehicle_media.settings.web_vehicles_s3_bucket",
        "",
    ):
        listed = await web_vehicles_client.get("/web_vehicles")

    assert listed.status_code == 200
    vehicle = listed.json()["vehicles"][0]
    assert vehicle["images"] == ["images/stock/18/frontal_copiloto.jpg"]
    assert vehicle["imageUrls"] == ["https://cdn.example.test/images/stock/18/frontal_copiloto.jpg"]


@pytest.mark.asyncio
async def test_get_unknown_web_vehicle_returns_404(web_vehicles_client: AsyncClient):
    response = await web_vehicles_client.get("/web_vehicles/0d0a7ba4-62d5-41df-83c4-8299d5c8e2fa")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_slug_returns_409(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    first = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert first.status_code == 201, first.text

    duplicate = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_invalid_year_returns_400(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}

    response = await web_vehicles_client.post(
        "/web_vehicles",
        headers=headers,
        json=_payload(year=99),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_uploads_base64_images_to_s3(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}
    # 1x1 PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    with (
        patch("app.services.web_vehicle_media.settings.web_vehicles_s3_bucket", "ads-test-web"),
        patch("app.services.web_vehicle_media.boto3.client") as boto_client,
    ):
        s3 = boto_client.return_value
        s3.generate_presigned_url.side_effect = (
            lambda ClientMethod, Params, ExpiresIn=3600: f"https://signed.example/{Params['Key']}"
        )
        created = await web_vehicles_client.post(
            "/web_vehicles",
            headers=headers,
            json=_payload(
                slug="peugeot-bipper-upload",
                images=[
                    {
                        "filename": "frontal.png",
                        "contentType": "image/png",
                        "data": png_b64,
                    }
                ],
            ),
        )

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["images"] == [f"images/stock/{body['uid']}/frontal-1.png"]
    s3.put_object.assert_called_once()
    call_kwargs = s3.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == "ads-test-web"
    assert call_kwargs["Key"] == f"images/stock/{body['uid']}/frontal-1.png"
    assert call_kwargs["ContentType"] == "image/png"


@pytest.mark.asyncio
async def test_patch_uploads_images_to_s3(web_vehicles_client: AsyncClient):
    token = await _login(web_vehicles_client, "admin@example.com", "adminpass1")
    headers = {"Authorization": f"Bearer {token}"}
    created = await web_vehicles_client.post("/web_vehicles", headers=headers, json=_payload())
    assert created.status_code == 201, created.text
    vehicle_uuid = created.json()["uuid"]
    uid = created.json()["uid"]
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    with (
        patch("app.services.web_vehicle_media.settings.web_vehicles_s3_bucket", "ads-test-web"),
        patch("app.services.web_vehicle_media.boto3.client") as boto_client,
    ):
        s3 = boto_client.return_value
        s3.generate_presigned_url.side_effect = (
            lambda ClientMethod, Params, ExpiresIn=3600: f"https://signed.example/{Params['Key']}"
        )
        patched = await web_vehicles_client.patch(
            f"/web_vehicles/{vehicle_uuid}",
            headers=headers,
            json={
                "images": [
                    "images/stock/18/frontal_copiloto.jpg",
                    {
                        "filename": "extra.png",
                        "contentType": "image/png",
                        "data": png_b64,
                    },
                ]
            },
        )

    assert patched.status_code == 200, patched.text
    assert patched.json()["images"] == [
        "images/stock/18/frontal_copiloto.jpg",
        f"images/stock/{uid}/extra-1.png",
    ]
    s3.put_object.assert_called_once()
