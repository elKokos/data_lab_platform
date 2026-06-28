#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <student_name>" >&2
  exit 1
fi

student_name="$1"

docker compose exec -T postgres psql \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${EDU_PLATFORM_DB:-edu_platform}" \
  -v student_name="$student_name" \
  -f sql/admin/create_sandbox.sql

