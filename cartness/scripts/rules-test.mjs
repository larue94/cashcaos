/**
 * Isolated security-rules tests for firestore.rules.
 *
 * Each case differs from a known-good lead by exactly one field, so a denial
 * can only be attributed to the rule under test. Run with the Firestore
 * emulator up:  npx firebase emulators:start --only firestore
 */
import { readFileSync } from "node:fs";
import {
  initializeTestEnvironment,
  assertSucceeds,
  assertFails,
} from "@firebase/rules-unit-testing";
import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  serverTimestamp,
  setDoc,
  updateDoc,
} from "firebase/firestore";

const env = await initializeTestEnvironment({
  projectId: "cartness-rules",
  firestore: {
    host: "127.0.0.1",
    port: 8080,
    rules: readFileSync("firestore.rules", "utf8"),
  },
});

const db = env.unauthenticatedContext().firestore();
const leads = collection(db, "leads");

const goodLead = () => ({
  email: "ops@plusstore.example",
  createdAt: serverTimestamp(),
  source: "hero",
  tier: null,
});

const results = [];
async function it(name, fn) {
  try {
    await fn();
    results.push(["PASS", name]);
  } catch (error) {
    results.push(["FAIL", `${name} — ${error.message.split("\n")[0]}`]);
  }
}

// ---------------------------------------------------------------- creates
await it("a visitor can create a valid lead", () => assertSucceeds(addDoc(leads, goodLead())));

await it("a valid lead carrying a pricing tier is accepted", () =>
  assertSucceeds(addDoc(leads, { ...goodLead(), source: "pricing", tier: "Monitor" })));

await it("an email with no @ is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: "opsplusstore.example" })));

await it("an email with no dot in the domain is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: "ops@plusstore" })));

await it("an email with whitespace is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: "ops @plusstore.example" })));

await it("a too-short email is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: "a@b.c" })));

await it("a non-string email is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: 42 })));

await it("an oversized email is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), email: `${"a".repeat(250)}@b.example` })));

await it("an extra field is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), payload: "injected" })));

await it("a missing source is rejected", () => {
  const { source: _source, ...withoutSource } = goodLead();
  return assertFails(addDoc(leads, withoutSource));
});

await it("an empty source is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), source: "" })));

await it("an oversized source is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), source: "x".repeat(41) })));

await it("a non-string tier is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), tier: 7 })));

await it("a client-chosen timestamp is rejected", () =>
  assertFails(addDoc(leads, { ...goodLead(), createdAt: new Date(2020, 0, 1) })));

// ------------------------------------------------- read / update / delete
const seeded = "seeded-lead";
await env.withSecurityRulesDisabled(async (ctx) => {
  await setDoc(doc(ctx.firestore(), "leads", seeded), {
    email: "seed@store.example",
    createdAt: new Date(),
    source: "hero",
    tier: null,
  });
});

await it("a visitor cannot list leads", () => assertFails(getDocs(leads)));

await it("a visitor cannot read one lead", () =>
  assertFails(getDoc(doc(db, "leads", seeded))));

await it("a visitor cannot update a lead", () =>
  assertFails(updateDoc(doc(db, "leads", seeded), { email: "hacked@evil.example" })));

await it("a visitor cannot delete a lead", () =>
  assertFails(deleteDoc(doc(db, "leads", seeded))));

// --------------------------------------------------------- other paths
await it("a visitor cannot write to any other collection", () =>
  assertFails(addDoc(collection(db, "anything"), { x: "y" })));

await it("a visitor cannot read any other collection", () =>
  assertFails(getDocs(collection(db, "anything"))));

await env.cleanup();

const failed = results.filter(([r]) => r === "FAIL");
results.forEach(([r, n]) => console.log(`  ${r} ${n}`));
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`);
process.exit(failed.length ? 1 : 0);
