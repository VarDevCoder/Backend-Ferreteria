#!/bin/sh
# Paso de "build" de Vercel (vercel.json → buildCommand).
#
# En simple: si el proyecto de Vercel es una instancia de cliente con
# servidor único (variable FRONTEND_DIR, por ejemplo "frontend"), baja las
# pantallas del repo del frontend para que el mismo despliegue las sirva.
# Sin FRONTEND_DIR (como la demo ankor-backend) no hace nada: solo API.
#
# Variables (Vercel → Settings → Environment Variables):
#   FRONTEND_DIR    carpeta relativa donde dejar el frontend (ej: frontend).
#   FRONTEND_TOKEN  token de GitHub de SOLO LECTURA del repo del frontend.
#                   Hace falta mientras Frontend-Ferreteria sea privado.
#   FRONTEND_REF    rama, tag o commit del frontend (por defecto: main).
#   FRONTEND_REPO   dueño/repo (por defecto: VarDevCoder/Frontend-Ferreteria).
set -eu

if [ -z "${FRONTEND_DIR:-}" ]; then
  echo "SAIL: sin FRONTEND_DIR, despliegue solo de API (el frontend está en otro lado)."
  exit 0
fi
case "$FRONTEND_DIR" in
  /*|*..*) echo "SAIL: FRONTEND_DIR tiene que ser una carpeta relativa al repo (ej: frontend)"; exit 1 ;;
esac

REPO="${FRONTEND_REPO:-VarDevCoder/Frontend-Ferreteria}"
REF="${FRONTEND_REF:-main}"
URL="https://api.github.com/repos/$REPO/tarball/$REF"
TMP="$(mktemp)"

echo "SAIL: bajando el frontend $REPO@$REF a $FRONTEND_DIR/"
if [ -n "${FRONTEND_TOKEN:-}" ]; then
  curl -fsSL -H "Authorization: Bearer $FRONTEND_TOKEN" -H "Accept: application/vnd.github+json" "$URL" -o "$TMP" || {
    echo "SAIL: no se pudo bajar el frontend con FRONTEND_TOKEN (¿venció el token o no tiene acceso a $REPO?)"; exit 1; }
else
  curl -fsSL -H "Accept: application/vnd.github+json" "$URL" -o "$TMP" || {
    echo "SAIL: no se pudo bajar el frontend. Si el repo $REPO es privado, definí FRONTEND_TOKEN"; exit 1; }
fi

rm -rf "$FRONTEND_DIR"
mkdir -p "$FRONTEND_DIR"
tar -xzf "$TMP" -C "$FRONTEND_DIR" --strip-components=1
rm -f "$TMP"
# Herramientas de desarrollo: no se publican.
rm -rf "$FRONTEND_DIR/.github" "$FRONTEND_DIR/herramientas"
test -f "$FRONTEND_DIR/index.html" || { echo "SAIL: el frontend bajado no tiene index.html"; exit 1; }
echo "SAIL: frontend listo ($(find "$FRONTEND_DIR" -type f | wc -l) archivos)."
