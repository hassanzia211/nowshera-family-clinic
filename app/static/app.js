"use strict";
const $ = (s) => document.querySelector(s);
const state = {
  user: null,
  csrf: "",
  page: "dashboard",
  today: "",
  now: "",
  doctors: [],
  appointments: [],
  booking: null,
  auth: "login",
};
const icons = {
  grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  calendar: "M4 5h16v16H4z M4 10h16 M8 2v6 M16 2v6",
  people:
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M16 3a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-3.9 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  clock: "M12 8v5l3 2 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  check: "m5 12 4 4L19 6",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z m-4 9 3 3 5-6",
  plus: "M12 4v16 M4 12h16",
  logout: "M9 4H4v16h5 M9 12h12 m-4-4 4 4-4 4",
  heart:
    "M20 5c-3-3-6-1-8 1-2-2-5-4-8-1-4 4 0 9 8 15 8-6 12-11 8-15 M2 12h5l2-4 4 8 2-4h7",
  arrow: "M4 12h16 m-6-6 6 6-6 6",
  menu: "M3 6h18 M3 12h18 M3 18h18",
  mail: "M3 5h18v14H3z m0 0 9 8 9-8",
};
const icon = (n) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[n] || icons.grid}"/></svg>`;
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const initials = (n) =>
  esc(
    n
      .replace(/^Dr\.\s*/, "")
      .split(" ")
      .map((x) => x[0])
      .slice(0, 2)
      .join(""),
  );
const brand = () =>
  '<div class="brand"><span class="brandmark">+</span><span>Nowshera<small>Family Clinic</small></span></div>';
const pill = (s) => `<span class="pill ${esc(s)}">${esc(s)}</span>`;
const date = (s) =>
  new Date(s.slice(0, 10) + "T12:00:00").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
