/**
 * Hero illustration — a line-art shopping cart passing through a checkout
 * gate rendered as a test-report card showing a large "94" score. Ink
 * #1C1917, score and gate highlights in #C2410C, flat #FAFAF9 field, even
 * flat lighting, no gradients or shadows.
 */
export function HeroArt() {
  const ink = "var(--color-text-primary)";
  const accent = "var(--color-accent)";
  const surface = "var(--color-surface)";
  const muted = "var(--color-text-muted)";
  const line = "var(--color-border)";

  return (
    <svg
      className="hero__art"
      viewBox="0 0 600 480"
      fill="none"
      role="img"
      aria-label="A shopping cart passing through a checkout gate whose report card scores the store 94 out of 100 for agent readiness."
    >
      <rect width="600" height="480" fill="var(--color-background)" />

      {/* --- checkout gate ---------------------------------------- */}
      <rect x="40" y="72" width="520" height="34" rx="6" fill={surface} stroke={ink} strokeWidth="2.5" />
      <rect x="40" y="106" width="24" height="326" rx="6" fill={surface} stroke={ink} strokeWidth="2.5" />
      <rect x="536" y="106" width="24" height="326" rx="6" fill={surface} stroke={ink} strokeWidth="2.5" />

      {/* gate highlights — the sensors either side of the beam */}
      <rect x="46" y="352" width="12" height="6" rx="3" fill={accent} />
      <rect x="46" y="368" width="12" height="6" rx="3" fill={accent} />
      <rect x="542" y="352" width="12" height="6" rx="3" fill={accent} />
      <rect x="542" y="368" width="12" height="6" rx="3" fill={accent} />

      {/* scan beam — the cart's solid fill interrupts it, so the beam
          reads as landing on the cart */}
      <line
        x1="64"
        y1="361"
        x2="536"
        y2="361"
        stroke={accent}
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="9 11"
      />

      {/* --- cart, mid-gate --------------------------------------- */}
      <path
        d="M86 292h26l17 48"
        fill="none"
        stroke={ink}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M129 340h153l-18 62H147z"
        fill={surface}
        stroke={ink}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* basket grid lines read as a barcode — the logo's motif */}
      <rect x="152" y="352" width="6" height="38" fill={ink} />
      <rect x="172" y="352" width="3" height="38" fill={ink} />
      <rect x="189" y="352" width="8" height="38" fill={accent} />
      <rect x="211" y="352" width="3" height="38" fill={ink} />
      <rect x="228" y="352" width="6" height="38" fill={ink} />
      <circle cx="167" cy="424" r="12.5" fill={surface} stroke={ink} strokeWidth="2.5" />
      <circle cx="245" cy="424" r="12.5" fill={surface} stroke={ink} strokeWidth="2.5" />

      {/* --- report card, mounted inside the gate ------------------ */}
      <rect x="308" y="140" width="208" height="164" rx="6" fill={surface} stroke={ink} strokeWidth="2.5" />
      <line x1="308" y1="174" x2="516" y2="174" stroke={ink} strokeWidth="1.5" />
      <text
        x="324"
        y="164"
        fill={muted}
        fontFamily="var(--font-mono)"
        fontSize="12"
        letterSpacing="1.3"
      >
        AGENT READINESS
      </text>
      <text
        x="322"
        y="248"
        fill={accent}
        fontFamily="var(--font-heading)"
        fontSize="64"
        fontWeight="700"
        letterSpacing="-2"
      >
        94
      </text>
      <text
        x="404"
        y="248"
        fill={muted}
        fontFamily="var(--font-heading)"
        fontSize="18"
        fontWeight="600"
      >
        / 100
      </text>

      <rect x="324" y="266" width="9" height="9" rx="2" fill={accent} />
      <rect x="341" y="268" width="106" height="6" rx="3" fill={line} />
      <rect x="324" y="282" width="9" height="9" rx="2" fill={line} />
      <rect x="341" y="284" width="78" height="6" rx="3" fill={line} />

      {/* --- ground ----------------------------------------------- */}
      <line x1="28" y1="432" x2="572" y2="432" stroke={ink} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
