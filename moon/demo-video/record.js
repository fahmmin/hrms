// Scripted walkthrough of the Moon Exchange HRMS demo -> webm clips (desktop1, mobile, desktop2)
const { chromium } = require('playwright');
const B = process.env.BASE || 'http://localhost:8080';
const OUT = process.env.OUT || require('path').join(__dirname, 'raw');
const W = 1280, H = 800;
const SPEED = 1.45; // >1 = slower, more reading time

const OVERLAY = () => {
  const install = () => {
    if (!document.body || document.getElementById('__cap')) return;
    const st = document.createElement('style');
    st.textContent = `
      #__cap{position:fixed;left:50%;bottom:14px;transform:translateX(-50%);z-index:2147483647;
        background:rgba(15,23,42,.92);color:#fff;padding:12px 22px;border-radius:14px;max-width:86%;
        font:500 16px/1.35 Inter,system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.25);
        transition:opacity .3s;pointer-events:none;text-align:center}
      #__cap b{color:#F5C542;font-weight:700;display:block;font-size:13px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:2px}
      #__cap:empty{opacity:0}
      @media (max-width:500px){#__cap{bottom:84px;font-size:14px;padding:9px 14px}}
      #__cur{position:fixed;z-index:2147483647;width:22px;height:22px;pointer-events:none;left:-40px;top:-40px;
        transition:transform .08s}
      #__cur.down{transform:scale(.8)}`;
    document.head.appendChild(st);
    const c = document.createElement('div'); c.id = '__cap'; document.body.appendChild(c);
    const k = document.createElement('div'); k.id = '__cur';
    k.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.5-7.5L20 11z" fill="#111827" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.body.appendChild(k);
    document.addEventListener('mousemove', e => { k.style.left = e.clientX - 3 + 'px'; k.style.top = e.clientY - 2 + 'px'; }, true);
    document.addEventListener('mousedown', () => k.classList.add('down'), true);
    document.addEventListener('mouseup', () => k.classList.remove('down'), true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install); else install();
  setInterval(install, 500);
};

function helpers(page) {
  let mx = W / 2, my = H / 2;
  const h = {
    pause: (ms) => page.waitForTimeout(Math.round(ms * SPEED)),
    cap: async (title, sub = '') => {
      const html = title ? `<b>${title}</b>${sub}` : '';
      for (let i = 0; i < 20; i++) {
        const ok = await page.evaluate((html) => { const c = document.getElementById('__cap'); if (c) { c.innerHTML = html; return true; } return false; }, html).catch(() => false);
        if (ok) break; await page.waitForTimeout(150);
      }
    },
    go: async (url, wait = 1800, title, sub) => {
      await page.goto(B + url, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => {});
      if (title !== undefined) await h.cap(title, sub);
      await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(wait);
      await page.mouse.move(mx, my);
    },
    move: async (x, y, steps = 25) => { await page.mouse.move(x, y, { steps }); mx = x; my = y; },
    to: async (loc, steps = 25) => {
      const el = loc.first();
      await el.scrollIntoViewIfNeeded({ timeout: 8000 }).catch(() => {});
      const box = await el.boundingBox({ timeout: 6000 }).catch(() => null);
      if (!box) return false;
      await h.move(box.x + Math.min(box.width / 2, 60), box.y + box.height / 2, steps);
      return true;
    },
    click: async (loc, after = 1500) => {
      if (await h.to(loc)) { await h.pause(250); await page.mouse.down(); await page.mouse.up(); await h.pause(after); return true; }
      console.log('  (missing)', loc.toString()); return false;
    },
    scroll: async (dy, steps = 12, delay = 60) => {
      for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await page.waitForTimeout(delay); }
    },
    type: async (loc, text) => { await h.click(loc, 200); await page.keyboard.type(text, { delay: 55 }); },
  };
  return h;
}

async function api(ctx, path) {
  const r = await ctx.request.get(B + path); return (await r.json()).data || [];
}
const q = (o) => encodeURIComponent(JSON.stringify(o));

