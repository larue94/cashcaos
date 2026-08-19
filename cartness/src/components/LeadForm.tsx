import { useId, useState } from "react";
import { isValidEmail, saveLead, type LeadSource } from "../lib/firebase";

type Props = {
  source: LeadSource;
  tier?: string | null;
  /** Inverted styling for the dark final-CTA band. */
  invert?: boolean;
  /** Rendered as a full-width stacked form inside the pricing modal. */
  stacked?: boolean;
  autoFocus?: boolean;
};

const CTA_LABEL = "Get my free agent scan";
const PRIVACY_NOTE = "No spam, no list-selling. One email when your scan is ready.";
const SUCCESS_BODY =
  "We onboard founding users in small batches — you'll get an email with your scan instructions within two weeks, and your first scan is free.";

export function LeadForm({
  source,
  tier = null,
  invert = false,
  stacked = false,
  autoFocus = false,
}: Props) {
  const emailId = useId();
  const honeypotId = useId();
  const [email, setEmail] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === "sending") return;

    // Honeypot: a real visitor never sees this field. Bots that fill it get a
    // success state and nothing is written.
    if (honeypot.trim() !== "") {
      setStatus("done");
      return;
    }

    if (!isValidEmail(email)) {
      setError("Enter a valid email address so we can send your scan.");
      setStatus("error");
      return;
    }

    setStatus("sending");
    setError("");

    try {
      await saveLead({ email, source, tier });
      setStatus("done");
    } catch (submitError) {
      console.error("Lead capture failed", submitError);
      setError("Something went wrong on our end. Try again in a moment.");
      setStatus("error");
    }
  }

  if (status === "done") {
    return (
      <div
        className={`leadform__success${invert ? " leadform--invert" : ""}`}
        role="status"
      >
        <p className="leadform__success-title">You&rsquo;re in.</p>
        <p>{SUCCESS_BODY}</p>
      </div>
    );
  }

  return (
    <form
      className={invert ? "leadform leadform--invert" : "leadform"}
      onSubmit={handleSubmit}
      noValidate
    >
      <label className="visually-hidden" htmlFor={emailId}>
        Work email
      </label>
      <div className="leadform__row" style={stacked ? { flexDirection: "column" } : undefined}>
        <input
          id={emailId}
          className="leadform__input"
          type="email"
          name="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@yourstore.com"
          value={email}
          autoFocus={autoFocus}
          onChange={(event) => {
            setEmail(event.target.value);
            if (status === "error") setStatus("idle");
          }}
          aria-invalid={status === "error"}
          required
        />
        <button className="btn btn--primary" type="submit" disabled={status === "sending"}>
          {status === "sending" ? "Saving…" : CTA_LABEL}
        </button>
      </div>

      {/* Honeypot — visually hidden, never announced, never tabbed to. */}
      <div className="visually-hidden" aria-hidden="true">
        <label htmlFor={honeypotId}>Company</label>
        <input
          id={honeypotId}
          type="text"
          name="company"
          tabIndex={-1}
          autoComplete="off"
          value={honeypot}
          onChange={(event) => setHoneypot(event.target.value)}
        />
      </div>

      {status === "error" && error ? (
        <p className="leadform__error" role="alert">
          {error}
        </p>
      ) : (
        <p className="leadform__note">{PRIVACY_NOTE}</p>
      )}
    </form>
  );
}

export { CTA_LABEL };
