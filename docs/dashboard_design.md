# Dashboard design system

Palette, layout grids and visual choices for the Power BI report. Everything here is
validated, not chosen by eye — the colour section states the measured numbers.

Import `powerbi/themes/NamibiaObservatory-Light.json` (default) or
`-Dark.json` via **View → Themes → Browse for themes**.

---

## 1. Which theme

Ship **light** as the default and keep dark for one specific case.

| Use | Theme |
|---|---|
| Anything exported to PDF, attached to an application, shown to a DFI or a reviewer | Light |
| A wall-mounted or projected display in a lit room | Light |
| A screen in a dark room, or a dim-room presentation | Dark |

Light prints, light survives a bad projector, and light is what a funder expects from an
analytical document. Dark looks better on a 1920×1080 screen in a dark room and nowhere
else. Both themes are fully validated, so switching is a one-click decision, not a
redesign — but pick one per artefact and do not mix within a report.

---

## 2. Palette

The eight categorical hues are grounded in Namibian landscape colour — Atlantic blue,
dune ochre, acacia green, oxide red, Namib sand — but the *steps* were chosen by
validation, not by taste.

### Categorical — assign in this fixed order, never cycled

| Slot | Hue | Light | Dark | Conventional use here |
|---|---|---|---|---|
| 1 | Atlantic blue | `#1F6FB2` | `#4894DA` | primary series, hydro, water |
| 2 | Dune ochre | `#D9772B` | `#BA5D03` | secondary series, imports |
| 3 | Acacia green | `#0E9E7E` | `#21A686` | renewables, wind, hydrogen |
| 4 | Oxide red | `#C8453F` | `#CB4741` | deficits, fossil generation |
| 5 | Namib sand | `#D9A520` | `#B58703` | solar |
| 6 | Welwitschia violet | `#6E5BC6` | `#7866D2` | fifth series |
| 7 | Savanna olive | `#7E9E2F` | `#7D9D2E` | sixth series |
| 8 | Rose | `#D4568C` | `#C2467D` | seventh series |

**Measured.** Light: worst adjacent CVD ΔE 8.6 (deuteranopia), normal-vision ΔE 23.4 —
both clear the gates. Dark: worst adjacent CVD ΔE 8.0, normal-vision 16.5. For scatter,
bubble and choropleth forms — where *every* pair is on screen together, not just
neighbours — only the **first three slots** validate (light CVD 9.9 / normal 18.2; dark
CVD 12.7 / normal 15.5). Past three series in those forms, fold the tail into "Other"
or use small multiples.

**Relief rule, light theme only:** `#D9A520` (2.15:1) and `#7E9E2F` (2.95:1) sit below
3:1 against the light surface. Wherever either carries meaning, ship a visible direct
label or a table view alongside — they are legal with that relief and not without it.

### Sequential — magnitude, one hue, light→dark

Use for drought severity, risk magnitude, anything "how much".

- Sand (risk/drought) light: `#CFA862 #B78B3C #9C6D22 #7E5213 #5B3808`
- Sand dark: `#71501A #916623 #B07F31 #CDA055 #E4C286`
- Blue (rainfall, water) light: `#8FB9CF #6397B6 #3F7497 #28547A #163A54`
- Blue dark: `#2A5570 #357291 #4891B2 #6DAFCC #9CCCE0`

### Diverging — polarity, two hues + a neutral midpoint

Use for SPI, rainfall anomaly, trade balance, deficit vs surplus. Dry/deficit reads
brown, wet/surplus reads blue — the SPI convention, and the one hydrologists expect.

**Light:** `#5B3808 #7E5212 #A2761F #B79450 #C6AC77` · **`#E6E3DC`** · `#9CB5C6 #779FB9 #5A869F #3B6887 #23455F`

**Dark:** `#E0BD85 #C79C55 #A87B2B #855C19 #6B4712` · **`#2B3A44`** · `#27536D #356B88 #4E8AA8 #74ACC6 #9DCADE`

Never put a hue at the midpoint. Never a rainbow.

### Status — reserved, and never colour alone

| State | Light | Dark |
|---|---|---|
| Good | `#1B7A4F` | `#2E9A66` |
| Warning | `#C79A1E` | `#C9A12A` |
| Critical | `#A8302A` | `#D4544A` |

