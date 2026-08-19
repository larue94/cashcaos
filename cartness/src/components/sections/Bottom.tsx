import { useState } from "react";
import { LeadForm, CTA_LABEL } from "../LeadForm";
import { Logo } from "../Logo";
import { useReveal } from "../../hooks/useReveal";
import {
  IconCheck,
  IconChecklist,
  IconChevron,
  IconGauge,
  IconScan,
  IconShareDoc,
  IconTrendUp,
  IconWrench,
} from "../Icons";
import type { ModalRequest } from "../LeadModal";

type OpenModal = (request: NonNullable<ModalRequest>) => void;

/* ------------------------------------------------------------------
   DEMO MOMENT — surface band, two bordered cards side by side.
   Worked example, verbatim.
   ------------------------------------------------------------------ */

const AGENT_INPUT = [
  { key: "Product", value: "Trailhead Insulated Bottle" },
  { key: "Price", value: '"$34.00  $28.90  SAVE!"' },
  { key: "Variants", value: "21 oz / 32oz / Thirty-Two Ounce (Steel)" },
  { key: "Inventory", value: '"Only a few left!" · stock: 14 · available' },
  { key: "Shipping", value: '"Free over $50 (US only — see banner)"' },
  {
    key: "Promo",
    value:
      '"Use WELCOME15 at checkout (new customers, one per order, excludes sale items)"',
  },
];

const FINDINGS = [
  {
    severity: "BLOCKER",
    tone: "blocker",
    title: "Ambiguous price.",
    body: "The agent reads two prices ($34.00 and $28.90) with no markup separating sale price from compare-at price.",
    fix: "expose the sale price in offers.price and move compare-at into priceSpecification.",
  },
  {
    severity: "BLOCKER",
    tone: "blocker",
    title: "Coupon rule in prose.",
    body: '"Excludes sale items" is not machine-readable. The agent applied WELCOME15, got a silent rejection, and abandoned.',
    fix: "return an explicit eligibility error code at cart validation.",
  },
  {
    severity: "HIGH",
    tone: "high",
    title: "Variant mismatch.",
    body: '"32oz" and "Thirty-Two Ounce (Steel)" parse as different products.',
    fix: "normalize variant option values to one format.",
  },
  {
    severity: "MEDIUM",
    tone: "medium",
    title: 'Inventory reads three ways ("Only a few left!", stock: 14, available).',
    body: "",
    fix: "publish one numeric inventory field.",
  },
];

export function DemoMoment() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section section--surface" id="demo" ref={ref}>
      <div className="container">
        <p className="demo__intro reveal">
          Here&rsquo;s what a report looks like for a typical product page.
        </p>

        <div className="demo__grid">
          {/* ---------- input ---------- */}
          <article
            className="panel reveal"
            style={{ "--i": 0 } as React.CSSProperties}
          >
            <div className="panel__head">
              <h3 className="panel__title">What the agent reads</h3>
              <span className="panel__tag">input</span>
            </div>
            <div className="panel__body panel__body--data">
              {AGENT_INPUT.map((row) => (
                <div className="datarow" key={row.key}>
                  <span className="datarow__key">{row.key}:</span>
                  <span className="datarow__value">{row.value}</span>
                </div>
              ))}
            </div>
          </article>

          {/* ---------- output ---------- */}
          <article
            className="panel reveal"
            style={{ "--i": 1 } as React.CSSProperties}
          >
            <div className="panel__head">
              <h3 className="panel__title">Agent Readiness Report</h3>
              <span className="panel__tag">output</span>
            </div>
            <div className="panel__body">
              <p className="report__score-label">Readiness score</p>
              <div className="report__score">
                <span className="report__score-number">58</span>
                <span className="report__score-total">/ 100</span>
              </div>
              <p className="report__verdict">Agent abandoned cart at the coupon step.</p>

              <div className="report__findings">
                {FINDINGS.map((finding) => (
                  <div className="finding" key={finding.title}>
                    <div className="finding__head">
                      <span className={`tag tag--${finding.tone}`}>{finding.severity}</span>
                      <h4 className="finding__title">{finding.title}</h4>
                    </div>
                    {finding.body ? <p className="finding__body">{finding.body}</p> : null}
                    <p className="finding__fix">
                      <span>Fix:</span> {finding.fix}
                    </p>
                  </div>
                ))}
              </div>

              <p className="report__footer">
                <strong>IF FIXED:</strong> Simulated agent completes purchase in 4 steps.
              </p>
            </div>
          </article>
        </div>

        {/* Email capture, directly below the demo moment. */}
        <div className="demo__capture">
          <div>
            <h3>Get this report for your own store, free.</h3>
            <p className="section__lede small">
              Founding users get early access and their first Agent Readiness Scan free — a
              full readiness score and fix list for one store.
            </p>
          </div>
          <LeadForm source="demo" />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   BENEFITS — background token, 6 bordered white cards, 3-col grid.
   ------------------------------------------------------------------ */

