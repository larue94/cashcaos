# Cartness — validation landing page

Single-page React app that tests demand for Cartness: an Agent Readiness Scan
for Shopify stores. The page's only job is to convert a stranger into an email
address, so every button on it either scrolls to an anchor or opens the capture
form.

## Stack

- Vite + React + TypeScript
- Firestore for lead capture (Firebase Web SDK, loaded lazily on first submit)
- No component or CSS framework — the design system is ~40 CSS custom
  properties in `src/index.css`, and nothing outside that block declares a
  colour, font, radius, or spacing value.

## Running it

```bash
npm install
npm run dev            # http://localhost:5173
npm run build          # typecheck + production build to dist/
npm run preview        # serve dist/ on http://localhost:4174
```

## Lead capture

Every submission writes one document to the `leads` collection:

| field       | value                                                      |
| ----------- | ---------------------------------------------------------- |
| `email`     | trimmed, lowercased                                        |
| `createdAt` | `serverTimestamp()` — rules reject any client-chosen value |
| `source`    | `nav` · `hero` · `demo` · `pricing` · `final-cta`          |
| `tier`      | `Audit` · `Monitor` · `Agency`, else `null`                |

Visitors never sign in. Every form carries a visually hidden `company`
honeypot: if it is filled the submission is dropped silently and the visitor
still sees the success state, so a bot cannot tell it failed.

### Configuration

Firebase config comes from environment variables (see `.env.example`) — the
Firebase integration fills these in. Nothing is hardcoded and no key lives in
source. Without them the app still builds and renders; submitting throws a
console error rather than failing silently.

### Security rules

`firestore.rules`: anyone may **create** a lead that passes validation; nobody
may read, update or delete one from the public site, and every other collection
is closed.

## Tests

Both suites run against the Firestore emulator with the real
`firestore.rules` loaded.

```bash
npm run emulator        # terminal 1
npm run test:rules      # 20 isolated security-rules cases
npm run preview         # terminal 2, then:
npm run test:capture    # 19 end-to-end cases, real browser + real writes
```

`npm run audit:design` re-checks the page against the design spec: token-only
colours, the three permitted fonts, 6px radii, zero shadows, the spacing scale,
the type scale, section band rhythm, button specs, and that motion only ever
touches `transform` and `opacity`.

## Assets

`public/logo.svg` is the mark — a cart whose basket grid lines form a barcode,
one bar in the accent. The same file is the favicon, and `src/components/Logo.tsx`
is the same geometry inline so it can pick up theme tokens. `public/og-image.png`
is generated from `scripts/og-image.html` via `npm run og`.
