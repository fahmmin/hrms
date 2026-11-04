# Moon Exchange HRMS

The HR, payroll and people-operations system for **Moon Exchange**, an FIU-IND registered crypto exchange.

It runs the open-source [Frappe HR](https://github.com/frappe/hrms) on [ERPNext](https://github.com/frappe/erpnext), plus our own app, **`moon_hr`**. That app adds what we needed on top:

| Added in `moon_hr` | What it does |
|---|---|
| **Person-specific work hours** | Expected hours come from each person's employment type (full-time, half-time, intern, contract, probation, apprentice, 24x7 ops) or a personal override. Worked hours are calculated from clock-in/clock-out, including lunch breaks, night shifts, approved leave, holidays and work-from-home days. |
| **Pipeline CRM** (Twenty-style) | Companies, people and opportunities on a kanban pipeline, with tasks, notes, an activity timeline, a pipeline report and "deal won" / "task assigned" automations. |
| **About page** | `/about` (alias `/team`) shows the co-founders, leadership and values from the founders whiteboard. |
| **Demo data** | One command seeds a realistic company (37 people) across *every* Frappe HR module, so the whole system can be shown on day one. |
| **One-command hosting** | Docker image + compose for a laptop demo, plus a production override with HTTPS and daily backups for a cloud VM. |

---

## Run the demo on your laptop

You only need **Docker Desktop** (Windows, macOS on Intel or Apple Silicon, or Linux), with at least 4 GB of RAM assigned to Docker.

```bash
git clone -b claude/hrms-cloud-hosting-custom-0netzf https://github.com/fahmmin/hrms.git moon-hrms
cd moon-hrms/moon
./start.sh            # Windows (PowerShell): docker compose -p moon -f docker/docker-compose.yml up -d --build
```

The first start builds the image, creates the site and seeds the demo. That takes **10–20 minutes**. Run `./start.sh logs` to watch progress. Later starts take under a minute.

Open **http://localhost:8080** and sign in:

| Who | Login | Password | Try |
|---|---|---|---|
| Administrator | `Administrator` | `admin` | everything |
| HR Manager | `swati@demo.moon.exchange` | `MoonDemo@2026` | approvals, payroll, recruitment |
| Engineering Manager | `arjun@demo.moon.exchange` | `MoonDemo@2026` | team leave approvals, interviews |
| Employee (mobile app) | `kavya@demo.moon.exchange` | `MoonDemo@2026` | `http://localhost:8080/hrms` → check in/out, leave, expenses, payslips |
| CRM user | `aisha@demo.moon.exchange` | `MoonDemo@2026` | pipeline kanban, tasks |

`./start.sh stop` stops the demo and keeps the data. `./start.sh reset` deletes everything, so the next start gives you a fresh demo.

---

## A 10-minute tour

1. **Apps screen → Moon Exchange.** This is the home for work hours and the CRM.
2. **Work Hours Report** (`Moon Exchange → Work Hours Report`). It shows expected vs worked hours per person for the last 30 days, with utilisation %, overtime, shortfall, late arrivals and leave. Switch **View → Daily** to see every day with first-in, last-out and breaks. Use **Recalculate** to rebuild from check-ins.
3. **Work Hour Policy.** Seven policies are seeded: Full-time 40 h, Part-time / Half-time 20 h, Intern 30 h (30 min auto-break), Contract 45 h, Probation 40 h, Apprentice 36 h, and 24x7 Ops on a 6-day week.
4. **Employee → Kavya Iyer → Work Hours tab.** Shows the personal policy, personal hours/day, worked vs expected this week and month, and overtime. The banner at the top shows today's live hours. Also open **Zoya Siddiqui** (personal 6 h/day) and **Tara Fernandes** (intern on a 4 h/day college schedule) to see per-person overrides.
5. **Mobile app** (`/hrms` as Kavya). Check out, and that day's **Employee Work Log** updates within seconds.
6. **Pipeline CRM.** Use *Deal Pipeline (Kanban)* and drag a card to **Customer**. The company becomes a Customer and the owner gets a "Deal won" notification. Open a company to see its people, deals, tasks, notes and timeline.
7. **Frappe HR modules**, all with data: see the table below.
8. **Public pages.** `/about` shows the founders and leadership. `/jobs` is the careers page with 4 open roles.

### What the demo data covers

| Area | Seeded |
|---|---|
| Organisation | Company *Moon Exchange* (INR, Indian fiscal year), 3 branches, 11 departments (Engineering, Compliance & AML, Trading Operations, Risk & Treasury, Customer Support, ...), grades, designations incl. **Principal Officer (FIU-IND)** |
| People | 6 founders/leaders (from the founders board) + 31 fictional staff + 1 former employee; reporting lines (org chart), 4 demo logins |
| Holidays & shifts | Office calendar (Sat/Sun off) and a 24x7 ops calendar (Sun off) with Indian holidays; 7 shift types including a night shift that crosses midnight; geofenced shift locations (Bengaluru, Mumbai); shift assignments and a pending shift request |
| Attendance | ~2,000 check-ins over 5 weeks (biometric + mobile app), ~780 auto-marked attendance records (present / half day / absent / late), WFH and on-duty attendance requests, compensatory-off requests |
| Leave | 3 leave policies (standard, intern, part-time) + a *Crypto Wellness Day* leave type, allocations for two leave periods, approved / rejected / pending leave applications |
| Payroll | CTC salary structure (Basic, HRA, Special Allowance, PF, Professional Tax, Income Tax), intern stipend structure, new-regime income tax slab with 4% cess, payroll periods, **two payroll runs** (last-but-one month submitted with its accounting entry; last month left as draft slips for review), performance bonus, referral incentive, retention bonus |
| Expenses | Expense claims (approved, draft, rejected), employee advances, domestic and international travel requests |
| Recruitment | Staffing plan, 3 job requisitions, 4 published job openings, 10 applicants, interview types with skill sets, 6 interviews with feedback, 2 job offers, appointment letter, employee referral |
| Lifecycle | Onboarding (template + project tasks), promotion, scheduled transfer, separation, exit interview, full & final statement, grievances |
| Performance | KRAs, 3 appraisal templates, a running appraisal cycle (19 appraisals), goals with progress, manager feedback |
| Training | 3 programs (PMLA & FIU-IND reporting, phishing awareness, volatile markets), events, results and feedback |
| Work hours | ~840 daily work logs, one manual correction, and rollups on every Employee record |
| CRM | 10 companies (market makers, a banking partner, vendors, institutions; all fictional `.example` domains), 12 people, 12 opportunities across all stages, 11 tasks, 6 notes, 2 automations, 2 kanban boards |

All seed dates are relative to the day you run it, so the demo always looks current.

> **About the founders' records.** Bios on the About page and on the Employee records use only the facts from the founders whiteboard. Frappe HR requires a date of birth, a joining date and a gender, so the seed fills these with obvious placeholders (01-01-1990, 06-01-2025, "Prefer not to say") and leaves a comment on each record asking HR to update them. Founders are deliberately left out of the payroll, attendance and leave demo data.
>
> **Photos.** Drop `saurabh.webp`, `manish-blazer.webp`, `devansh-yacht.webp`, `karol.webp` and `shashwat.webp` into `apps/moon_hr/moon_hr/public/team/`, then rebuild (`./start.sh`). Until then everyone is shown with their initials, as the founders board specifies.

---

## How the work-hours engine works

```
Employee Checkin (mobile app / web / biometric device)
        │  doc event → background job (deduplicated per employee & day)
        ▼
pair IN/OUT into sessions ─► worked hours, breaks, first-in, last-out, late-by
        │
expected hours for that person & day:
   personal hours/day  >  personal policy  >  policy of Employment Type  >  default policy
   minus approved leave (full / half day), public holidays, policy weekly offs
        │
        ▼
Employee Work Log (one per person per day)  ─►  Employee rollups (week / month / overtime)
        │                                    ─►  Employee Work Hours report (summary / daily)
        └─ HR can tick "Manual Entry" to correct a day; recalculation then leaves it alone
```

* Night shifts are grouped by **shift start**, so 22:00 → 06:00 counts as one day.
* With no check-ins, the Attendance record is used instead (biometric summaries, Work From Home).
* Statuses: On Track, Overtime (more than 30 min over target), Short, Half Day, Absent, On Leave, Holiday, Weekly Off, In Progress (today).
* An hourly job refreshes today and a nightly job closes out the last 7 days.

Code: `apps/moon_hr/moon_hr/moon_hr/work_hours.py`.

---

## Project layout

```
moon/
├── start.sh                         one-command laptop demo
├── docker/
│   ├── Dockerfile                   ERPNext v16 image + Frappe HR v16 + moon_hr
│   ├── docker-compose.yml           full stack: MariaDB, Redis, web, workers, scheduler, socket.io, nginx
│   ├── docker-compose.prod.yml      cloud override: Caddy (HTTPS) + daily backups
│   ├── docker-compose.dev.yml       live-mount moon_hr for development
│   ├── bootstrap.sh                 create site → install apps → setup wizard → seed (idempotent)
│   └── .env.example
├── apps/moon_hr/                    the custom Frappe app (upgrade-safe: no core code is modified)
│   └── moon_hr/
│       ├── moon_hr/                 module "Moon HR": Work Hour Policy, Employee Work Log, report, engine
│       ├── moon_crm/                module "Moon CRM": Pipeline Company / Person / Opportunity / Task / Note
│       ├── www/about.{py,html}      /about page
│       ├── data/team.py             founders & leadership (mirror of website/data/team.ts)
│       ├── demo/                    setup wizard automation + demo seed
│       └── install.py               custom fields, roles, default policies, kanban boards
├── website/data/team.ts             founders data for the marketing website (as supplied)
└── docs/HOSTING.md                  how to run it in the cloud for real
```

## Development

```bash
cd moon
docker compose -p moondev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
# edit apps/moon_hr/..., then:
docker compose -p moondev -f docker/docker-compose.yml exec backend bench --site moon.localhost migrate
```

Re-run the seed after a partial failure: `bench --site moon.localhost execute moon_hr.demo.seed.run`. Completed steps are skipped.

## Versions

Pinned in `docker/.env.example`: `frappe/erpnext:v16.53.0` (Frappe 16.55) and Frappe HR `v16.53.1`. To upgrade, change the tags, run `./start.sh` again, and the bootstrap runs `bench migrate`.

## Licence

`moon_hr` is GPLv3, like Frappe HR and ERPNext.
