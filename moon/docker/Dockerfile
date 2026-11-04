# Moon Exchange HRMS image
# = official ERPNext v16 production image + Frappe HR + the moon_hr app.
#
# Build (from the `moon/` folder):  docker compose -f docker/docker-compose.yml build
ARG ERPNEXT_IMAGE=frappe/erpnext:v16.53.0
FROM ${ERPNEXT_IMAGE}

ARG HRMS_REPO=https://github.com/frappe/hrms
ARG HRMS_REF=v16.53.1

USER frappe
WORKDIR /home/frappe/frappe-bench

# 1) Frappe HR (cached layer - only rebuilt when HRMS_REF changes).
#    The base image keeps compiled assets in ./assets (outside the `sites` volume),
#    so we temporarily point sites/assets at it while building.
RUN set -eux; \
    rm -rf sites/assets && ln -s /home/frappe/frappe-bench/assets sites/assets; \
    ls -1 apps > sites/apps.txt; \
    bench get-app --branch "${HRMS_REF}" hrms "${HRMS_REPO}"; \
    find apps/hrms -name .git -prune -exec rm -rf {} +; \
    rm -rf apps/hrms/frontend/node_modules apps/hrms/roster/node_modules /home/frappe/.cache/yarn; \
    rm sites/assets

# 2) Moon Exchange customisations.
COPY --chown=frappe:0 apps/moon_hr /home/frappe/frappe-bench/apps/moon_hr
RUN set -eux; \
    rm -rf sites/assets && ln -s /home/frappe/frappe-bench/assets sites/assets; \
    ./env/bin/pip install --no-cache-dir -e apps/moon_hr; \
    ls -1 apps > sites/apps.txt; \
    bench build --app moon_hr; \
    rm sites/assets; \
    chmod -R g=u apps/moon_hr

# Helper scripts used by docker-compose (site bootstrap + demo seed)
COPY --chown=frappe:0 docker/bootstrap.sh /home/frappe/bootstrap.sh
