#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Uso: ./scripts/restore-backup.sh ./backups/arquivo.dump" >&2
  exit 2
fi

backup="$1"
if [ ! -f "$backup" ]; then
  echo "Arquivo de backup não encontrado: $backup" >&2
  exit 2
fi

echo "ATENÇÃO: a restauração substitui objetos existentes no banco."
printf "Digite RESTAURAR para confirmar: "
read confirmation
if [ "$confirmation" != "RESTAURAR" ]; then
  echo "Operação cancelada."
  exit 1
fi

cat "$backup" | docker compose exec -T db sh -c \
  'pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" -'
echo "Restauração concluída. Reinicie a API se necessário: docker compose restart api"
