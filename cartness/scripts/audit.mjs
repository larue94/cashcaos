/** Design-spec audit: tokens, layout scale, targets, motion. */
import { chromium } from "playwright";

const URL = "http://localhost:4174/";
const TOKENS = {
  background: "rgb(250, 250, 249)",
  surface: "rgb(255, 255, 255)",
  border: "rgb(231, 229, 228)",
  textPrimary: "rgb(28, 25, 23)",
  textMuted: "rgb(87, 83, 78)",
  accent: "rgb(194, 65, 12)",
  accentHover: "rgb(154, 52, 18)",
};
const ALLOWED = new Set([...Object.values(TOKENS), "rgba(0, 0, 0, 0)"]);
const SPACING = new Set([0, 2, 3, 4, 8, 10, 14, 16, 18, 24, 28, 32, 48, 64, 96]);

const browser = await chromium.launch({
  executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(URL, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
await page.evaluate(() =>
  document.querySelectorAll(".reveal").forEach((e) => e.classList.add("is-visible")),
);

const report = await page.evaluate(
  ({ ALLOWED, SPACING }) => {
    const allowed = new Set(ALLOWED);
    const spacing = new Set(SPACING);
    const els = [...document.querySelectorAll("body *")];
    const out = {};

    // --- colour discipline -------------------------------------------
    const offColors = new Map();
    for (const el of els) {
      const s = getComputedStyle(el);
      for (const prop of [
        "color",
        "backgroundColor",
        "borderTopColor",
        "borderRightColor",
        "borderBottomColor",
        "borderLeftColor",
        "outlineColor",
        "fill",
        "stroke",
      ]) {
        const v = s[prop];
        if (!v || v === "none" || allowed.has(v)) continue;
        if (v.startsWith("rgba") && v.endsWith(" 0)")) continue;
        offColors.set(`${v} via ${prop}`, `${el.tagName}.${el.className}`.slice(0, 60));
      }
    }
    out.offTokenColors = [...offColors.entries()].map(([k, v]) => `${k} on ${v}`);

    // --- fonts --------------------------------------------------------
    out.fonts = [
      ...new Set(els.map((e) => getComputedStyle(e).fontFamily.split(",")[0].replace(/"/g, ""))),
    ].sort();

    // --- radii --------------------------------------------------------
    out.radii = [
      ...new Set(
        els.flatMap((e) => {
          const s = getComputedStyle(e);
          return [s.borderTopLeftRadius, s.borderBottomRightRadius];
        }),
      ),
    ]
      .filter((r) => r !== "0px")
      .sort();

    // --- shadows ------------------------------------------------------
    out.shadows = els.filter((e) => {
      const s = getComputedStyle(e).boxShadow;
      return s && s !== "none";
    }).length;

    // --- spacing scale (off-scale paddings/margins/gaps) --------------
    const offScale = new Set();
    for (const el of els) {
      const s = getComputedStyle(el);
      for (const prop of [
        "paddingTop",
        "paddingBottom",
        "paddingLeft",
        "paddingRight",
        "marginTop",
        "marginBottom",
        "rowGap",
        "columnGap",
      ]) {
        const v = s[prop];
        if (!v || v === "normal" || v === "auto") continue;
        const n = Math.abs(Math.round(parseFloat(v)));
        if (!Number.isFinite(n) || spacing.has(n)) continue;
        offScale.add(`${prop}: ${v} on ${el.tagName}.${String(el.className).slice(0, 34)}`);
      }
    }
    out.offScaleSpacing = [...offScale];

    // --- type scale ---------------------------------------------------
    const t = (sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const s = getComputedStyle(el);
      return `${s.fontSize} / ${s.fontWeight} / ${(parseFloat(s.lineHeight) / parseFloat(s.fontSize)).toFixed(2)} / ${s.fontFamily.split(",")[0].replace(/"/g, "")}`;
    };
    out.type = {
      h1: t("h1"),
      h2: t("#problem h2"),
      h3: t(".benefit__title"),
      body: t(".hero__sub"),
      small: t(".leadform__note"),
      mono: t(".datarow__value"),
    };

    // --- layout -------------------------------------------------------
    out.containerWidth = Math.round(
      document.querySelector("#problem .container").getBoundingClientRect().width,
    );
    out.sectionPadding = [
      ...new Set(
        [...document.querySelectorAll("section")].flatMap((s) => {
          const cs = getComputedStyle(s);
          return [cs.paddingTop, cs.paddingBottom];
        }),
      ),
    ];
    out.benefitColumns = getComputedStyle(document.querySelector(".benefits__grid"))
      .gridTemplateColumns.split(" ").length;
    out.sectionBands = [...document.querySelectorAll("section")].map((s) => ({
      id: s.id,
      bg: getComputedStyle(s).backgroundColor,
    }));

    // --- buttons ------------------------------------------------------
    const btn = getComputedStyle(document.querySelector(".hero__form .btn--primary"));
    out.primaryButton = {
      bg: btn.backgroundColor,
      color: btn.color,
      padding: `${btn.paddingTop} ${btn.paddingRight}`,
      radius: btn.borderTopLeftRadius,
    };
    const sec = getComputedStyle(document.querySelector("#pricing .btn--secondary"));
    out.secondaryButton = {
      bg: sec.backgroundColor,
      color: sec.color,
      border: `${sec.borderTopWidth} ${sec.borderTopStyle} ${sec.borderTopColor}`,
      padding: `${sec.paddingTop} ${sec.paddingRight}`,
    };

    // --- nav ----------------------------------------------------------
    out.nav = {
      links: [...document.querySelectorAll(".nav__links a")].map((a) => a.textContent.trim()),
      buttons: document.querySelectorAll(".nav button").length,
    };

    // --- every interactive target -------------------------------------
    out.targets = [
      ...document.querySelectorAll("a[href], button"),
    ].map((el) => {
      if (el.tagName === "A") return `a → ${el.getAttribute("href")}`;
      if (el.type === "submit") return "button → submits capture form";
      if (el.closest(".faq__item")) return "button → FAQ accordion";
      if (el.classList.contains("modal__close")) return "button → close modal";
      return "button → opens capture form";
    });

    // --- recommended tier ---------------------------------------------
    const rec = getComputedStyle(document.querySelector(".tier--recommended"));
    out.recommendedTier = {
      border: `${rec.borderTopWidth} ${rec.borderTopStyle} ${rec.borderTopColor}`,
      transform: rec.transform,
      badge: document.querySelector(".tier__badge")?.textContent,
    };

    // --- motion --------------------------------------------------------
    const animatedProps = new Set();
    for (const el of els) {
      const s = getComputedStyle(el);
      if (s.transitionProperty && s.transitionProperty !== "all" && s.transitionProperty !== "none") {
        s.transitionProperty.split(",").forEach((p) => animatedProps.add(p.trim()));
      }
    }
    out.transitionProperties = [...animatedProps].sort();
    out.transitionDurations = [
      ...new Set(
        els.flatMap((e) =>
          getComputedStyle(e)
            .transitionDuration.split(",")
            .map((d) => d.trim()),
        ),
      ),
    ].filter((d) => d !== "0s");
    out.transitionTimings = [
      ...new Set(
        els.flatMap((e) =>
          getComputedStyle(e)
            .transitionTimingFunction.split(", ")
            .map((d) => d.trim()),
        ),
      ),
    ];

    return out;
  },
  { ALLOWED: [...ALLOWED], SPACING: [...SPACING] },
);

console.log(JSON.stringify(report, null, 2));
await browser.close();
