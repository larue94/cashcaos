/** Renders public/og-image.png (1200x630) from scripts/og-image.html. */
import { chromium } from "playwright";
const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
const p = await b.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await p.goto(new URL("./og-image.html", import.meta.url).href, { waitUntil: "networkidle" });
await p.waitForTimeout(1500);
await p.screenshot({ path: "public/og-image.png" });
await b.close();
