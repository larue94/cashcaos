import { Logo } from "../Logo";
import { HeroArt } from "../HeroArt";
import { LeadForm, CTA_LABEL } from "../LeadForm";
import { useReveal } from "../../hooks/useReveal";
import type { ModalRequest } from "../LeadModal";

type OpenModal = (request: NonNullable<ModalRequest>) => void;

/* ------------------------------------------------------------------
   NAV — wordmark, three anchor links, one CTA. Nothing else.
   ------------------------------------------------------------------ */

export function Nav({ onOpen }: { onOpen: OpenModal }) {
  return (
    <header className="nav">
      <div className="container nav__inner">
        <a className="nav__brand" href="#top">
          <Logo size={26} />
          Cartness
        </a>

        <nav className="nav__links" aria-label="Primary">
          <a href="#how-it-works">How it works</a>
          <a href="#pricing">Pricing</a>
          <a href="#faq">FAQ</a>
        </nav>

        <button
          className="btn btn--primary btn--compact"
          type="button"
          onClick={() => onOpen({ source: "nav" })}
        >
          {CTA_LABEL}
        </button>
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------
   HERO — background token, split layout, no card, open.
   ------------------------------------------------------------------ */

export function Hero() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section hero" id="top" ref={ref}>
      <div className="container hero__grid">
        <div className="hero__copy">
          <h1 className="reveal" style={{ "--i": 0 } as React.CSSProperties}>
            Your store converts humans.
            <br className="hero__break" /> Can it convert AI&nbsp;agents?
</h1>

          <p className="hero__sub reveal" style={{ "--i": 1 } as React.CSSProperties}>
            Cartness simulates a shopping agent buying from your Shopify store and hands you
            a readiness score plus a prioritized fix list.
          </p>

          <div className="hero__form reveal" style={{ "--i": 2 } as React.CSSProperties}>
            <LeadForm source="hero" />
          </div>

          <p className="hero__credibility reveal" style={{ "--i": 3 } as React.CSSProperties}>
            Shopping agents skip your banners and read your raw product data — one ambiguous
            price field can kill the sale before checkout.
          </p>
        </div>

        <div
          className="hero__art-wrap reveal"
          style={{ "--i": 2 } as React.CSSProperties}
        >
          <HeroArt />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   PROBLEM — surface band, 1px-bordered open list, no cards.
   ------------------------------------------------------------------ */

const PAINS = [
  'An agent reads "$34.00 $28.90 SAVE!" as two conflicting prices. It doesn’t guess. It leaves.',
  'Your coupon rules live in prose. "Excludes sale items" means nothing to a machine — the code fails silently and the cart gets abandoned.',
  "Inventory is formatted three different ways across your catalog. Every new product description is a new chance to break the read.",
  "Your conversion report shows the drop and stops there. No session recording ever shows you a machine buyer walking away.",
];

export function Problem() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section section--surface" id="problem" ref={ref}>
      <div className="container">
        <div className="section__head">
          <p className="eyebrow">The problem</p>
          <h2 className="reveal">The buyer your analytics can&rsquo;t see</h2>
        </div>

        <ul className="problem__list">
          {PAINS.map((pain, index) => (
            <li
              className="problem__item reveal"
              key={pain}
              style={{ "--i": index } as React.CSSProperties}
            >
              <span className="problem__index" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <p className="problem__text">{pain}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------
   HOW IT WORKS — background token, 3 numbered steps in a row.
   ------------------------------------------------------------------ */

const STEPS = [
  {
    title: "Paste your product data.",
    body: "Drop in a product page’s structured data, JSON, or copied content — no app install, no store access needed.",
  },
  {
    title: "Cartness runs the agent’s read.",
    body: "It parses your prices, variants, inventory, coupons, and shipping rules exactly the way a shopping agent would, across five purchase scenarios.",
  },
  {
    title: "Get your score and fix list.",
    body: "You get a 0–100 readiness score and a prioritized list of breaks, each with a specific fix your dev team can act on today.",
  },
];

export function HowItWorks() {
  const ref = useReveal<HTMLElement>();

  return (
    <section className="section section--background" id="how-it-works" ref={ref}>
      <div className="container">
        <div className="section__head">
          <p className="eyebrow">How it works</p>
          <h2 className="reveal">From catalog paste to fix list</h2>
        </div>

        <ol className="steps">
          {STEPS.map((step, index) => (
            <li
              className="reveal"
              key={step.title}
              style={{ "--i": index } as React.CSSProperties}
            >
              <span className="step__number" aria-hidden="true">
                {index + 1}
              </span>
              <h3 className="step__title">{step.title}</h3>
              <p className="step__body">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
