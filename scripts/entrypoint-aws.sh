#!/usr/bin/env sh
# Load contact email secrets from AWS SSM before starting the API.
# Usage: ./scripts/entrypoint-aws.sh uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# Secrets live at /ads/shared/contact/* (same SMTP config for pre/pro/local-on-aws).

set -e

REGION="${AWS_REGION:-eu-north-1}"
PREFIX="/ads/shared/contact"

load_param() {
  name="$1"
  var="$2"
  value="$(aws ssm get-parameter --name "${PREFIX}/${name}" --with-decryption --region "${REGION}" --query Parameter.Value --output text 2>/dev/null || true)"
  if [ -n "$value" ] && [ "$value" != "None" ]; then
    export "$var=$value"
  fi
}

load_param "smtp-host" SMTP_HOST
load_param "smtp-user" SMTP_USER
load_param "smtp-password" SMTP_PASSWORD
load_param "contact-email-from" CONTACT_EMAIL_FROM
load_param "contact-email-to" CONTACT_EMAIL_TO

export EMAIL_PROVIDER="${EMAIL_PROVIDER:-smtp}"
export SMTP_PORT="${SMTP_PORT:-587}"
export SMTP_USE_TLS="${SMTP_USE_TLS:-true}"

exec "$@"
