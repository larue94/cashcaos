/**
 * End-to-end lead-capture test.
 * Drives the real page in Chromium against a live Firestore emulator running
 * firestore.rules, then reads the stored documents back over the emulator's
 * REST API (which bypasses rules, exactly as the Firebase console does).
 */
import { chromium } from "playwright";

const APP = "http://localhost:4174/";
const PROJECT = "cartness-demo";
const EMU = "http://127.0.0.1:8080";
const DOCS = `${EMU}/v1/projects/${PROJECT}/databases/(default)/documents/leads`;

const pass = [];
const fail = [];
const check = (name, ok, detail = "") =>
  (ok ? pass : fail).push(`${name}${detail ? ` — ${detail}` : ""}`);

// The emulator enforces firestore.rules on plain REST calls; the "owner"
// bearer token is the admin bypass, i.e. what the Firebase console uses.
const ADMIN = { headers: { Authorization: "Bearer owner" } };

async function readLeads() {
  const res = await fetch(DOCS, ADMIN);
  if (res.status === 404) return [];
  const json = await res.json();
  if (json.error) throw new Error("admin read failed: " + JSON.stringify(json.error));
  return (json.documents ?? []).map((d) => ({
    id: d.name.split("/").pop(),
    email: d.fields.email?.stringValue ?? null,
    source: d.fields.source?.stringValue ?? null,
    tier: "nullValue" in (d.fields.tier ?? {}) ? null : (d.fields.tier?.stringValue ?? null),
    createdAt: d.fields.createdAt?.timestampValue ?? null,
  }));
}

async function wipe() {
  for (const lead of await readLeads()) {
    await fetch(`${DOCS}/${lead.id}`, { method: "DELETE", ...ADMIN });
  }
}

const browser = await chromium.launch({
  executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on("console", (m) => {
  if (m.type() === "error") console.log("  [browser error]", m.text());
});

await wipe();
await page.goto(APP, { waitUntil: "networkidle" });

const SUCCESS =
  "We onboard founding users in small batches — you'll get an email with your scan instructions within two weeks, and your first scan is free.";

// ---------------------------------------------------------------- 1. hero
await page.locator(".hero__form input[type=email]").fill("ops@trailhead.example");
await page.locator(".hero__form button[type=submit]").click();
await page.locator(".hero__form .leadform__success").waitFor({ timeout: 15000 });
check(
  "hero form shows the success state verbatim",
  (await page.locator(".hero__form .leadform__success").innerText()).includes(SUCCESS),
);

// ------------------------------------------------------- 2. invalid email
await page.reload({ waitUntil: "networkidle" });
await page.locator(".hero__form input[type=email]").fill("not-an-email");
await page.locator(".hero__form button[type=submit]").click();
await page.waitForTimeout(400);
check(
  "invalid email is rejected client-side",
  await page.locator(".hero__form .leadform__error").isVisible(),
);

// ------------------------------------------------------------ 3. honeypot
await page.reload({ waitUntil: "networkidle" });
await page.locator(".demo__capture input[type=email]").fill("bot@spam.example");
await page.locator('.demo__capture input[name="company"]').fill("Acme Bots Inc");
await page.locator(".demo__capture button[type=submit]").click();
await page.locator(".demo__capture .leadform__success").waitFor({ timeout: 10000 });
check("honeypot submission still shows success (silent drop)", true);

// ------------------------------------------- 4. demo-band capture (genuine)
await page.reload({ waitUntil: "networkidle" });
await page.locator(".demo__capture input[type=email]").fill("lead@demoband.example");
await page.locator(".demo__capture button[type=submit]").click();
await page.locator(".demo__capture .leadform__success").waitFor({ timeout: 15000 });
check("demo-band form captures", true);

// ------------------------------------------------- 5. pricing tier → modal
await page.reload({ waitUntil: "networkidle" });
await page.locator('#pricing .tier--recommended button.btn').click();
await page.locator(".modal__card").waitFor();
await page.locator(".modal__card input[type=email]").fill("cro@plusstore.example");
await page.locator(".modal__card button[type=submit]").click();
await page.locator(".modal__card .leadform__success").waitFor({ timeout: 15000 });
check("pricing tier button opens the capture form and submits", true);

// ------------------------------------------------------------- 5. final CTA
await page.reload({ waitUntil: "networkidle" });
await page.locator("#signup input[type=email]").fill("Founder@Agency.Example");
await page.locator("#signup button[type=submit]").click();
await page.locator("#signup .leadform__success").waitFor({ timeout: 15000 });
check("final CTA band captures", true);

// ---------------------------------------------------------- stored records
const leads = await readLeads();
console.log("\n--- leads collection contents ---");
console.table(leads);

check("stored exactly the 4 non-bot submissions", leads.length === 4, `got ${leads.length}`);
check(
  "honeypot lead was never written",
  !leads.some((l) => l.email === "bot@spam.example"),
);
check(
  "email is normalised to lowercase",
  leads.some((l) => l.email === "founder@agency.example"),
);
check(
  "source recorded for every lead",
  leads.every((l) => l.source),
  leads.map((l) => l.source).join(", "),
);
check(
  "pricing tier recorded only for the tier click",
  leads.filter((l) => l.tier === "Monitor").length === 1 &&
    leads.filter((l) => l.tier === null).length === 3,
);
check("server timestamp set on every lead", leads.every((l) => l.createdAt));

// ------------------------------------------------ security rules, enforced
// These calls carry no admin token, so the emulator applies firestore.rules
// exactly as it would for a visitor's browser.
const target = `${DOCS}/${leads[0].id}`;

const readRes = await fetch(DOCS);
check("public READ of leads is denied", readRes.status === 403, `HTTP ${readRes.status}`);

const getRes = await fetch(target);
check("public GET of one lead is denied", getRes.status === 403, `HTTP ${getRes.status}`);

const updateRes = await fetch(target, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ fields: { email: { stringValue: "hacked@evil.example" } } }),
});
check("public UPDATE of a lead is denied", updateRes.status === 403, `HTTP ${updateRes.status}`);

const deleteRes = await fetch(target, { method: "DELETE" });
check("public DELETE of a lead is denied", deleteRes.status === 403, `HTTP ${deleteRes.status}`);

const badEmail = await fetch(DOCS, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    fields: {
      email: { stringValue: "garbage" },
      source: { stringValue: "hero" },
      tier: { nullValue: null },
      createdAt: { timestampValue: new Date().toISOString() },
    },
  }),
});
check("CREATE with a malformed email is denied", badEmail.status === 403, `HTTP ${badEmail.status}`);

const extraField = await fetch(DOCS, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    fields: {
      email: { stringValue: "ok@store.example" },
      source: { stringValue: "hero" },
      tier: { nullValue: null },
      createdAt: { timestampValue: new Date().toISOString() },
      injected: { stringValue: "payload" },
    },
  }),
});
check("CREATE with an unexpected field is denied", extraField.status === 403, `HTTP ${extraField.status}`);

const otherCollection = await fetch(
  `${EMU}/v1/projects/${PROJECT}/databases/(default)/documents/anything`,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields: { x: { stringValue: "y" } } }),
  },
);
check("writes to any other collection are denied", otherCollection.status === 403, `HTTP ${otherCollection.status}`);

await browser.close();

console.log("\n--- results ---");
pass.forEach((p) => console.log("  PASS", p));
fail.forEach((f) => console.log("  FAIL", f));
console.log(`\n${pass.length} passed, ${fail.length} failed`);
process.exit(fail.length ? 1 : 0);
