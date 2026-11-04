#!/bin/bash
# Site bootstrap for the Moon Exchange HRMS stack (runs in the `create-site` service).
#  - first run : create site, install erpnext + hrms + moon_hr, run setup wizard, seed demo data
#  - later runs: bench migrate (applies app upgrades after an image rebuild)
set -euo pipefail
cd /home/frappe/frappe-bench

SITE="${SITE_NAME:-moon.localhost}"

wait-for-it -t 180 db:3306
wait-for-it -t 60 redis-cache:6379
wait-for-it -t 60 redis-queue:6379

ls -1 apps > sites/apps.txt

if [ ! -f "sites/${SITE}/site_config.json" ]; then
  echo ">> Creating site ${SITE}"
  bench new-site "${SITE}" \
    --mariadb-user-host-login-scope='%' \
    --db-root-username=root \
    --db-root-password="${DB_ROOT_PASSWORD}" \
    --admin-password="${ADMIN_PASSWORD}" \
    --install-app erpnext \
    --install-app hrms \
    --install-app moon_hr \
    --set-default
  # Demo instance: never send real e-mails to the seeded (fictional) addresses.
  bench --site "${SITE}" set-config -p mute_emails 1
else
  echo ">> Site ${SITE} exists - running migrate"
  bench --site "${SITE}" migrate
fi

# Company + fiscal year + defaults (idempotent).
bench --site "${SITE}" execute moon_hr.demo.setup.complete_setup

if [ "${SEED_DEMO:-1}" = "1" ]; then
  echo ">> Seeding demo data (skipped automatically if already seeded)"
  bench --site "${SITE}" execute moon_hr.demo.seed.run
fi

bench --site "${SITE}" enable-scheduler
bench --site "${SITE}" clear-cache
echo ">> Done. Open http://localhost:${HTTP_PORT:-8080}"