A green/amber/red scale cannot clear colourblind separation — green↔red sits at
deuteranopia ΔE ≈ 5 in both themes, and no re-stepping fixes that; it is inherent to
the traffic-light metaphor. **So status always ships with an icon or an arrow glyph and
a text label.** `Change Arrow` and `Change Caption` in `powerbi/measures.dax` exist for
exactly this. Never reuse these three as "series 4".

### Risk bands are ordinal, not status

Normal → Watch → Severe → Extreme is an *ordered* scale, so it takes the one-hue sand
ramp plus the band name, not a traffic light. `Risk Band Colour` does this.

### Surfaces and ink

| Role | Light | Dark |
|---|---|---|
| Page canvas | `#F4F2EC` | `#0B151C` |
| Card surface | `#FBFAF7` | `#101E27` |
| Raised surface | `#EFEDE5` | `#17262F` |
| Hairline / border | `#E2DED3` | `#263A46` |
| Gridline | `#E7E3D9` | `#1D303A` |
| Text primary | `#1C2B33` (13.9:1) | `#F2F6F8` (15.6:1) |
| Text secondary | `#5A6B74` (5.3:1) | `#9DB2BF` (7.7:1) |
| Text muted | `#8D9BA3` | `#6E8696` (4.5:1) |

Text always wears a text colour. A number never takes its series' colour — the coloured
mark beside it carries identity.

---

## 3. Layout

### Grid

Keep the 1920×1080 canvas. Use a **12-column grid**: 24px outer margin, 12px gutters,
so one column is 137px. Vertical rhythm in 8px steps. Every visual snaps to column
boundaries — nothing is eyeballed.

Reserve a **64px header band** (page title left, global date slicer right) and a
**32px footer band** (`Data As Of` measure, left-aligned, in secondary ink). The footer
is not decoration: a dashboard that does not say how old its numbers are cannot be
trusted by someone who did not build it.

### Page furniture

- **Visual headers off** (already in the theme). On a wall display the icon strip is noise.
- **One slicer row, at the top, never down the side.** A left rail of slicers costs
  137px of width on every page forever. Put the year/date slicer in the header band and
  any dimension slicer immediately beneath it, in one row.
- **8px corner radius, 1px hairline border, no drop shadows.** Shadows on a flat
  analytical surface read as a template default.
- **Sync the date slicer across pages** (View → Sync slicers). A reader who filters to
  2024 on the exec page expects 2024 everywhere.

### The anti-patterns to hold the line on

- **No dual axes, ever.** Two y-scales is the single most common chart mistake. Two
  measures of different scale → two charts stacked, or index both to a common base year.
- **No pie or donut for the generation mix.** Six slices, and the reader's job is to
  compare shares. Use a horizontal bar chart sorted descending, or a single stacked bar
  if the 100%-ness is the point.
- **No gauge for the climate risk index.** A gauge spends a quarter of the page to show
  one number with no history. A stat tile plus a sparkline shows the number *and* where
  it came from, in less space.
- **No 3D, no gradients, no background images.**
- **No data label on every point.** Label the first, the last, and the extreme.

---

## 4. Page-by-page

### Page 1 — Executive Overview

The current page is 24 visuals, all KPI cards, textboxes and shapes. Seven numbers with
no history is a scoreboard, not a dashboard: a reader cannot tell whether 65.2% debt is
a crisis or an improvement. Replace roughly half the card real estate with trend.

**Layout.** Header band. Then a **headline sentence** across all 12 columns (the
`Executive Headline` measure) — one line of prose stating what the numbers mean, which
is the highest-value object on the page. Then a **KPI strip of five tiles**, not seven:
GDP growth · inflation · broad unemployment · debt-to-GDP · climate risk band. Each
tile is value + `Change Caption` + a 40px-high sparkline. Below that, a 2×2 of charts:

| | |
|---|---|
| GDP growth, 2000→, line with a zero reference line | Debt-to-GDP vs the 60% SADC benchmark, line + benchmark line, projections dashed |
| Trade balance, diverging columns around zero | Climate risk index monthly, area, with the Severe threshold marked |

Cut: the separate strict *and* broad unemployment cards (pick broad for the exec page,
put both on the economy page), and the population card (it belongs on economy, it does
not move).

**Fix the climate card.** It is currently bound to `Sum(climate_risk_composite.climate_risk_index)`
— a sum of a monthly index over 300 months, which is a meaningless number that grows
forever. Use `[Climate Risk]` (an average) with `[Risk Band]` as the label.

### Page 2 — Economy & Finance (currently empty)

