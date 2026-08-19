/** Outline icons only — 24px grid, currentColor stroke, no fills. */

type IconProps = { size?: number };

function Svg({ size = 24, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

/** Magnifying glass over a barcode. */
export function IconScan(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 4v9M6 4v9M9 4v6M12 4v5" />
      <circle cx="15" cy="14" r="5.5" />
      <path d="m19.2 18.2 2.3 2.3" />
    </Svg>
  );
}

/** Gauge dial. */
export function IconGauge(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3.5 18a9 9 0 1 1 17 0" />
      <path d="m12 14 4-4" />
      <circle cx="12" cy="15" r="1.4" />
    </Svg>
  );
}

/** Wrench. */
export function IconWrench(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M15.6 3.4a5 5 0 0 0-6 6.4L3.6 15.8a2 2 0 0 0 0 2.8l1.8 1.8a2 2 0 0 0 2.8 0l6-6a5 5 0 0 0 6.4-6l-3 3-2.6-.7-.7-2.6z" />
    </Svg>
  );
}

/** Checklist. */
export function IconChecklist(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m3 6 1.6 1.6L7.8 4.4M3 13l1.6 1.6 3.2-3.2M3 20l1.6 1.6 3.2-3.2" />
      <path d="M11.5 6H21M11.5 13H21M11.5 20H21" />
    </Svg>
  );
}

/** Trending-up arrow. */
export function IconTrendUp(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 17.5 9.5 11l4 4L21 7.5" />
      <path d="M15.5 7.5H21v5.5" />
    </Svg>
  );
}

/** Document with share arrow. */
export function IconShareDoc(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M13.5 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8.5z" />
      <path d="M13.5 3v5.5H19" />
      <path d="M9 15h5.5M12 12.5 14.5 15 12 17.5" />
    </Svg>
  );
}

/** Small check used in pricing feature rows. */
export function IconCheck({ size = 16 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m3 8.5 3 3 7-7" />
    </svg>
  );
}

/** Accordion chevron. */
export function IconChevron({ size = 20 }: IconProps) {
  return (
    <svg
      className="faq__chevron"
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m5 8 5 5 5-5" />
    </svg>
  );
}

/** Modal close. */
export function IconClose({ size = 16 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m4 4 8 8M12 4l-8 8" />
    </svg>
  );
}
