#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <student_name> <student_password> [with_sandbox=true|false]" >&2
  exit 1
fi

student_name="$1"
student_password="$2"
with_sandbox="${3:-true}"

docker compose exec -T postgres psql \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${EDU_PLATFORM_DB:-edu_platform}" \
  -v student_name="$student_name" \
  -v student_password="$student_password" \
  -v with_sandbox="$with_sandbox" \
  -f sql/admin/create_student.sql

