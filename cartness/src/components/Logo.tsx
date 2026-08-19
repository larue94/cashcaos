/**
 * Cartness mark — a shopping cart whose basket grid lines form a scannable
 * barcode. Flat vector, ink #1C1917, one barcode bar in the accent, on a
 * transparent field. Reads at 24px; the same artwork is the favicon
 * (public/logo.svg).
 */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* handle */}
      <path
        d="M2.5 4.5h3.2l2.1 6"
        stroke="var(--color-text-primary)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* basket */}
      <path
        d="M7.5 10.5h22L26.8 21.5H10.2z"
        stroke="var(--color-text-primary)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* barcode bars — one bar in the accent */}
      <rect x="11.9" y="13" width="2" height="6" fill="var(--color-text-primary)" />
      <rect x="15.5" y="13" width="1.2" height="6" fill="var(--color-text-primary)" />
      <rect x="18.3" y="13" width="2.6" height="6" fill="var(--color-accent)" />
      <rect x="22.5" y="13" width="1.2" height="6" fill="var(--color-text-primary)" />
      <rect x="25.1" y="13" width="1.6" height="6" fill="var(--color-text-primary)" />
      {/* wheels */}
      <circle cx="13.5" cy="26.8" r="1.9" stroke="var(--color-text-primary)" strokeWidth="2" />
      <circle cx="24" cy="26.8" r="1.9" stroke="var(--color-text-primary)" strokeWidth="2" />
    </svg>
  );
}
