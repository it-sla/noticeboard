---
name: Notice Board design system (Apple-inspired)
source: owner-supplied "Apple-design-analysis" spec, condensed and adapted for a dense admin app
colors:
  primary: "#0066cc"          # Action Blue - the ONLY interactive accent
  primary-focus: "#0071e3"    # keyboard focus ring
  primary-on-dark: "#2997ff"  # links on dark surfaces
  ink: "#1d1d1f"
  ink-muted-80: "#333333"
  ink-muted-48: "#7a7a7a"
  hairline: "#e0e0e0"
  divider-soft: "#f0f0f0"
  canvas: "#ffffff"
  canvas-parchment: "#f5f5f7"
  surface-pearl: "#fafafc"
  surface-tile-1: "#272729"   # dark tile / sidebar
  surface-black: "#000000"
  chip-translucent: "#d2d2d7"
typography:
  family: "SF Pro Display/Text -> system-ui, -apple-system, Inter, 'Noto Sans Devanagari'"
  display: "28-40px / 600 / tracking -0.02em"       # page titles
  body: "15px / 400 / 1.47 / tracking -0.01em"      # admin density (spec says 17px for marketing)
  caption: "14px / 400 / tracking -0.016em"          # tables, buttons
  weights: "400, 600 only (no 500)"
rounded: { sm: 8px, md: 11px, lg: 18px, pill: 9999px }
spacing: "8px base; card padding 24px; section rhythm 24-32px"
---

# Rules (apply to every screen)

1. **One accent.** `primary` (#0066cc) for every link, primary action and focus. No second brand colour.
   Semantic status colours (red failure, amber warning, green success) are allowed only inside badges/alerts.
2. **Pills for actions.** Buttons are `rounded-full`; primary = solid blue + white text, secondary = white/transparent
   with blue text and a blue 1px ring. Press state `scale(0.95)`. Focus = 2px `primary-focus` outline.
3. **Surfaces, not shadows.** Page canvas is parchment `#f5f5f7`; cards are white with a 1px hairline and `18px` radius.
   No box-shadows on cards, buttons, text or inputs. The sidebar is the dark tile `#272729` with white text.
4. **Typography.** System/SF stack, weights 400 and 600 only, slightly negative letter-spacing on titles.
   Titles use ink `#1d1d1f`; muted copy `#7a7a7a`.
5. **Inputs** are white, hairline-bordered, `11px` radius; search fields are pills.
6. **Tables** sit in a white 18px-radius hairline container; header row parchment, 12px uppercase labels.
7. **Quiet chrome.** No gradients, no decorative borders. Whitespace separates sections.
8. **Dialogs/toasts:** 18px radius dialog on white; toasts are ink `#1d1d1f` with white text.
9. **Email** follows the same palette: parchment page, white 18px card, hairline dividers, blue links, ink text.

# Adaptation notes
- The spec's 17px body and 80px tile padding are for marketing pages; this is a data-dense admin UI, so body is 15px and
  spacing is 24px. All colour, radius, weight and button rules are kept.
- Apple's top "global nav" is rendered as the left dark sidebar (desktop) and a black top bar (mobile).
- Photography-first imagery maps to the notice image: it is shown edge-to-edge in its card with a 11px radius.
