#!/bin/sh
set -eu

: "${PGHOST:=db}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=controle_financeiro}"
: "${PGUSER:=financeiro_app}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_INTERVAL_SECONDS:=86400}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"

while true; do
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  final="$BACKUP_DIR/controle-financeiro-$stamp.dump"
  temp="$final.partial"
  echo "[backup] Iniciando backup em $stamp"
  if pg_dump --format=custom --no-owner --no-acl --file="$temp"; then
    mv "$temp" "$final"
    echo "[backup] Backup concluído: $final"
    find "$BACKUP_DIR" -type f -name 'controle-financeiro-*.dump' -mtime "+$BACKUP_RETENTION_DAYS" -delete
  else
    rm -f "$temp"
    echo "[backup] ERRO: pg_dump falhou; próximo ciclo tentará novamente" >&2
  fi
  sleep "$BACKUP_INTERVAL_SECONDS"
done