(async () => {
  const browser = await chromium.launch();
  const mkctx = (opts = {}) => browser.newContext({
    viewport: { width: W, height: H }, recordVideo: { dir: OUT + '/' + (opts.name || 'x'), size: { width: W, height: H } },
    locale: 'en-IN', timezoneId: 'Asia/Kolkata', ...opts.ctx,
  });

  // look-ups (separate, non-recorded context)
  const look = await browser.newContext();
  await look.request.post(B + '/api/method/login', { form: { usr: 'Administrator', pwd: 'admin' } });
  const emp = async (k) => (await api(look, `/api/resource/Employee?filters=${q([['moon_demo_key', '=', k]])}`))[0].name;
  const kavya = await emp('kavya'), zoya = await emp('zoya'), tara = await emp('tara');
  const slip = (await api(look, `/api/resource/Salary Slip?filters=${q([['employee', '=', kavya], ['docstatus', '=', 1]])}`))[0]?.name;
  const claim = (await api(look, `/api/resource/Expense Claim?filters=${q([['docstatus', '=', 1], ['approval_status', '=', 'Approved']])}`))[0]?.name;
  const opening = (await api(look, `/api/resource/Job Opening?filters=${q([['job_title', 'like', 'Senior Backend%']])}`))[0]?.name;
  const appraisal = (await api(look, `/api/resource/Appraisal?filters=${q([['employee', '=', kavya]])}`))[0]?.name;
  const onboarding = (await api(look, `/api/resource/Employee Onboarding`))[0]?.name;
  const payroll = (await api(look, `/api/resource/Payroll Entry?filters=${q([['docstatus', '=', 1]])}&order_by=start_date asc`))[0]?.name;
  const interview = (await api(look, `/api/resource/Interview?filters=${q([['status', '=', 'Cleared']])}`))[0]?.name;
  console.log({ kavya, slip, claim, opening, appraisal, onboarding, payroll, interview });

  // ===================================================== DESKTOP PART 1
  let ctx = await mkctx({ name: 'd1' });
  await ctx.addInitScript(OVERLAY);
  let page = await ctx.newPage();
  let h = helpers(page);

  await h.go('/login', 1200, 'Moon Exchange HRMS', 'Frappe HR v16 + ERPNext + our own <i>moon_hr</i> app &middot; one-command Docker demo');
  await h.pause(2500);
  await h.type(page.locator('#login_email'), 'Administrator');
  await h.type(page.locator('#login_password'), 'admin');
  await h.click(page.locator('button:has-text("Continue")').first(), 3500);

  await h.go('/desk', 1500, 'Apps screen', 'ERPNext, Frappe HR and our <b style="display:inline;color:#F5C542;font-size:16px;text-transform:none;letter-spacing:0">Moon Exchange</b> app');
  await h.pause(1800);
  await h.click(page.locator('text=Moon Exch').first(), 3000);
  await h.cap('Moon Exchange workspace', 'Work hours, people and the Pipeline CRM in one place, with live counts');
  await h.pause(3500);

  await h.go('/desk/work-hour-policy', 1500, 'Work Hour Policies', 'Expected hours per employment type: full-time 40 h, half-time 20 h, intern 30 h, contract, probation, 24x7 ops');
  await h.pause(3500);
  await h.click(page.locator('a:has-text("Part-time / Half-time")').first(), 2000);
  await h.cap('Policy rules', 'Working days, start time, late grace, auto-break, half-day threshold, overtime threshold');
  await h.scroll(500, 14, 90); await h.pause(2500); await h.scroll(-500, 8);
  await h.click(page.locator('button:has-text("Employees on this policy")').first(), 2500);
  await h.pause(1500);
  await page.keyboard.press('Escape'); await h.pause(800);

  await h.go('/desk/query-report/Employee Work Hours', 3000, 'Employee Work Hours report', 'Expected vs worked hours for every person, using their own policy, for the last 30 days');
  await h.pause(3000);
  await h.move(700, 230); await h.pause(1200);
  await h.cap('Utilisation, overtime, late arrivals', 'Computed from real clock-in / clock-out sessions, leave, holidays and WFH');
  await h.scroll(450, 14, 90); await h.pause(3000);
  await page.mouse.wheel(600, 0); await h.pause(2500); await page.mouse.wheel(-600, 0);
  await h.scroll(-450, 8);
  // daily view
  const viewSel = page.locator('.frappe-control[data-fieldname="view"] select').first();
  if (await viewSel.count()) {
    await h.to(viewSel); await viewSel.selectOption('Daily'); await h.pause(3000);
    await h.cap('Daily view', 'Every person, every day: first in, last out, breaks, overtime, shortfall, late minutes');
    await h.scroll(400, 12, 90); await h.pause(3000); await h.scroll(-400, 6);
  }

  await h.go(`/desk/employee/${zoya}`, 2500, 'Person-specific targets', 'Zoya has a personal 6 h/day schedule that overrides the full-time policy');
  await h.click(page.locator('.form-tabs .nav-link:has-text("Work Hours")').first(), 2000);
  await h.pause(3500);
  await h.go(`/desk/employee/${tara}`, 2500, 'Interns on a college schedule', 'Tara: intern policy is 6 h/day, personal override 4 h/day. Live banner shows today');
  await h.click(page.locator('.form-tabs .nav-link:has-text("Work Hours")').first(), 2000);
  await h.pause(3500);
  await h.cap('', '');
  await ctx.close();

  // ===================================================== MOBILE (employee app)
  const mctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: false,
    recordVideo: { dir: OUT + '/m', size: { width: 390, height: 844 } },
    geolocation: { latitude: 12.9352, longitude: 77.6245 }, permissions: ['geolocation'],
    locale: 'en-IN', timezoneId: 'Asia/Kolkata',
  });
  await mctx.addInitScript(OVERLAY);
  await mctx.request.post(B + '/api/method/login', { form: { usr: 'kavya@demo.moon.exchange', pwd: 'MoonDemo@2026' } });
  page = await mctx.newPage(); h = helpers(page);
  await h.go('/hrms/home', 4000, 'Employee app', 'Kavya clocks out from her phone (geofenced to the Bengaluru office)');
  await h.pause(2500);
  const btn = page.locator('button:has-text("Check Out"), button:has-text("Check In")').first();
  await h.click(btn, 2000);
  const confirm = page.locator('button:has-text("Confirm")').first();
  if (await confirm.count()) await h.click(confirm, 3000);
  await h.pause(2000);
  await h.cap('Self-service', 'Attendance, leave, expenses, advances and payslips');
  for (const tab of ['Attendance', 'Leaves', 'Expenses', 'Salary']) {
    await h.click(page.locator(`ion-tab-button:has-text("${tab}")`).first(), 2600);
  }
  await h.cap('', '');
  await mctx.close();

  // ===================================================== DESKTOP PART 2
  ctx = await mkctx({ name: 'd2' });
  await ctx.addInitScript(OVERLAY);
  await ctx.request.post(B + '/api/method/login', { form: { usr: 'Administrator', pwd: 'admin' } });
  page = await ctx.newPage(); h = helpers(page);

  await h.go(`/desk/employee-work-log?employee=${kavya}`, 2500, 'Updated live', "The check-out reached Kavya's Employee Work Log seconds later via a background job");
  await h.pause(2500);
  await h.click(page.locator('.list-row-container .level-left a.ellipsis, .list-row .list-subject a').first(), 2500);
  await h.cap('Daily work log', 'Clock-in sessions, worked vs expected hours, overtime, late-by, plus a manual override for HR');
  await h.scroll(500, 12, 90); await h.pause(3000);

  await h.go('/desk/employee-checkin', 2500, 'Check-ins', '~2,000 clock-ins from biometric devices and the mobile app');
  await h.pause(3000);
  await h.go('/desk/attendance', 2500, 'Auto attendance', 'Shifts turn check-ins into Present / Half Day / Absent, with late-entry and early-exit flags');
  await h.pause(3500);
  await h.go('/hr/roster', 4000, 'Shift roster', 'Month view of shifts, weekly offs and holidays: day, half-time, intern and 24x7 ops shifts');
  await h.scroll(1200, 16, 110); await h.pause(3000);

  await h.go('/desk/leave-application', 2500, 'Leave', 'Policies, allocations and applications: approved, rejected and pending');
  await h.pause(3000);
  await h.go('/desk/query-report/Employee Leave Balance', 4000, 'Leave balances', 'Allocated, taken and remaining leave per person and leave type');
  await h.pause(3500);

  if (payroll) {
    await h.go(`/desk/payroll-entry/${payroll}`, 3000, 'Payroll', 'Monthly payroll run for 31 employees, posted to accounts');
    await h.pause(3500);
  }
  if (slip) {
    await h.go(`/desk/salary-slip/${slip}`, 3000, 'Salary slip', 'Basic, HRA, special allowance, PF, professional tax and new-regime income tax');
    await h.scroll(700, 14, 90); await h.pause(3500);
  }
  if (claim) {
    await h.go(`/desk/expense-claim/${claim}`, 3000, 'Expenses', 'Claims with approvals, employee advances and travel requests');
    await h.pause(3500);
  }

  if (opening) {
    await h.go(`/desk/job-opening/${opening}`, 3000, 'Recruitment', 'Staffing plan, requisitions, published openings, applicants, interviews and offers');
    await h.pause(3000);
  }
  await h.go('/desk/job-applicant', 2500, 'Applicant pipeline', 'Applicants by status, source and rating');
  await h.pause(3000);
  if (interview) {
    await h.go(`/desk/interview/${interview}`, 3000, 'Interviews', 'Interview types with skill sets, feedback and ratings');
    await h.pause(3000);
  }
  if (onboarding) {
    await h.go(`/desk/employee-onboarding/${onboarding}`, 3000, 'Onboarding', 'Laptop and security keys, background checks, AML training, least-privilege access');
    await h.scroll(500, 12, 90); await h.pause(3000);
  }
  if (appraisal) {
    await h.go(`/desk/appraisal/${appraisal}`, 3500, 'Performance', 'Appraisal cycle with KRAs, goals that roll up automatically and 360° feedback');
    await h.scroll(600, 14, 90); await h.pause(3500);
  }
  await h.go('/desk/training-event', 2500, 'Training', 'PMLA & FIU-IND reporting, phishing awareness, volatile-market playbooks');
  await h.pause(3000);
  await h.go('/desk/organizational-chart', 3500, 'Org chart', 'Founders, leadership and reporting lines');
  const expand = page.locator('button:has-text("Expand All")').first();
  if (await expand.count()) { await h.click(expand, 2500); }
  await h.scroll(600, 14, 100); await h.pause(2500);

  // CRM
  await h.go('/desk/pipeline-opportunity/view/kanban/Opportunities by Stage', 3500, 'Pipeline CRM', 'Twenty-style deal board: market makers, institutions, banking and payment partners');
  await h.pause(3000);
  await page.evaluate(() => { const bd = document.querySelector('.kn-board'); if (bd) bd.scrollTo({ left: 520, behavior: 'smooth' }); });
  await h.pause(1200);
  const card = page.locator('.kn-card:has-text("Tidewater - OTC")').first();
  const target = page.locator('.kn-column[data-col="Customer"] .kn-column-body').first();
  const cb = await card.boundingBox({ timeout: 5000 }).catch(() => null);
  const tb = await target.boundingBox({ timeout: 5000 }).catch(() => null);
  if (cb && tb) {
    await h.cap('Drag a deal to Customer', 'The company becomes a customer and the deal owner is notified automatically');
    await h.move(cb.x + 60, cb.y + 30); await h.pause(700);
    await page.mouse.down();
    await h.move(cb.x + 80, cb.y + 40, 6);
    await h.move(tb.x + 80, tb.y + 90, 45);
    await h.pause(400); await page.mouse.up(); await h.pause(3500);
  } else console.log('  (kanban drag skipped)', !!cb, !!tb);
  await h.go('/desk/pipeline-company/Northstar Liquidity', 3000, 'Company record', 'People, deals, tasks, notes and a timeline for each account');
  await h.pause(3500);
  await h.go('/desk/query-report/Pipeline Summary', 3000, 'Pipeline report', 'Open and weighted pipeline by stage, won value and win rate');
  await h.pause(3500);

  // public pages
  await h.go('/about', 2500, 'About page', 'Co-founders, leadership and values from the founders board (initials until photos are added)');
  await h.scroll(1400, 20, 120); await h.pause(2500);
  await h.go('/jobs', 2500, 'Careers page', 'Job openings are published to the website automatically');
  await h.pause(3000);
  await h.go('/desk/moon-exchange', 2000, 'Moon Exchange HRMS', 'Run it yourself: <code style="color:#F5C542">cd moon && ./start.sh</code> &rarr; http://localhost:8080');
  await h.pause(4000);
  await ctx.close();
  await browser.close();
  console.log('done');
})();