const time = (s) => {
  const [h, m] = s.slice(11, 16).split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
};
const weekdays = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
let toastTimer;
function toast(message, error = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "show" + (error ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = ""), 5500);
}
async function api(path, method = "GET", body) {
  const response = await fetch("/api" + path, {
    method,
    headers:
      method === "GET"
        ? {}
        : { "Content-Type": "application/json", "X-CSRF-Token": state.csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(result.error || "Unable to complete the request.");
  return result;
}
async function session() {
  const result = await api("/session");
  Object.assign(state, result);
  return result;
}
function empty(title, description = "") {
  return `<div class="empty">${icon("calendar")}<strong>${esc(title)}</strong>${esc(description)}</div>`;
}
function modal(title, body, subtitle = "") {
  const dlg = $("#modal");
  $("#modal-content").innerHTML =
    `<div class="modal-head"><div><h2>${esc(title)}</h2>${subtitle ? `<p class="subtitle">${esc(subtitle)}</p>` : ""}</div><button class="ghost" data-action="close" aria-label="Close dialog">×</button></div>${body}`;
  if (!dlg.open) dlg.showModal();
}
function closeModal() {
  $("#modal").close();
  state.booking = null;
}
function auth() {
  const invite = location.hash.startsWith("#invite=");
  const register = state.auth === "register" && !invite;
  const title = invite
    ? "Set your password"
    : register
      ? "A healthier start."
      : "Welcome back.";
  $("#root").innerHTML =
    `<div class="auth"><section class="auth-story">${brand()}<div class="auth-copy"><p class="eyebrow">YOUR NEIGHBORHOOD. YOUR CARE.</p><h1>Good health starts<br>with <em>good care.</em></h1><p>A simpler way to connect with your doctor. Book your visit, keep track of your appointments, and feel a little more at ease.</p><div class="auth-visual"><div class="hero-art">${icon("heart")}</div><p>Thoughtful care.<br>One connected clinic.</p></div></div><div class="auth-footer">Nowshera, Pakistan &nbsp; · &nbsp; Patient-first, always.</div></section><section class="auth-form"><div class="auth-box"><div class="mobile-brand">${brand()}</div><p class="eyebrow">${invite ? "DOCTOR INVITATION" : "YOUR CLINIC, CONNECTED"}</p><h2>${title}</h2><p class="subtitle">${invite ? "Choose a secure password to activate your doctor account." : register ? "Create your patient account to book your first visit." : "Sign in to your personal clinic workspace."}</p><form data-form="${invite ? "set-password" : register ? "register" : "login"}">${register ? '<div class="field"><label for="name">Full name</label><input id="name" name="name" autocomplete="name" maxlength="100" required placeholder="Your full name"></div><div class="field"><label for="phone">Phone number</label><input id="phone" name="phone" type="tel" autocomplete="tel" maxlength="30" required placeholder="0300 1234567"></div>' : ""}${!invite ? '<div class="field"><label for="email">Email address</label><input id="email" name="email" type="email" autocomplete="email" maxlength="254" required placeholder="you@example.com"></div>' : ""}<div class="field"><label for="password">${invite ? "New password" : "Password"}</label><input id="password" name="password" type="password" autocomplete="${register || invite ? "new-password" : "current-password"}" ${register || invite ? 'minlength="10"' : ""} maxlength="128" required placeholder="${register || invite ? "At least 10 characters" : "Enter your password"}"></div><div id="form-error" role="alert"></div><button type="submit">${invite ? "Activate account" : register ? "Create patient account" : "Sign in"} ${icon("arrow")}</button></form>${!invite ? `<p class="auth-switch">${register ? "Already have an account?" : "New to the clinic?"} <button data-action="auth-switch">${register ? "Sign in" : "Create an account"}</button></p>` : ""}<div class="auth-trust">${icon("shield")}Your records. Private and protected.</div></div></section></div>`;
}
const pages = {
  dashboard: ["grid", "Overview"],
  appointments: ["calendar", "Appointments"],
  doctors: ["people", "Find a doctor"],
  availability: ["clock", "My availability"],
  patients: ["people", "Patients"],
  team: ["people", "Doctors"],
};
function shell() {
  const role = state.user.role;
  const nav =
    role === "patient"
      ? ["dashboard", "doctors", "appointments"]
      : role === "doctor"
        ? ["dashboard", "appointments", "availability", "patients"]
        : ["dashboard", "appointments", "team", "patients"];
  $("#root").innerHTML =
    `<aside class="sidebar">${brand()}<p class="nav-label">${role.toUpperCase()} WORKSPACE</p><nav class="nav" aria-label="Main navigation">${nav.map((p) => `<button data-action="nav" data-page="${p}" class="${state.page === p ? "active" : ""}">${icon(pages[p][0])}${pages[p][1]}</button>`).join("")}</nav><div class="sidebar-bottom"><div class="support">${icon("heart")}<p><strong>Care, without the clutter.</strong></p><p>All your appointments and clinic updates, in one place.</p><span class="pill Confirmed">Pakistan time · PKT</span></div><div class="profile"><span class="avatar">${initials(state.user.name)}</span><div><strong>${esc(state.user.name)}</strong><small>${role[0].toUpperCase() + role.slice(1)} account</small></div><button class="ghost" data-action="logout" aria-label="Sign out" title="Sign out">${icon("logout")}</button></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb"><button class="ghost mobile-toggle" data-action="menu" aria-label="Open navigation">${icon("menu")}</button>Workspace <span>/</span> <strong>${pages[state.page][1]}</strong></div><div class="top-date">${icon("calendar")}${date(state.today)}<span class="pill Confirmed">Clinic workspace</span></div></header><div class="content" id="content"><div class="loading">Loading…</div></div></main>`;
}
function heading(title, sub, button = "") {
  return `<div class="page-heading"><div><p class="eyebrow">NOWSHERA FAMILY CLINIC</p><h1>${esc(title)}</h1><p class="subtitle">${esc(sub)}</p></div>${button}</div>`;
}
const bookButton = () =>
  `<button data-action="nav" data-page="doctors">${icon("plus")}Book appointment</button>`;
function footer() {
  return '<footer class="footer"><span>© Nowshera Family Clinic · A little more care, every day.</span><span>All times in Pakistan Standard Time</span></footer>';
}
async function render() {
  shell();
  try {
    if (state.page === "dashboard") await dashboard();
    else if (state.page === "appointments") await appointments();
    else if (["doctors", "team"].includes(state.page)) await doctors();
    else if (state.page === "availability") await availability();
    else if (state.page === "patients") await patients();
  } catch (e) {
    $("#content").innerHTML = empty("Unable to load this page", e.message);
    toast(e.message, true);
  }
}
function appointmentTable(rows, compact = false) {
  if (!rows.length)
    return empty(
      "No appointments here yet",
      "Your appointments will appear here when a visit is requested.",
    );
  return `<div class="table-wrap"><table><thead><tr><th>${state.user.role === "patient" ? "Doctor" : "Patient"}</th><th>${state.user.role === "admin" ? "Doctor" : "Visit"}</th><th>Date & time</th><th>Status</th><th></th></tr></thead><tbody>${rows.map((a) => `<tr><td><div class="person-cell"><span class="avatar">${initials(state.user.role === "patient" ? a.doctor_name : a.patient_name)}</span><div><strong>${esc(state.user.role === "patient" ? a.doctor_name : a.patient_name)}</strong><small>${state.user.role === "patient" ? esc(a.specialty) : "#APT-" + String(a.id).padStart(4, "0")}</small></div></div></td><td>${state.user.role === "admin" ? esc(a.doctor_name) : "Clinic appointment"}<small>30-minute visit</small></td><td><strong>${date(a.start)}</strong><small>${time(a.start)}</small></td><td>${pill(a.status)}</td><td><button class="secondary small" data-action="detail" data-id="${a.id}">View ${icon("arrow")}</button></td></tr>`).join("")}</tbody></table></div>`;
}
async function dashboard() {
  const [dash, apps, docs] = await Promise.all([
    api("/dashboard"),
    api("/appointments"),
    api("/doctors"),
  ]);
  state.doctors = docs.doctors;
  state.appointments = apps.appointments;
  const role = state.user.role;
  const short = state.user.name.replace(/^Dr\.\s*/, "").split(" ")[0];
  const isPatient = role === "patient";
  const today = apps.appointments.filter(
    (a) => a.start.slice(0, 10) === state.today,
  );
  const upcoming = apps.appointments
    .filter(
      (a) =>
        ["Pending", "Confirmed"].includes(a.status) && a.start >= state.now,
    )
    .sort((a, b) => a.start.localeCompare(b.start));
  const stats = isPatient
    ? [
        [
          "Upcoming visits",
          upcoming.length,
          "calendar",
          "Pending and confirmed",
        ],
        [
          "Awaiting confirmation",
          dash.counts.Pending,
          "clock",
          "Your appointment requests",
        ],
        [
          "Completed visits",
          dash.counts.Completed,
          "check",
          "Your care history",
        ],
        [
          "Available doctors",
          docs.doctors.length,
          "people",
          "Find the right specialist",
        ],
      ]
    : [
        [
          "Appointments today",
          dash.today,
          "calendar",
          "All appointments scheduled today",
        ],
        [
          "Awaiting confirmation",
          dash.counts.Pending,
          "clock",
          "Requests that need attention",
        ],
        [
          "Confirmed visits",
          dash.counts.Confirmed,
          "check",
          "Accepted appointments",
        ],
        [
          role === "admin" ? "Registered patients" : "Completed visits",
          role === "admin" ? dash.patients : dash.counts.Completed,
          "people",
          role === "admin"
            ? "Your clinic community"
            : "Visits marked as completed",
        ],
      ];
  $("#content").innerHTML =
    heading(
      `Good to see you, ${short}.`,
      isPatient
        ? "Your next step toward feeling better starts here."
        : "Here’s what’s happening at your clinic.",
      isPatient
        ? bookButton()
        : `<button class="secondary" data-action="refresh">${icon("calendar")}Refresh overview</button>`,
    ) +
    `<section class="hero"><div><p class="eyebrow">${isPatient ? "A LITTLE MORE PEACE OF MIND" : "CONNECTED CARE, EVERY DAY"}</p><h2>${isPatient ? "Your care, on your schedule." : "A clear view of the day ahead."}</h2><p>${isPatient ? "Find the right doctor, choose a time that works, and let us take care of the rest." : "Less time managing appointments. More time focused on the people who need you."}</p></div><div class="hero-art">${icon("heart")}</div></section><div class="stats">${stats.map(([label, value, i, caption]) => `<div class="stat"><div class="stat-top">${label}${icon(i)}</div><div class="stat-value">${String(value).padStart(2, "0")}</div><div class="stat-caption">${caption}</div></div>`).join("")}</div><div class="split"><div><section class="panel"><div class="panel-head"><div><h2>${isPatient ? "Your upcoming visits" : "Today’s appointments"}</h2><p>${isPatient ? "Keep your next appointments in view." : date(state.today) + " · Pakistan time"}</p></div><button class="ghost small" data-action="nav" data-page="appointments">View all ${icon("arrow")}</button></div>${appointmentTable((isPatient ? upcoming : today).slice(0, 5), true)}</section></div><aside><section class="panel"><div class="panel-head"><h2>${role === "doctor" ? "Your practice" : "Our care team"}</h2>${icon("people")}</div><div class="panel-body">${(role === "doctor" ? docs.doctors.filter((d) => d.id === state.user.id) : docs.doctors.filter((d) => d.active).slice(0, 3)).map((d) => `<div class="doctor-row"><div class="avatar">${initials(d.name)}</div><div><strong>${esc(d.name)}</strong><p>${esc(d.specialty)}</p></div></div>`).join("") || '<p class="subtitle">Add your first doctor to get started.</p>'}</div></section><p class="footnote">${icon("shield")} ${isPatient ? "Visit notes are visible only to you and the doctor who saw you." : role === "admin" ? "Clinical notes stay between the patient and their doctor." : "You can access only your own appointments and patient history."}</p></aside></div>${role === "admin" ? doctorCounts(dash.doctors) + `<p class="notice">${state.mail_mode === "file" ? "Email delivery is in local demo mode. Messages are saved in instance/outbox; no real emails are sent. Configure SMTP in .env for real delivery." : "SMTP delivery is enabled."} ${dash.mail.map((m) => esc(m.state) + ": " + m.total).join(" · ")}</p>` : ""}` +
    footer();
}
function doctorCounts(doctors) {
  return `<section class="panel"><div class="panel-head"><div><h2>Doctor activity</h2><p>All-time appointment totals · saved in your clinic database</p></div></div><div class="table-wrap"><table><thead><tr><th>Doctor</th>${["Pending", "Confirmed", "Completed", "No-show", "Cancelled", "Rejected"].map((s) => `<th>${s}</th>`).join("")}</tr></thead><tbody>${doctors.map((d) => `<tr><td><strong>${esc(d.name)}</strong><small>${esc(d.specialty)}${d.active ? "" : " · Inactive"}</small></td>${["Pending", "Confirmed", "Completed", "No-show", "Cancelled", "Rejected"].map((s) => `<td>${d.counts[s]}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>`;
}
async function appointments() {
  const docs = await api("/doctors");
  state.doctors = docs.doctors;
  $("#content").innerHTML =
    heading(
      "Appointments",
      state.user.role === "patient"
        ? "Keep track of every step in your care."
        : "Manage requests, scheduled visits, and appointment history.",
      state.user.role === "patient" ? bookButton() : "",
    ) +
    `<section class="panel"><div class="filters"><select id="filter-status" aria-label="Filter by status"><option value="">All statuses</option>${["Pending", "Confirmed", "Completed", "No-show", "Cancelled", "Rejected"].map((s) => `<option>${s}</option>`).join("")}</select>${state.user.role === "admin" ? `<select id="filter-doctor" aria-label="Filter by doctor"><option value="">All doctors</option>${docs.doctors.map((d) => `<option value="${d.id}">${esc(d.name)}</option>`).join("")}</select>` : ""}<input id="filter-date" type="date" aria-label="Filter by date"><button class="secondary" data-action="clear-filters">Reset filters</button></div><div id="appointment-list"></div></section>` +
    footer();
  await filterAppointments();
}
async function filterAppointments() {
  const query = new URLSearchParams();
  [
    ["status", "#filter-status"],
    ["doctor", "#filter-doctor"],
    ["date", "#filter-date"],
  ].forEach(([key, s]) => {
    if ($(s)?.value) query.set(key, $(s).value);
  });
  const result = await api("/appointments?" + query);
  state.appointments = result.appointments;
  $("#appointment-list").innerHTML = appointmentTable(result.appointments);
}
async function doctors() {
  const result = await api("/doctors");
  state.doctors = result.doctors;
  const admin = state.user.role === "admin";
  $("#content").innerHTML =
    heading(
      admin ? "Your care team" : "Find your doctor",
      admin
        ? "Manage the specialists who make your clinic possible."
        : "Choose a specialist and find a time that works for you.",
      admin
        ? `<button data-action="add-doctor">${icon("plus")}Add doctor</button>`
        : "",
    ) +
    `<div class="grid">${result.doctors.map((d) => `<article class="doctor-card"><div class="avatar">${initials(d.name)}</div><h3>${esc(d.name)}</h3><p>${esc(d.specialty)}</p>${pill(d.active ? "Active" : "Inactive")}<p>${admin ? esc(d.email) : "In-person appointments · 30 minutes"}</p>${admin ? `<div class="actions"><button class="${d.active ? "secondary" : "button"} small" data-action="toggle-doctor" data-id="${d.id}" data-active="${d.active ? 0 : 1}">${d.active ? "Deactivate" : "Reactivate"}</button>${d.active ? `<button class="ghost small" data-action="invite" data-id="${d.id}">Resend invitation</button>` : ""}</div>` : `<button class="secondary" data-action="book" data-id="${d.id}">View available times ${icon("arrow")}</button>`}</article>`).join("")}</div>${!result.doctors.length ? empty("No doctors yet", admin ? "Add your first doctor to open appointments." : "Please check back with the clinic soon.") : ""}` +
    footer();
}
async function booking(uid, aid = null) {
  const doc = state.doctors.find((d) => d.id === uid) || {
    id: uid,
    name:
      state.appointments.find((a) => a.id === aid)?.doctor_name ||
      "Your doctor",
    specialty: "",
  };
  state.booking = { doctor: doc, id: aid, start: null };
  modal(
    aid ? "Reschedule your visit" : "Choose your appointment",
    `<div class="booking-summary"><h3>${esc(doc.name)}</h3><p>${esc(doc.specialty)} · 30-minute clinic appointment</p></div><p class="step">01 / CHOOSE A DATE</p><label for="slot-date">Appointment date</label><input id="slot-date" type="date" min="${state.today}" value="${state.today}"><div id="slot-list"></div><div class="form-actions"><button class="secondary" data-action="close">Cancel</button><button id="book-submit" data-action="book-submit" disabled>${aid ? "Request new time" : "Request appointment"}</button></div>`,
    "All times are shown in Pakistan time.",
  );
  await loadSlots();
}
async function loadSlots() {
  const b = state.booking;
  if (!b) return;
  const dateValue = $("#slot-date").value;
  b.start = null;
  $("#book-submit").disabled = true;
  $("#slot-list").innerHTML =
    '<p class="subtitle">Finding available times…</p>';
  const result = await api(
    `/doctors/${b.doctor.id}/slots?date=${encodeURIComponent(dateValue)}`,
  );
  if (state.booking !== b || $("#slot-date").value !== dateValue) return;
  $("#slot-list").innerHTML = result.slots.length
    ? `<p class="step">02 / PICK A TIME</p><div class="slots">${result.slots.map((s) => `<button class="slot" data-action="slot" data-start="${s}">${time(s)}</button>`).join("")}</div><p class="footnote">Your request holds this slot while the doctor reviews it.</p>`
    : empty(
        "No free slots on this date",
        "Try another date. The doctor may be off or fully booked.",
      );
}
async function detail(aid) {
  const a = (await api("/appointments/" + aid)).appointment;
  const role = state.user.role;
  const active = ["Pending", "Confirmed"].includes(a.status);
  let actions = "";
  if (role === "patient" && active) {
    actions += `<button class="secondary small" data-action="reschedule" data-id="${aid}" data-doctor="${a.doctor_id}">Reschedule</button>`;
  }
  if ((role === "patient" || role === "admin") && active)
    actions += `<button class="danger small" data-action="confirm-cancel" data-id="${aid}">Cancel appointment</button>`;
  if (role === "doctor") {
    if (a.status === "Pending")
      actions += `<button class="small" data-action="status" data-id="${aid}" data-status="Confirmed">Confirm request</button><button class="danger small" data-action="status" data-id="${aid}" data-status="Rejected">Reject</button>`;
    if (a.status === "Confirmed")
      actions += `<button class="small" data-action="finish" data-id="${aid}" data-status="Completed">Mark completed</button><button class="secondary small" data-action="finish" data-id="${aid}" data-status="No-show">Mark no-show</button>`;
    if (["Completed", "No-show"].includes(a.status))
      actions += `<button class="secondary small" data-action="edit-note" data-id="${aid}">Edit visit note</button>`;
    actions += `<button class="secondary small" data-action="history" data-id="${a.patient_id}">Patient history</button>`;
  }
  let note = "";
  if (role !== "admin") {
    note = (await api(`/appointments/${aid}/note`)).note;
  }
  modal(
    "Appointment details",
    `<div class="booking-summary"><div class="person-cell"><span class="avatar">${initials(a.doctor_name)}</span><div><h3>${esc(a.doctor_name)}</h3><p>${esc(a.specialty)}</p></div></div></div><div class="form-grid"><div><p class="eyebrow">PATIENT</p><p>${esc(a.patient_name)}</p></div><div><p class="eyebrow">STATUS</p>${pill(a.status)}</div><div><p class="eyebrow">DATE</p><p>${date(a.start)}</p></div><div><p class="eyebrow">TIME</p><p>${time(a.start)} · 30 minutes</p></div></div>${a.reason ? `<p class="notice">${esc(a.reason)}</p>` : ""}${role !== "admin" ? `<p class="eyebrow">PRIVATE VISIT NOTE</p><div class="note">${esc(note || "No visit note has been added.")}</div>` : ""}${role === "patient" && active ? '<p class="footnote">You can cancel or reschedule at least 2 hours before your visit.</p>' : ""}<div class="form-actions actions">${actions}</div>`,
    "#APT-" + String(aid).padStart(4, "0"),
  );
}
async function availability() {
  const result = await api("/availability");
  $("#content").innerHTML =
    heading(
      "Your availability",
      "Set a predictable schedule. We’ll take care of the slots.",
    ) +
    `<div class="split"><section class="panel"><div class="panel-head"><div><h2>Weekly working hours</h2><p>Each working period becomes 30-minute appointments.</p></div><button class="secondary small" data-action="add-hours">${icon("plus")}Add hours</button></div>${result.hours.length ? `<div class="table-wrap"><table><thead><tr><th>Day</th><th>Working hours</th><th></th></tr></thead><tbody>${result.hours.map((h) => `<tr><td><strong>${weekdays[h.weekday]}</strong></td><td>${h.start} – ${h.end}</td><td><button class="ghost small" data-action="delete-hours" data-id="${h.id}">Remove</button></td></tr>`).join("")}</tbody></table></div>` : empty("No working hours yet", "Add your first working period to start receiving appointments.")}</section><aside><section class="panel"><div class="panel-head"><h2>Leave days</h2>${icon("calendar")}</div><div class="panel-body"><p class="subtitle">Adding leave cancels Pending and Confirmed appointments for that date and queues a patient email.</p><button class="secondary small" data-action="add-leave">${icon("plus")}Add leave day</button>${result.leaves.map((l) => `<div class="doctor-row"><strong>${date(l.date)}</strong><button class="ghost small" data-action="delete-leave" data-id="${l.id}">Remove</button></div>`).join("")}</div></section><p class="footnote">Removing a leave day reopens availability. Cancelled appointments remain cancelled.</p></aside></div>` +
    footer();
}
async function patients() {
  const result = await api("/patients");
  $("#content").innerHTML =
    heading(
      "Patients",
      state.user.role === "doctor"
        ? "Your patients and the care you’ve provided."
        : "Your clinic community, in one place.",
    ) +
    `<section class="panel"><div class="filters"><input id="patient-search" type="search" placeholder="Search name, email, or phone…" aria-label="Search patients"><button class="secondary" data-action="search-patients">Search</button></div><div id="patient-list"></div></section>` +
    footer();
  patientTable(result.patients);
}
function patientTable(rows) {
  $("#patient-list").innerHTML = rows.length
    ? `<div class="table-wrap"><table><thead><tr><th>Patient</th><th>Email</th><th>Phone</th><th></th></tr></thead><tbody>${rows.map((p) => `<tr><td><div class="person-cell"><span class="avatar">${initials(p.name)}</span><strong>${esc(p.name)}</strong></div></td><td>${esc(p.email)}</td><td>${esc(p.phone)}</td><td>${state.user.role === "doctor" ? `<button class="secondary small" data-action="history" data-id="${p.id}">View history</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`
    : empty(
        "No patients found",
        "Try a different search or check back after a booking.",
      );
}
async function history(pid) {
  const result = await api(`/patients/${pid}/history`);
  modal(
    "Patient history",
    result.history
      .map(
        (a) =>
          `<article class="timeline-item"><div class="person-cell"><strong>${date(a.start)} · ${time(a.start)}</strong>${pill(a.status)}</div><p>${esc(a.note || "No visit note.")}</p></article>`,
      )
      .join(""),
    "Only this patient’s appointments with you are shown.",
  );
}
function doctorForm() {
  modal(
    "Add a doctor",
    `<form data-form="doctor"><div class="field"><label for="doctor-name">Full name</label><input id="doctor-name" name="name" placeholder="Dr. Full Name" maxlength="100" required></div><div class="field"><label for="specialty">Specialty</label><input id="specialty" name="specialty" placeholder="e.g. Family Medicine" maxlength="100" required></div><div class="field"><label for="doctor-email">Email address</label><input id="doctor-email" type="email" name="email" maxlength="254" placeholder="doctor@example.com" required></div><p class="notice">A single-use password invitation will be queued for this email. The link expires after 24 hours.</p><div class="form-actions"><button type="button" class="secondary" data-action="close">Cancel</button><button type="submit">Create doctor & invite</button></div></form>`,
  );
}
function hoursForm() {
  modal(
    "Add working hours",
    `<form data-form="hours"><div class="field"><label for="weekday">Day of the week</label><select id="weekday" name="weekday">${weekdays.map((d, i) => `<option value="${i}">${d}</option>`).join("")}</select></div><div class="form-grid"><div><label for="start">Start time</label><input id="start" type="time" name="start" value="09:00" step="1800" required></div><div><label for="end">End time</label><input id="end" type="time" name="end" value="13:00" step="1800" required></div></div><p class="footnote">Use :00 or :30 times. Working periods cannot overlap.</p><div class="form-actions"><button type="submit">Save working hours</button></div></form>`,
  );
}
async function finishForm(id, status) {
  modal(
    status === "Completed" ? "Complete the visit" : "Mark as no-show",
    `<form data-form="finish" data-id="${id}" data-status="${status}"><div class="field"><label for="note">Visit note (optional)</label><textarea id="note" name="note" maxlength="2000" placeholder="Add a short note about this visit…"></textarea></div><p class="footnote">Only you and this patient can read this note. This action is allowed only after the appointment starts.</p><div class="form-actions"><button type="submit">Save as ${status.toLowerCase()}</button></div></form>`,
  );
}
async function editNote(id) {
  const result = await api(`/appointments/${id}/note`);
  modal(
    "Edit visit note",
    `<form data-form="note" data-id="${id}"><label for="note">Private visit note</label><textarea id="note" name="note" maxlength="2000">${esc(result.note)}</textarea><div class="form-actions"><button type="submit">Save note</button></div></form>`,
  );
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = Number(button.dataset.id);
  try {
    if (action === "auth-switch") {
      state.auth = state.auth === "login" ? "register" : "login";
      auth();
    } else if (action === "nav") {
      state.page = button.dataset.page;
      await session();
      await render();
    } else if (action === "menu") {
      $(".sidebar").classList.toggle("open");
    } else if (action === "refresh") {
      await session();
      await render();
    } else if (action === "logout") {
      await api("/logout", "POST", {});
      await session();
      state.page = "dashboard";
      auth();
    } else if (action === "close") closeModal();
    else if (action === "book") await booking(id);
    else if (action === "slot") {
      state.booking.start = button.dataset.start;
      document
        .querySelectorAll(".slot")
        .forEach((el) => el.classList.toggle("selected", el === button));
      $("#book-submit").disabled = false;
    } else if (action === "book-submit") {
      button.disabled = true;
      try {
        const b = state.booking;
        await api(
          b.id ? `/appointments/${b.id}/reschedule` : "/appointments",
          "POST",
          b.id
            ? { start: b.start }
            : { doctor_id: b.doctor.id, start: b.start },
        );
        closeModal();
        toast(
          "Appointment requested. Your slot is held while the doctor reviews it.",
        );
        state.page = "appointments";
        await render();
      } catch (e) {
        button.disabled = false;
        throw e;
      }
    } else if (action === "detail") await detail(id);
    else if (action === "reschedule")
      await booking(Number(button.dataset.doctor), id);
    else if (action === "status") {
      button.disabled = true;
      await api(`/appointments/${id}/status`, "POST", {
        status: button.dataset.status,
      });
      closeModal();
      toast("Appointment updated.");
      await render();
    } else if (action === "confirm-cancel") {
      modal(
        "Cancel this appointment?",
        `<p>The slot will be released and a cancellation email will be queued for the patient.</p><div class="form-actions"><button class="secondary" data-action="close">Keep appointment</button><button class="danger" data-action="status" data-id="${id}" data-status="Cancelled">Yes, cancel appointment</button></div>`,
      );
    } else if (action === "finish") await finishForm(id, button.dataset.status);
    else if (action === "edit-note") await editNote(id);
    else if (action === "history") await history(id);
    else if (action === "add-doctor") doctorForm();
    else if (action === "toggle-doctor") {
      const active = button.dataset.active === "1";
      modal(
        active ? "Reactivate doctor?" : "Deactivate doctor?",
        `<p>${active ? "Patients will be able to book this doctor again." : "Future Pending and Confirmed appointments will be cancelled and patient emails queued. The doctor will no longer be able to sign in."}</p><div class="form-actions"><button class="secondary" data-action="close">Go back</button><button data-action="save-doctor-active" data-id="${id}" data-active="${active ? 1 : 0}">Confirm</button></div>`,
      );
    } else if (action === "save-doctor-active") {
      await api("/doctors/" + id, "PATCH", {
        active: button.dataset.active === "1",
      });
      closeModal();
      toast("Doctor updated.");
      await render();
    } else if (action === "invite") {
      await api(`/doctors/${id}/invite`, "POST", {});
      toast("Password invitation queued.");
    } else if (action === "add-hours") hoursForm();
    else if (action === "delete-hours") {
      await api("/availability/" + id, "DELETE", {});
      toast("Working period removed.");
      await render();
    } else if (action === "add-leave") {
      modal(
        "Add a leave day",
        `<form data-form="leave"><label for="leave-date">Date</label><input id="leave-date" name="date" type="date" min="${state.today}" required><p class="notice">All Pending and Confirmed appointments on this date will be cancelled and patients notified.</p><div class="form-actions"><button class="danger" type="submit">Add leave & cancel affected visits</button></div></form>`,
      );
    } else if (action === "delete-leave") {
      await api("/leaves/" + id, "DELETE", {});
      toast("Leave day removed.");
      await render();
    } else if (action === "clear-filters") {
      ["#filter-status", "#filter-doctor", "#filter-date"].forEach((s) => {
        if ($(s)) $(s).value = "";
      });
      await filterAppointments();
    } else if (action === "search-patients") {
      patientTable(
        (
          await api(
            "/patients?q=" + encodeURIComponent($("#patient-search").value),
          )
        ).patients,
      );
    }
  } catch (e) {
    button.disabled = false;
    toast(e.message, true);
  }
});
document.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(form));
  const submit = form.querySelector("[type=submit]");
  submit.disabled = true;
  try {
    const kind = form.dataset.form;
    if (["login", "register"].includes(kind)) {
      await api("/" + kind, "POST", payload);
      await session();
      state.page = "dashboard";
      await render();
    } else if (kind === "set-password") {
      payload.token = location.hash.slice("#invite=".length);
      await api("/set-password", "POST", payload);
      location.hash = "";
      state.auth = "login";
      auth();
      toast("Password set. You can now sign in.");
    } else {
      if (kind === "doctor") await api("/doctors", "POST", payload);
      else if (kind === "hours")
        await api("/availability", "POST", {
          ...payload,
          weekday: Number(payload.weekday),
        });
      else if (kind === "leave") await api("/leaves", "POST", payload);
      else if (kind === "finish")
        await api(`/appointments/${form.dataset.id}/status`, "POST", {
          ...payload,
          status: form.dataset.status,
        });
      else if (kind === "note")
        await api(`/appointments/${form.dataset.id}/note`, "PUT", payload);
      closeModal();
      toast("Saved successfully.");
      await render();
    }
  } catch (e) {
    const err = form.querySelector("#form-error");
    if (err) {
      err.className = "notice error";
      err.textContent = e.message;
    } else toast(e.message, true);
  } finally {
    submit.disabled = false;
  }
});
document.addEventListener("change", async (event) => {
  try {
    if (event.target.id === "slot-date") await loadSlots();
    if (event.target.id.startsWith("filter-")) await filterAppointments();
  } catch (e) {
    toast(e.message, true);
  }
});
document.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && event.target.id === "patient-search") {
    event.preventDefault();
    try {
      patientTable(
        (await api("/patients?q=" + encodeURIComponent(event.target.value)))
          .patients,
      );
    } catch (e) {
      toast(e.message, true);
    }
  }
});
window.addEventListener("hashchange", () => {
  if (location.hash.startsWith("#invite=")) auth();
});
(async () => {
  try {
    await session();
    if (state.user && !location.hash.startsWith("#invite=")) await render();
    else auth();
  } catch (e) {
    $("#root").innerHTML = empty("Unable to connect", e.message);
  }
})();
