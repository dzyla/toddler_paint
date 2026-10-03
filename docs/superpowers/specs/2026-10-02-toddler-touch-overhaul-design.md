# Toddler touch overhaul — design

Date: 2026-10-02
Status: approved for planning

## Purpose

A 2–3-year-old uses Little Art Studio on a phone, a tablet, and a
touchscreen laptop. He is pre-reading, so word labels are decoration:
shape, colour and size carry all meaning. He taps repeatedly, opens and
closes the picture menu, cannot tell the gallery cards apart at normal
viewing distance, and mis-taps the cluster of buttons at the top right.
He gets frustrated often enough that his parent asked for an overhaul.

Success: he taps, and something visibly and audibly happens, every time.
Nothing he can do with ten fast taps damages his picture or wedges the
interface. He can find a picture he wants and tell the cards apart.

## Root cause

The app defends against toddler input by **silently discarding it on
timers**:

| Guard | Location | Effect |
|---|---|---|
| `SETTLE_MS = 500` | `write_v5.html:1782` | A freshly opened window ignores touch for half a second |
| `REPEAT_MS = 600` | `write_v5.html:1782` | Any button ignores a second tap for 600 ms |
| `data-cooldown="1000"` | `write_v5.html:399,400,407` | New page, Clean and Next picture ignore taps for a full second |
| ghost-click swallow, 450 ms | `write_v5.html:1828` | Trusted clicks are discarded after any panel tap |
| `sheetClosedAt < 350` | `write_v5.html:1487` | The paper ignores touch for 350 ms after a window closes |

To a 2-year-old a silently ignored tap is indistinguishable from a broken
app, so he taps again — and that tap is suppressed *because* he tapped.
The guard manufactures the mashing it exists to absorb.

A second, independent cause compounds it. `write_v5.html:1484` gives the
paper pointer capture on the first finger down, and eight control sites
begin with `if (activeId !== null) return`. **While any finger or palm
rests on the paper, the entire interface is dead** — every tool, colour
and button silently refuses. A toddler steadying a tablet with one hand
and tapping with the other gets nothing, with no explanation.

## Decisions taken with the parent

- Undo, New page and Clean are his controls. Redo moves to the grown-up
  menu, where `gRedo` already exists.
- The gallery shows 6 bold cards per page.
- `write_v5.html` is **preserved unchanged**. The overhaul ships as a new
  `write_v6.html`, so either version can be handed to the child.
- Touch is the only input that matters. Mouse support must keep working
  but is no longer optimised for.
- The 12 tools and 14 colours all stay available.
- Single standalone HTML file, no build step, no network dependency.

## Approach: instant and idempotent

Stop defending with timers; defend with structure. Controls respond
immediately, and repeat taps are made *harmless* rather than *blocked*.

### 1. Tap engine

Replace the per-panel `pointerup` handler at `write_v5.html:1789-1821`
with one tap engine shared by every child-facing control.

- **Activate on `pointerdown`** for all non-destructive controls: tools,
  colours, stamps, brush sizes, gallery cards, gallery tabs, gallery
  arrows, Undo, New page, Next picture, the phone dock. Response arrives
  under the finger, and sliding off afterwards cannot lose the tap.
- **Clean keeps press-and-release**, so a graze cannot wipe the page. It
  is the only control that waits for `pointerup`.
- **Remove** `REPEAT_MS`, all three `data-cooldown` attributes, and
  `SETTLE_MS`. Reduce the post-close paper guard from 350 ms to 150 ms,
  which is all that is needed once cards act on pointerdown.
- **Keep** the ghost-click swallow, narrowed so it can never discard a
  trusted tap inside an open sheet.
- **Gap snapping** rises from 26 px to 40 px and refuses ambiguity: if two
  candidate buttons are within 25% of the same distance, the tap is
  dropped rather than guessed. Between Undo and Clean a guess is worse
  than nothing.

### 2. Resting fingers no longer block the interface