Two columns. Left, the household story: inflation vs the 4.5% midpoint, a line;
unemployment strict/broad/youth as **clustered columns** for 2016/2018/2023 — three
survey points are not a trend line and drawing them as one implies measurement that
does not exist. Right, the fiscal story: debt-to-GDP with the 60% benchmark and the
2027–29 projections visibly dashed; total debt and interest payments as two stacked
charts, never a dual axis; fiscal deficit as diverging columns against the 3% line.

Use `Value Actual` and `Value Forecast` as two series on the debt chart so the
projection reads as a projection.

### Page 3 — Trade & Competitiveness (new)

Exports and imports as two lines on one axis (same units, so one axis is correct), with
the balance as diverging columns beneath, sharing the x-axis. Trade openness and mineral
rents as a small-multiple pair. The caveat about 2020–23 being round estimates belongs
in a footnote on this page, not buried in the README.

### Page 4 — Climate & Energy (currently empty)

**Left half, climate.** A Namibia **choropleth** of regional SPI-12 on the diverging
ramp — this is the visual the regional extract was built for and the single most
distinctive thing this dashboard can show. Beneath it, a **small-multiple grid of ten
regional SPI-12 sparklines**, sorted driest first, so the reader sees that drought is
regional before they see a national average. A national SPI-12 line with the −1.0 and
−1.5 drought thresholds marked completes it.

**Right half, energy.** Generation mix as a horizontal bar sorted descending, coloured
by `Color_Light`/`Color_Dark`. Then — and this is the interesting chart — **share of
supply next to share of installed capacity, as a paired bar**. Solar is 24% of capacity
and 4% of supply; that gap is the story about intermittency and curtailment, and no
single pie chart can show it. Energy-security metrics as bullet charts: current value
as the bar, target as the reference line.

Add a footnote reconciling the 21% vs ~40% renewable-share discrepancy, or drop one of
the two numbers. Publishing both without explanation is the kind of thing a careful
reader notices first.

### Page 5 — Green Hydrogen Observatory (currently empty)

A **timeline**, not a table, is the right primary form: this is a pipeline of projects
moving through FEED → FID → COD against dated milestones. Lay out `milestones.csv` and
`generation_pipeline.csv` on a shared horizontal time axis, one row per project, bar
length = construction window, colour = status (ordinal: Announced → FEED → Under
construction → Operating, on the sand ramp). Capacity as the bar label.

Beneath: committed green FDI by partner as a horizontal bar split grant/loan;
announcements as a date-sorted card list with the `Impact` field driving an ordinal
chip, not a traffic light. A stat tile for "N$37.4bn committed vs US$190bn needed by
2040" — that ratio is the whole point of the page and deserves to be one number in
large type, not a row in a table.

---

## 5. Visual form, by data job

| The data's job | Form | Not |
|---|---|---|
| One headline number | stat tile + sparkline | gauge, KPI visual with no history |
| Change over time, one series | line, 2px | area with a non-zero baseline |
| Change over time, 2–4 series | line, direct-labelled at the last point | legend-only with 6 series |
| Composition, few parts | horizontal bar, sorted | pie, donut |
| Composition over time | stacked area, ≤4 bands | stacked area with 8 bands |
| Polarity around a baseline | diverging columns | bars all one colour |
| Value vs target | bullet chart | gauge |
| Geographic variation | choropleth, diverging or sequential | bubbles on a map |
| Many similar series | small multiples, shared axis | one chart with 10 lines |
| Ragged survey points | clustered columns | a line implying continuity |
| Ordered stages | timeline / Gantt | a table |

Mark specs: 2px lines, markers ≥8px and only when the series is sparse, 4px rounded bar
ends, a 2px surface gap between adjacent fills, recessive gridlines on the value axis
only, no gridlines on the category axis. All of this is already set in the theme files.

---

## 6. Accessibility floor

- A legend is present for every chart with ≥2 series; charts with ≤4 series are *also*
  direct-labelled, so identity never rests on colour alone.
- Every status or direction indicator carries a glyph and a word, not just a colour.
- Turn on **View → Show accessibility** checks, and set tab order and alt text on every
  visual. Power BI will not do this for you and a screen reader cannot guess.
- Keep a table view reachable from each page (a bookmark to a drill-through table page
  is enough). This is also the relief the two low-contrast light-theme hues require.
- Sort orders and axis ranges are explicit, never left to default. A y-axis that
  auto-scales per filter makes two states of the same chart incomparable.
