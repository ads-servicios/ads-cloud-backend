import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.contact import router as contact_router
from app.api.routes.health import router as health_router
from app.api.routes.roles import router as roles_router
from app.api.routes.users import router as users_router
from app.api.routes.web_vehicles import router as web_vehicles_router
from app.core.config import settings
from app.services.bootstrap import bootstrap_admin_if_needed

logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
    force=True,
)

openapi_tags = [
    {
        "name": "health",
        "description": "Service health and liveness endpoints.",
    },
    {
        "name": "contact",
        "description": "Public contact form submissions.",
    },
    {
        "name": "auth",
        "description": "Authentication (login) and current user profile.",
    },
    {
        "name": "users",
        "description": "User CRUD with role-based access control.",
    },
    {
        "name": "roles",
        "description": "Role and scope/action permission management.",
    },
    {
        "name": "web_vehicles",
        "description": "Public web vehicle listing plus protected backoffice CRUD.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await bootstrap_admin_if_needed()
    yield


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.resolved_docs_url,
    redoc_url=settings.resolved_redoc_url,
    openapi_url=settings.resolved_openapi_url,
    openapi_tags=openapi_tags,
    swagger_ui_parameters={"displayRequestDuration": True},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"message": "all required fields must be completed"},
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=openapi_tags,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

app.include_router(health_router)
app.include_router(contact_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(web_vehicles_router)