Introduce `drawingNow()`: true only when the active stroke has *moved*
within the last 400 ms. Replace the `activeId !== null` guard at all eight
sites (`1802`, `1833`, `1952`, `1993`, `2032`, `2153`, `2188`, `2426`,
and the paper's own check at `1485` keeps `activeId`) with
`drawingNow()`. A finger parked on the paper has its stroke committed via
`finish()` and the control tap is honoured. Active scribbling still
blocks tool changes, which was the original and correct intent.

### 3. Mashing is harmless

- **Clean** on an already-empty page records no history entry and redraws
  nothing; it only confirms. Ten taps cannot consume ten undo slots.
- **Choosing the page already open** closes the gallery and does nothing
  else: no history entry, no re-render.
- **Re-tapping the current tool or colour** pops and chimes without
  changing state.
- **Undo** is naturally repeatable and needs no lock.
- **Next picture advances once per tap.** This reverses today's documented
  "mashing advances once" behaviour, with the parent's agreement. Each
  advance is visible and is one undo step.

### 4. New page is a real on/off toggle

`btnPaper` calls `toggleSheet('paperSheet')`, reading the live `.open`
class so state cannot desync. While the gallery is open the action
cluster lifts above the overlay and the gallery card insets its top edge,
so **the button he pressed stays visible and tappable**, wearing an "on"
ring like a selected tool. A second tap closes it; a third reopens
immediately with no lock. The large Back button remains as the other
exit. Backdrop taps continue to do nothing.

### 5. Gallery

- Fixed **3×2** grid, **2×3** on phone portrait, replacing the
  `paperGridSize()` computation at `write_v5.html:2080` that could reach
  12 tiny tiles.
- Previews: `lineWidth` 1.25 → 2.6, higher backing resolution, scaled up
  to fill the panel, drawn over the card's pastel tile colour instead of
  white-on-white. The per-picture art functions in `PICTURE_ART` are not
  modified.
- Large arrows and page dots stay.
- The **Words** tab moves to the grown-up menu: it needs typing, so it is
  unusable to him and is only a fifth thing to mis-tap. Four tabs remain.

### 6. Top-right cluster and right edge

Three tiles — Undo, New page, Clean — differentiated on all three
channels he can use:

| Control | Colour | Shape | Position |
|---|---|---|---|
| Undo | amber `#f6a93b` | circle, `border-radius:50%` | first |
| New page | violet `#b9a7ff` | rounded square, `border-radius:20px` | second |
| Clean | teal `#6fd8c2` | squircle, `border-radius:34%` | last, after a 16 px gap |

The wide gap before Clean means a slip off Undo cannot reach the
destructive control. Tile size rises from 80 px to 96 px on tablet and
laptop, and from 56 px to 68 px on phone. Captions remain for the parent
but shrink. Redo is removed from the cluster entirely.

The right edge becomes four large targets: Next picture and the three
brush sizes. Mirror moves to the grown-up menu, where `gMirror` already
exists. Colour swatches rise from 56 px to 60 px on phone and 76 px to
80 px elsewhere.

`fitUI` currently injects Next picture into the cluster on phones,
producing four tiles at 4 px gaps — the worst case in the app. That
injection is removed; the gallery covers picture-changing on phone.

Delete the dead `SIZE_STEPS` and `rowsNeeded` (`write_v5.html:502-516`).
`fitUI` ignores them and hardcodes two size steps at line 554, so they
actively mislead anyone reading the file.

### 7. Feedback

Accepted taps keep the press animation and chime. **No-op taps get the
same press animation plus a softer chime**, so "nothing happened" still
feels answered. The only remaining silent case is a tap during active
scribbling. No toasts in child controls; he cannot read them.

### 8. Failure modes

- A lost `pointerup` is common on inexpensive touchscreens. A stroke idle
  for 2.5 s auto-finishes, so the interface can never stay wedged.
- `toggleSheet` reads the DOM rather than a tracked boolean, so the
  toggle cannot desync from what is on screen.
- Storage access keeps its existing `try`/`catch`; a cleared or blocked
  store must not break startup.

## Files

| File | Change |
|---|---|
| `write_v5.html` | **Untouched.** Preserved as the old version. |
| `write_v6.html` | New. Copied from `write_v5.html`, then overhauled. |
| `index.html` | Opens `write_v6.html`; keeps a link to `write_v5.html`. |
| `README.md` | Documents v6 behaviour and that v5 is retained. |
| `tests/toddler_checks.py` | Rewrite three assertions, add nine checks. |
| `tests/touch_checks.py` | Raise target-size minimums; retarget to v6. |
| `tests/browser_checks.py`, `tests/rainbow_checks.py` | Retarget to v6. |

Tests currently resolve the app as
`Path(__file__).resolve().parents[1]/'write_v5.html'`. They gain a shared
target so both versions can be checked, defaulting to v6.

## Testing

New checks in `tests/toddler_checks.py`:

1. Ten rapid taps on a tool all register; none are suppressed.
2. Double-tapping New page opens then closes the gallery; a third tap
   reopens it immediately.
3. A finger held down on the paper does not block a tool change.
4. A stroke that is actively moving *does* block a tool change.
5. Ten Clean taps on an already-clean page leave history depth unchanged,
   and one Undo restores the pre-clean drawing.
6. Exactly 6 cards per page across all ten viewport sizes, with no
   scrolling in the gallery.
7. Cluster tiles measure at least 68 px on phone and 96 px elsewhere,
   with at least 16 px of gap before Clean.
8. A tap equidistant between two cluster tiles selects neither.
9. No `data-cooldown` attribute survives anywhere in the document.

Rewritten, not deleted, because they encode behaviour being reversed on
purpose: `toddler_checks.py:17` (eager second tap ignored),
`toddler_checks.py:30` (mashing advances once), and the settle comment at
`toddler_checks.py:12`.

Device testing still required and not covered by Playwright: real
fullscreen, operating-system gestures, and stylus pressure.

## Out of scope

- Any change to `write_v5.html`.
- Culling the tool or colour set.
- A separate simplified "tiny mode" UI.
- Rewriting the drawing engine, brushes, bucket fill or tracing rewards.
