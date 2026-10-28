---
name: 上海路网调色台
description: Local map editing with a quiet blue-gray workbench
colors:
  accent: "#245e86"
  ink: "#21364a"
  muted: "#526779"
  border: "#dce3e9"
  surface: "#fff"
  desk: "#e9eef2"
  soft: "#f2f5f8"
  button-hover: "#e9f0f6"
  primary-hover: "#194d72"
  selected: "#f1f6fa"
  focus: "#2d7caf"
  invalid: "#a53939"
  status: "#3b795e"
typography:
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "21px"
    fontWeight: 650
    letterSpacing: "-.02em"
  title:
    fontSize: "18px"
  section:
    fontSize: "13px"
    fontWeight: 650
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
  label:
    fontSize: "12px"
  caption:
    fontSize: "11px"
rounded:
  swatch: "3px"
  color-input: "5px"
  control: "7px"
  notice: "8px"
  details: "12px"
spacing:
  tight: "4px"
  compact: "8px"
  field: "10px"
  small: "12px"
  medium: "16px"
  section: "20px"
  panel: "24px"
  workspace: "28px"
components:
  button-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-text:
    textColor: "{colors.accent}"
    padding: "5px 0"
    typography: "{typography.label}"
  input-hex:
    textColor: "{colors.muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.swatch}"
    width: "72px"
    padding: "5px 2px"
  preset-selected:
    backgroundColor: "{colors.selected}"
    rounded: "{rounded.control}"
    padding: "4px"
  data-details:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.details}"
    typography: "{typography.label}"
    padding: "22px 25px"
---

# Design System: 上海路网调色台

## Overview

**Creative North Star: "地图调色工作台"**

A local map workbench extending the existing blue-gray map-tool interface. White editing surfaces and restrained blue controls keep attention on editable road geometry, water and land. Compact system typography supports repeated adjustments and offline use.

**Key Characteristics:**

- Map-led workspace with quiet white and blue-gray chrome.
- Compact native controls with visible focus and numerical values.
- Editable map palettes independent of the interface palette.

This captures the implemented system in `style.css`, `index.html` and `app.js`, checked against desktop and mobile finish captures. The surface direction and operating mode remain in `docs/surface.md`. The sidecar’s tonal ramps are derived panel previews; the frontmatter records the actual implemented colors.

## Colors

### Primary

The muted blue **accent** identifies export, links, selected presets, sliders and checkboxes. **Primary-hover** deepens the export action; **focus** provides a separate keyboard outline.

### Neutral

**Ink** carries readable labels; **muted** carries secondary instructions and data. **Surface** forms the header, sidebar and preview sheet. **Desk** separates the workspace; **soft** supports loading surfaces. **Border** divides editing groups. **Button-hover** and **selected** provide quiet state changes.

### Status

**Status** is the small green trial-data indicator. **Invalid** marks malformed hex input.

**The Independent Palette Rule.** Interface colors remain stable when users change map themes. Map colors are document content, sourced from `PRESETS`, `SURFACE_PALETTES` and `vendor/maptoposter/themes.js`, not global UI tokens.

## Typography

Use the native system stack with Chinese fallbacks. The header uses the headline role; sidebar headings use title; group headings use section. Controls inherit body typography, with label and caption sizes for dense editing and provenance. Numeric hex and width values use tabular figures.

The map-sheet heading uses (18px), weight (550), and tracking (.08em); its English descriptor uses caption size and tracking (.13em). At widths up to (700px), the app headline becomes (18px) and road labels become (14px). No separate display or monospaced font is installed.

## Layout

Desktop uses a (72px) header above a viewport-height two-column workspace. The left editor is (306px) wide with independent vertical scrolling; from (1600px), it expands to (326px). The remaining area contains the view toolbar, centered map sheet and data strip. The map viewport is always (16:10); the sheet fits available width and height. Sheet title, compass, caption and preview controls belong to the surrounding interface.

