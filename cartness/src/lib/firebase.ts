import type { Firestore } from "firebase/firestore";

/**
 * Firestore lead capture.
 *
 * Config comes from the Firebase integration's environment variables — no
 * hand-rolled backend, no keys in source. Visitors never sign in: the form is
 * email-only and writes a single `leads` document per submission. Reads,
 * updates and deletes are denied to the public site by firestore.rules.
 */

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const isFirebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId,
);

let db: Firestore | null = null;

/**
 * The Firebase SDK is loaded on first submit rather than at page load, so the
 * landing page paints without waiting on ~200 kB of vendor JavaScript.
 */
async function getDb(): Promise<Firestore | null> {
  if (!isFirebaseConfigured) return null;
  if (db) return db;

  const [{ initializeApp, getApps }, { getFirestore }] = await Promise.all([
    import("firebase/app"),
    import("firebase/firestore"),
  ]);

  const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  db = getFirestore(app);

  // Local rules/capture testing against the Firestore emulator. Unset in
  // production, where this branch never runs.
  const emulator = import.meta.env.VITE_FIREBASE_EMULATOR_HOST;
  if (emulator) {
    const { connectFirestoreEmulator } = await import("firebase/firestore");
    const [host, port] = emulator.split(":");
    connectFirestoreEmulator(db, host, Number(port));
  }

  return db;
}

/** Which CTA on the page produced the lead. */
export type LeadSource =
  | "nav"
  | "hero"
  | "demo"
  | "pricing"
  | "final-cta";

export type LeadInput = {
  email: string;
  source: LeadSource;
  /** Set only when the visitor clicked a pricing tier button. */
  tier?: string | null;
};

export const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function isValidEmail(email: string): boolean {
  const trimmed = email.trim();
  return (
    trimmed.length >= 6 && trimmed.length <= 254 && EMAIL_PATTERN.test(trimmed)
  );
}

/**
 * Writes one lead. Fields match firestore.rules exactly — adding a field here
 * without adding it there will be rejected by the security rules.
 */
export async function saveLead({ email, source, tier }: LeadInput): Promise<void> {
  const database = await getDb();

  if (!database) {
    // Firebase not yet provisioned (local dev before the integration is
    // enabled). Fail loudly in the console, never silently to the visitor.
    throw new Error(
      "Firebase is not configured. Enable the Firebase integration so VITE_FIREBASE_* is set.",
    );
  }

  const { addDoc, collection, serverTimestamp } = await import("firebase/firestore");

  await addDoc(collection(database, "leads"), {
    email: email.trim().toLowerCase(),
    createdAt: serverTimestamp(),
    source,
    tier: tier ?? null,
  });
}
