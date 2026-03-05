#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1}"
COOKIE_JAR="/tmp/flask-auth-cookie.txt"

echo "[1/3] Test login valide"
curl -sS -c "$COOKIE_JAR" -X POST "$BASE_URL/login" \
  -d "username=admin&password=admin123" >/dev/null

PRIVATE_BODY="$(curl -sS -b "$COOKIE_JAR" "$BASE_URL/private")"
if [[ "$PRIVATE_BODY" == *"Acces au contenu prive autorise"* ]]; then
  echo "OK: acces /private autorise apres login"
else
  echo "ERREUR: acces /private non autorise"
  exit 1
fi

echo "[2/3] Test login invalide"
STATUS_CODE="$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/login" \
  -d "username=admin&password=bad")"
if [[ "$STATUS_CODE" == "401" ]]; then
  echo "OK: echec login retourne HTTP 401"
else
  echo "ERREUR: code HTTP inattendu: $STATUS_CODE"
  exit 1
fi

echo "[3/3] Simulation tentative brute force (5 echecs)"
for _ in {1..5}; do
  curl -sS -o /dev/null -X POST "$BASE_URL/login" -d "username=admin&password=wrong"
done
echo "Termine. Verifier ensuite fail2ban: sudo fail2ban-client status flask-login"
