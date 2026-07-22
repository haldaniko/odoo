#!/usr/bin/env bash
set -e

wait_for_postgres() {
    if [ -z "${DB_HOST:-}" ]; then
        return
    fi

    echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."
    until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "${DB_USER:-odoo}" >/dev/null 2>&1; do
        sleep 1
    done
}

if [ "$#" -eq 0 ] || [ "$1" = "odoo" ] || [ "${1#-}" != "$1" ]; then
    if [ "$#" -gt 0 ] && [ "$1" = "odoo" ]; then
        shift
    fi

    wait_for_postgres

    set -- python /opt/odoo/odoo-bin \
        -c "${ODOO_RC:-/etc/odoo/odoo.conf}" \
        --db_host="${DB_HOST:-db}" \
        --db_port="${DB_PORT:-5432}" \
        --db_user="${DB_USER:-odoo}" \
        --db_password="${DB_PASSWORD:-odoo}" \
        "$@"
fi

exec "$@"