const BENEFITS = [
  {
    Icon: IconScan,
    title: "Find the breaks before agents do.",
    body: "Every ambiguity gets flagged before it costs a checkout.",
  },
  {
    Icon: IconGauge,
    title: "A score you can put in a deck.",
    body: "One number tells leadership exactly how agent-ready the store is.",
  },
  {
    Icon: IconWrench,
    title: "Fixes, not vague warnings.",
    body: "Every flag comes with the specific change your developers need to make.",
  },
  {
    Icon: IconChecklist,
    title: "Five scenarios, not one happy path.",
    body: "Coupons, multi-item carts, subscriptions, and international orders all get tested.",
  },
  {
    Icon: IconTrendUp,
    title: "Watch the score climb.",
    body: "Re-run after each fix and show measurable progress week over week.",
  },
  {
    Icon: IconShareDoc,
    title: "Reports your clients can read.",
    body: "Agencies get a clean, shareable report page to hand to every client.",
  },
];

export function Benefits() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section section--background" id="benefits" ref={ref}>
      <div className="container">
        <div className="section__head">
          <p className="eyebrow">Benefits</p>
          <h2 className="reveal">Why ops teams run the scan first</h2>
        </div>

        <ul className="benefits__grid">
          {BENEFITS.map(({ Icon, title, body }, index) => (
            <li
              className="benefit reveal"
              key={title}
              style={{ "--i": index % 3 } as React.CSSProperties}
            >
              <span className="benefit__icon">
                <Icon />
              </span>
              <h3 className="benefit__title">{title}</h3>
              <p className="benefit__body">{body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   PRICING — surface band, 3 bordered cards. Recommended tier gets a
   2px accent border and a small accent badge.
   ------------------------------------------------------------------ */

const TIERS = [
  {
    name: "Audit",
    price: "$199/mo",
    bestFor: "A single Shopify Plus store getting agent-ready.",
    features: [
      "1 store",
      "10 scans per month",
      "All 5 purchase scenarios",
      "Email support",
    ],
    recommended: false,
  },
  {
    name: "Monitor",
    price: "$499/mo",
    bestFor: "Ops teams with catalogs that change weekly.",
    features: [
      "Up to 3 stores",
      "Unlimited scans",
      "Full report history and score tracking",
      "Priority support",
    ],
    recommended: true,
  },
  {
    name: "Agency",
    price: "$999/mo",
    bestFor: "Agencies running CRO for multiple clients.",
    features: [
      "Up to 10 stores",
      "Unlimited scans",
      "Client-shareable report pages",
      "Dedicated support",
    ],
    recommended: false,
  },
];

export function Pricing({ onOpen }: { onOpen: OpenModal }) {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section section--surface" id="pricing" ref={ref}>
      <div className="container">
        <div className="section__head">
          <p className="eyebrow">Pricing</p>
          <h2 className="reveal">One recovered checkout pays for it</h2>
        </div>

        <div className="pricing__grid">
          {TIERS.map((tier, index) => (
            <article
              className={`tier reveal${tier.recommended ? " tier--recommended" : ""}`}
              key={tier.name}
              style={{ "--i": index } as React.CSSProperties}
            >
              {tier.recommended ? <span className="tier__badge">Recommended</span> : null}

              <div>
                <div className="tier__head">
                  <h3>{tier.name}</h3>
                  <span className="tier__price">{tier.price}</span>
                </div>
                <p className="tier__best-for">Best for: {tier.bestFor}</p>
              </div>

              <ul className="tier__features">
                {tier.features.map((feature) => (
                  <li className="tier__feature" key={feature}>
                    <IconCheck />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                className={`btn btn--block ${tier.recommended ? "btn--primary" : "btn--secondary"}`}
                type="button"
                onClick={() => onOpen({ source: "pricing", tier: tier.name })}
              >
                {CTA_LABEL}
              </button>
            </article>
          ))}
        </div>

        <p className="pricing__note">
          Cartness is in early access — tier buttons register your interest and your free
          founding-user scan. No card required.
        </p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   FAQ — background token, single-column accordions, 1px borders.
   ------------------------------------------------------------------ */

const FAQS = [
  {
    q: "Is Cartness available today?",
    a: "We’re in early access. Sign up now and you’ll be a founding user: you get first access at launch and your first Agent Readiness Scan free. We’re onboarding stores in small batches so every report gets real attention.",
  },
  {
    q: "Are AI agents actually buying anything yet?",
    a: "Shopify is shipping agent-checkout infrastructure right now — UCP and Instant Checkout are live initiatives. Agent traffic is small today and growing; the stores that pass the read collect the sales the others drop.",
  },
  {
    q: "Will this touch my live store or place real orders?",
    a: "No. The scan runs on data you paste in. Nothing connects to your checkout, nothing gets ordered, and no customer ever sees a test.",
  },
  {
    q: "We already run QA with Katalon. Why this?",
    a: "Your QA suite tests human journeys — clicks, forms, layouts. It never tests whether a machine can parse your coupon rules or your variant names. That’s the entire gap Cartness covers.",
  },
  {
    q: "Is $199 a month worth it?",
    a: "If your average order is $60 and the scan recovers even four agent checkouts a month, it’s paid for itself. Ambiguous data doesn’t fail once — it fails on every agent visit.",
  },
  {
    q: "How much dev work do the fixes take?",
    a: "Most flags are data-format fixes — normalizing a variant name, exposing a price field — not rebuilds. Each fix in the report says exactly what to change, so your devs skip the diagnosis.",
  },
];

export function FAQ() {
  const ref = useReveal<HTMLElement>();
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section className="section section--background" id="faq" ref={ref}>
      <div className="container">
        <div className="section__head">
          <p className="eyebrow">FAQ</p>
          <h2 className="reveal">Fair questions</h2>
        </div>

        <div className="faq__list">
          {FAQS.map((item, index) => {
            const isOpen = open === index;
            return (
              <div
                className="faq__item reveal"
                key={item.q}
                data-open={isOpen}
                style={{ "--i": Math.min(index, 3) } as React.CSSProperties}
              >
                <h3>
                  <button
                    className="faq__trigger"
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={`faq-panel-${index}`}
                    id={`faq-trigger-${index}`}
                    onClick={() => setOpen(isOpen ? null : index)}
                  >
                    {item.q}
                    <IconChevron />
                  </button>
                </h3>
                {isOpen ? (
                  <div
                    className="faq__panel"
                    id={`faq-panel-${index}`}
                    role="region"
                    aria-labelledby={`faq-trigger-${index}`}
                  >
                    {item.a}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   FINAL CTA — #1C1917 full-width band, the one dark moment.
   ------------------------------------------------------------------ */

export function FinalCTA() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section final" id="signup" ref={ref}>
      <div className="container final__grid">
        <div>
          <h2 className="reveal">Agents are learning to buy. Find out if your store lets them.</h2>
          <p className="final__risk reveal" style={{ "--i": 1 } as React.CSSProperties}>
            Founding users get early access and their first Agent Readiness Scan free — no
            card, no store access required.
          </p>
        </div>
        <div className="reveal" style={{ "--i": 2 } as React.CSSProperties}>
          <LeadForm source="final-cta" invert />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   FOOTER
   ------------------------------------------------------------------ */

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <span className="nav__brand">
          <Logo size={22} />
          Cartness
        </span>
        <span>Agent readiness scanning for Shopify stores. Early access, 2026.</span>
      </div>
    </footer>
  );
}