The sidebar uses (24px 22px 18px) padding. Preset swatches form four columns for built-ins and three columns for the six library themes. Spacing is compact within rows and larger between editing sections. At (1000px) and below, workspace gutters shrink. At (1100px) and below, the local-data badge is hidden.

At (700px) and below, the header may wrap and the preview precedes the editor in a single column. The workspace height is `calc(100vw / 1.6 + 190px)`, bounded between (450px) and (650px); the editor participates in page scrolling. Mobile road color controls enlarge to (32px); base rows become (44px) tall.

## Elevation & Depth

The interface uses flat white controls, fine borders and restrained shadows. The preview sheet receives `0 7px 26px #1e3a5012`; selected view buttons receive `0 2px 5px #243d5210`. The data-details overlay uses `0 6px 28px #12243622`, and transient notices use `0 4px 18px #12243625`. Map control groups remove the library shadow and use the interface border.

## Shapes

Controls use gently rounded corners; color wells and swatch strips are tighter. The map sheet itself is rectangular. Circular dots communicate data status. Preserve this small-scale corner hierarchy rather than turning editing sections into separate cards.

## Components

### Actions and view navigation

Export is the filled primary action with an inline outlined SVG icon. Save/load use bordered white buttons; reset and data details use text buttons. Buttons have a (36px) minimum height, with (32px) text buttons. Hover changes background over (.16s ease-out); disabled buttons use (.5) opacity and a wait cursor. Keyboard focus uses a (3px) outline offset by (3px). View buttons are transparent until selected, then use a white fill and the light navigation shadow.

### Color and layer controls

Background and water rows pair an uppercase hex field with a native color picker. Invalid hex values receive the invalid border; focused hex input uses the implemented `2px solid #a8cde5` outline. Road rows combine a color picker, named visibility checkbox, width range and right-aligned two-decimal output. Hidden road labels and ranges dim to (.45) opacity. Surface rows combine a color picker, visibility checkbox and opacity range. Keep accessible names on every input.

### Preset tiles

Each tile shows four equal color bands and a short Chinese name. Selected tiles use an accent border and selected fill with `aria-pressed`. There are four built-in themes and six MapToPoster presets; their source link and adaptation note remain near the tiles. Theme changes retain per-layer editing.

### Map and feedback

The preview sheet includes title, north indicator, caption, map navigation, scale and attribution. Place markers are optional preview overlays. PNG export draws only the map canvas: exact (1920 × 1200), (3840 × 2400, default) or (7680 × 4800) pixels, without text, dots, frame or padding. Large exports render native tiles and join them; export progress temporarily blocks editing and restores the view afterward.

Loading uses a small pulse (1.2s ease-in-out). View resets animate for (450ms), location jumps for (550ms). Reduced-motion preference disables CSS motion and makes these map moves immediate. Data details expand above the data strip; notices use a dark compact bottom overlay.

## Do's and Don'ts

### Do:

- Do preserve the blue-gray interface when map palettes change.
- Do keep layer color, visibility and width or opacity controls together.
- Do retain native inputs, visible keyboard focus and reduced-motion behavior.
- Do keep the 16:10 export restricted to map pixels at the selected native resolution.

### Don't:

- Don't add poster text, markers, frames or padding to exported maps.
- Don't treat MapToPoster map colors as interface tokens.
- Don't replace the system font or introduce decorative gradients into the editing chrome.

## 2026-10-28 trial additions

Preserve the existing workbench. The header identifies Shanghai trial mode. The sidebar starts with a short instruction explaining palette → layers → export and browser-local saving. Loading shows actual bytes and a native progress bar, then an indeterminate rendering stage; failures show a retry button. Desktop defaults to 3840×2400, widths up to 700px default to 1920×1200. Both desktop and emulated mobile viewport captures are in `.impeccable/review/trial-*.png`; verification limits are recorded in `docs/VERIFICATION.md`.
