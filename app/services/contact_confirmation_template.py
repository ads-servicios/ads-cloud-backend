from html import escape
from pathlib import Path

from app.core.config import settings
from app.services.contact_email_content import InlineImage

LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "email" / "ads-logo.png"
LOGO_CID = "ads-logo"

# ADS Precision Core (Stitch design system)
COLOR_PRIMARY = "#162839"
COLOR_PRIMARY_CONTAINER = "#2c3e50"
COLOR_SECONDARY = "#006d37"
COLOR_ON_PRIMARY = "#ffffff"
COLOR_ON_PRIMARY_CONTAINER = "#96a9be"
COLOR_PRIMARY_FIXED_DIM = "#b5c8df"
COLOR_SURFACE = "#f9f9fa"
COLOR_SURFACE_CONTAINER = "#eeeeef"
COLOR_SURFACE_VARIANT = "#e2e2e3"
COLOR_ON_SURFACE = "#1a1c1d"
COLOR_ON_SURFACE_VARIANT = "#43474c"
COLOR_OUTLINE_VARIANT = "#c4c6cd"


def load_logo_image() -> InlineImage:
    return InlineImage(cid=LOGO_CID, content=LOGO_PATH.read_bytes(), subtype="png")


def build_confirmation_html(full_name: str) -> tuple[str, list[InlineImage]]:
    safe_name = escape(full_name)
    website_url = escape(settings.contact_public_website_url.rstrip("/"))
    footer_email = escape(settings.contact_footer_email)
    footer_website = escape(settings.contact_footer_website.rstrip("/"))
    display_website = footer_website.replace("https://", "").replace("http://", "")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confirmación de Contacto - ADS</title>
</head>
<body style="margin:0;padding:0;background-color:{COLOR_SURFACE};font-family:'Work Sans',Arial,Helvetica,sans-serif;color:{COLOR_ON_SURFACE};">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:{COLOR_SURFACE};padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background-color:{COLOR_SURFACE};border:1px solid {COLOR_OUTLINE_VARIANT};border-radius:8px;overflow:hidden;">
          <tr>
            <td style="background-color:{COLOR_PRIMARY_CONTAINER};padding:32px 24px;text-align:center;border-bottom:4px solid {COLOR_SECONDARY};">
              <table role="presentation" cellspacing="0" cellpadding="0" align="center" style="margin:0 auto 16px;">
                <tr>
                  <td style="width:96px;height:96px;background-color:{COLOR_SURFACE};border-radius:50%;text-align:center;vertical-align:middle;padding:8px;">
                    <img src="cid:{LOGO_CID}" alt="ADS - Servicios Integrales" width="80" height="80" style="display:block;margin:0 auto;border:0;border-radius:50%;">
                  </td>
                </tr>
              </table>
              <p style="margin:0;font-family:Montserrat,Arial,Helvetica,sans-serif;font-size:32px;line-height:40px;font-weight:700;color:{COLOR_ON_PRIMARY};">ADS Inversiones</p>
              <p style="margin:8px 0 0;font-family:'Work Sans',Arial,Helvetica,sans-serif;font-size:12px;line-height:16px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:{COLOR_PRIMARY_FIXED_DIM};">Servicios Integrales</p>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px 24px;">
              <p style="margin:0 0 24px;font-family:Montserrat,Arial,Helvetica,sans-serif;font-size:20px;line-height:28px;font-weight:600;color:{COLOR_PRIMARY};">Confirmación de Contacto</p>
              <p style="margin:0 0 16px;font-size:18px;line-height:28px;color:{COLOR_ON_SURFACE_VARIANT};">Estimado/a <strong style="color:{COLOR_PRIMARY};">{safe_name}</strong>,</p>
              <p style="margin:0 0 16px;font-size:18px;line-height:28px;color:{COLOR_ON_SURFACE_VARIANT};">
                Gracias por ponerse en contacto con nosotros. Hemos recibido su solicitud correctamente
                y nuestro equipo está revisando los detalles.
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0;background-color:{COLOR_SURFACE_CONTAINER};border-left:4px solid {COLOR_SECONDARY};border-radius:0 8px 8px 0;">
                <tr>
                  <td style="padding:20px 24px;font-size:16px;line-height:24px;font-weight:500;color:{COLOR_PRIMARY};">
                    En breve un asesor especializado se pondrá en contacto con usted para brindarle
                    la atención personalizada que caracteriza a nuestros servicios.
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 24px;font-size:18px;line-height:28px;color:{COLOR_ON_SURFACE_VARIANT};">
                Apreciamos su interés en nuestras soluciones automotrices profesionales.
              </p>
              <p style="margin:0 0 16px;font-size:14px;line-height:22px;color:{COLOR_ON_SURFACE_VARIANT};">
                Esto es un correo no monitorizado, por favor no responder
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:24px;padding-top:24px;border-top:1px solid {COLOR_SURFACE_VARIANT};">
                <tr>
                  <td>
                    <p style="margin:0;font-size:16px;font-weight:600;color:{COLOR_PRIMARY};">Saludos cordiales,</p>
                    <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{COLOR_SECONDARY};">El equipo de ADS Inversiones</p>
                  </td>
                </tr>
              </table>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:32px;">
                <tr>
                  <td align="center">
                    <a href="{website_url}" style="display:inline-block;background-color:{COLOR_SECONDARY};color:{COLOR_ON_PRIMARY};text-decoration:none;padding:12px 32px;border-radius:4px;font-size:16px;font-weight:500;font-family:'Work Sans',Arial,Helvetica,sans-serif;">
                      Visitar nuestro sitio web
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background-color:{COLOR_PRIMARY};padding:32px 24px;color:{COLOR_ON_PRIMARY};border-top:1px solid {COLOR_PRIMARY_CONTAINER};">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="vertical-align:top;padding-bottom:16px;">
                    <p style="margin:0 0 8px;font-family:Montserrat,Arial,Helvetica,sans-serif;font-size:20px;line-height:28px;font-weight:600;">ADS - Servicios Integrales</p>
                    <p style="margin:0;font-size:16px;line-height:24px;color:{COLOR_ON_PRIMARY_CONTAINER};">Professional Automotive Solutions.</p>
                  </td>
                  <td style="vertical-align:top;text-align:right;">
                    <p style="margin:0 0 8px;font-size:16px;line-height:24px;color:{COLOR_ON_PRIMARY_CONTAINER};">
                      <a href="{footer_website}" style="color:{COLOR_ON_PRIMARY_CONTAINER};text-decoration:none;">{display_website}</a>
                    </p>
                    <p style="margin:0;font-size:16px;line-height:24px;color:{COLOR_ON_PRIMARY_CONTAINER};">
                      <a href="mailto:{footer_email}" style="color:{COLOR_ON_PRIMARY_CONTAINER};text-decoration:none;">{footer_email}</a>
                    </p>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 0;padding-top:16px;border-top:1px solid {COLOR_PRIMARY_CONTAINER};text-align:center;font-size:12px;line-height:16px;letter-spacing:0.05em;color:{COLOR_ON_PRIMARY_CONTAINER};">
                © ADS - Servicios Integrales. Todos los derechos reservados.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return html, [load_logo_image()]
