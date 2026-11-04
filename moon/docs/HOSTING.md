# Hosting Moon Exchange HRMS in the cloud

This guide takes the same Docker stack used for the laptop demo and runs it on one cloud VM, with HTTPS, e-mail and backups. For a company of up to a few hundred employees, one VM is enough.

## 1. What is running

| Container | Role |
|---|---|
| `db` | MariaDB 11.8, the only stateful database |
| `redis-cache`, `redis-queue` | cache and background job queue |
| `backend` | Gunicorn, the Python web workers |
| `queue` | RQ workers: e-mails, payroll, auto-attendance, work-hour logs |
| `scheduler` | cron-style jobs: hourly/nightly work-hour refresh, leave accrual, reminders |
| `websocket` | Socket.IO realtime updates |
| `frontend` | nginx, serving static assets and proxying to the backend |
| `caddy` *(prod)* | TLS termination with automatic Let's Encrypt certificates |
| `backup` *(prod)* | daily `bench backup --with-files`, keeping 14 days |
| `configurator`, `create-site` | one-off setup jobs: create the site, migrate on upgrade, seed the demo |

## 2. Choose a server

| Size | vCPU / RAM / disk | Good for | Approx. cost |
|---|---|---|---|
| Minimum | 2 / 4 GB / 40 GB SSD | demo, up to about 50 employees | Hetzner CX22 ~€5, DigitalOcean ~$24 |
| **Recommended** | 4 / 8 GB / 80 GB SSD | up to about 500 employees, payroll runs in seconds | Hetzner CX32 ~€8, AWS t3.large ~$60, Lightsail 8 GB ~$40 |

Use Ubuntu 24.04 LTS. For data residency (payroll, PAN and Aadhaar-linked data), use an **India region**: AWS ap-south-1 (Mumbai), GCP asia-south1, Azure Central India, or DigitalOcean BLR1.

## 3. Step by step

```bash
# 3.1 DNS: create an A record   hr.moon.exchange -> <VM public IP>

# 3.2 On the VM: Docker + firewall
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable

# 3.3 Code
git clone -b claude/hrms-cloud-hosting-custom-0netzf https://github.com/fahmmin/hrms.git moon-hrms
cd moon-hrms/moon
cp docker/.env.example docker/.env
```

Edit `docker/.env`:

```ini
SITE_NAME=hr.moon.exchange
ADMIN_PASSWORD=<long random password>
DB_ROOT_PASSWORD=<long random password>
SEED_DEMO=0                       # 1 only for a demo/staging server
DOMAIN=hr.moon.exchange
ACME_EMAIL=ops@moon.exchange
```

```bash
# 3.4 Start (HTTPS + backups)
docker compose -p moon --env-file docker/.env \
  -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build

docker compose -p moon logs -f create-site     # wait for ">> Done"
```

Open `https://hr.moon.exchange` and sign in as Administrator. With `SEED_DEMO=0` you get a clean *Moon Exchange* company with the default work-hour policies, ready for real data.

## 4. After the first login

1. **E-mail.** Go to *Email Account → New*, use Google Workspace / SES / Brevo SMTP, and tick *Default Outgoing*. Then remove the demo mute: `docker compose -p moon exec backend bench --site hr.moon.exchange set-config mute_emails 0`.
2. **Single sign-on.** Go to *Social Login Key → Google* (or *Microsoft*) and add your Workspace OAuth client so staff sign in with company accounts. Enforce *System Settings → Two Factor Auth* for HR and admin roles.
3. **Import employees.** Use *Data Import → Employee*, starting from an exported template.
4. **Set up rules.** Holiday list, leave policies, salary structures, and Work Hour Policies for each employment type.
5. **Attendance devices.** Biometric devices post to `Employee Checkin` through the API (`/api/resource/Employee Checkin`) with an API key and secret from a dedicated integration user. The mobile app (`/hrms`) also supports geofenced check-in.

## 5. Backups and restore

The `backup` container writes a daily database dump plus public and private files to the `sites` volume (`sites/<site>/private/backups`). **Also copy them off the server**, for example with rclone to S3 or Backblaze B2:

```bash
# crontab on the VM, 02:30 daily
30 2 * * * docker run --rm -v moon_sites:/sites:ro -v ~/.config/rclone:/config/rclone rclone/rclone:1.68 \
  copy /sites/hr.moon.exchange/private/backups b2:moon-hr-backups
```

Restore on a fresh server:

```bash
docker compose -p moon exec backend bench --site hr.moon.exchange restore \
  /home/frappe/frappe-bench/sites/hr.moon.exchange/private/backups/<file>-database.sql.gz \
  --with-public-files <...>-files.tar --with-private-files <...>-private-files.tar
```

**Test a restore at least once a quarter.**

## 6. Upgrades

```bash
git pull
# optionally bump ERPNEXT_IMAGE / HRMS_REF in docker/.env
docker compose -p moon --env-file docker/.env -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
```

`create-site` runs `bench migrate` automatically on every start. Take a backup first and try the upgrade on a staging copy before production.

## 7. Monitoring and security checklist

- [ ] Uptime check on `https://hr.moon.exchange/api/method/ping`, for example with UptimeRobot or Uptime Kuma.
- [ ] Disk alerts above 80%: backups and logs grow over time.
- [ ] Only ports 22, 80 and 443 open; SSH by key only (`PasswordAuthentication no`).
- [ ] Strong `ADMIN_PASSWORD` and `DB_ROOT_PASSWORD`; never commit `docker/.env`.
- [ ] 2FA for System Manager, HR Manager and payroll roles.
- [ ] Off-site backups with a tested restore.
- [ ] *System Settings*: session expiry, password policy, login attempts lockout.
- [ ] Review *Role Permissions* so salary data is visible only to payroll roles.

## 8. Alternatives

- **Frappe Cloud** (managed): fastest, with backups and upgrades handled for you. Install `erpnext`, `hrms` and this `moon_hr` app from its Git repository.
- **Kubernetes**: the same image works with the official `frappe/helm` chart when you outgrow one VM.
- **Managed database**: point `db_host` at Amazon RDS for MariaDB and remove the `db` container.
