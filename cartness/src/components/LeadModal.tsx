import { useEffect, useRef } from "react";
import { LeadForm } from "./LeadForm";
import { IconClose } from "./Icons";
import type { LeadSource } from "../lib/firebase";

export type ModalRequest = {
  source: LeadSource;
  tier?: string | null;
} | null;

type Props = {
  request: ModalRequest;
  onClose: () => void;
};

export function LeadModal({ request, onClose }: Props) {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!request) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [request, onClose]);

  if (!request) return null;

  const heading = request.tier
    ? `Claim your free scan — ${request.tier}`
    : "Claim your free agent scan";

  return (
    <div
      className="modal"
      role="dialog"
      aria-modal="true"
      aria-label={heading}
      onMouseDown={(event) => {
        if (!cardRef.current?.contains(event.target as Node)) onClose();
      }}
    >
      <div className="modal__scrim" />
      <div className="modal__card" ref={cardRef}>
        <div className="modal__head">
          <h3>{heading}</h3>
          <button className="modal__close" type="button" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>
        <p className="modal__lede">
          Founding users get early access and their first Agent Readiness Scan free — a full
          readiness score and fix list for one store. No card, no store access required.
        </p>
        <LeadForm source={request.source} tier={request.tier ?? null} stacked autoFocus />
      </div>
    </div>
  );
}
