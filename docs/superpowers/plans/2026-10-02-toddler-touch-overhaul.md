# Toddler Touch Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `write_v6.html`, a version of Little Art Studio whose controls answer a 2–3-year-old's every tap instantly, where mashing is harmless rather than blocked, leaving `write_v5.html` untouched.

**Architecture:** One tap engine replaces section 10 of the file. It resolves a target button on `pointerdown`, then dispatches a custom `toddlertap` event on it; every child-facing control listens for `toddlertap` instead of `click`, and native clicks on those panels are swallowed so nothing fires twice. Five silent timing guards are deleted, replaced by idempotent actions and a `drawingNow()` predicate that distinguishes a finger actively scribbling from one merely resting on the paper.

**Tech Stack:** Single standalone HTML file — vanilla ES2020, Canvas 2D, no build step, no network dependency. Tests are Python + Playwright driving Chromium.

**Spec:** `docs/superpowers/specs/2026-10-02-toddler-touch-overhaul-design.md`

## Global Constraints

- `write_v5.html` must not be modified by any task. Verify with `git diff --quiet -- write_v5.html` before every commit.
- `write_v6.html` stays a single self-contained file: no build step, no external fonts, no network requests, no new dependencies.
- Touch is the only input optimised for, but mouse and keyboard must keep working. No control may fire twice from one gesture.
- All 12 tools and 14 colours stay reachable on every layout.
- No control may carry a `data-cooldown` attribute when the work is done.
- Every child-facing tap produces visible press feedback plus a chime, including taps that change nothing.
- The drawing area must stay at least 50% of viewport height on phone layouts (`drawingBounds().height/viewH() >= .5`), which bounds how large controls may grow.
- Minimum touch target: 68px on phone layouts, 96px on tablet and laptop, for the action cluster.
- Exactly 6 gallery cards per page: 3×2, or 2×3 on phone portrait.
- Storage access stays wrapped in `try`/`catch`; a blocked or cleared store must not break startup.

## Deviation from the spec

The spec's section 8 called for a stroke idle 2.5 s to auto-finish on a timer.
Implemented as written, that would silently break a stroke whenever the child
held still for 2.5 s mid-scribble, splitting it in two and interrupting the
pigment buildup the brushes depend on. It is also no longer the fix it was
written to be: once `drawingNow()` ignores a stroke idle for 400 ms, an idle
stroke can no longer block the controls.

The real remaining wedge is the paper's own gate at `write_v6.html:1485` — a
lost `pointerup` leaves `activeId` set, so the child can never draw again. So
Task 3 applies the 2.5 s rule there instead: a *new* finger landing on the
paper takes over a stroke that has been idle longer than `STROKE_STALE_MS`.
Same constant, same failure covered, and it can never cut a live stroke short.

## Review Focus

These are the failure modes the spec implies but does not give a task. Each line's test is assigned to the task that owns the code.

1. **Double-firing.** Activating on `pointerdown` while the browser still delivers a native `click` would run every action twice — a double Clean, a double page change. Most likely failure in this plan, and silent. Test in Task 2.
2. **Two fingers at once.** A toddler taps two controls simultaneously; the per-panel single-slot `tap` state must not lose the second or leave a button stuck in `.press`. Test in Task 2.
3. **Larger controls starving the canvas.** Growing tiles to 96px and swatches to 80px can push `drawingBounds()` below half the viewport on 320×568 and 568×320. Test in Task 7.
4. **Stale stroke killing the paper.** If a `pointerup` is lost, `activeId` stays set and `hit`'s own gate means the child can never draw again, even though controls now work. Test in Task 3.
5. **`artIsEmpty()` on the largest canvas.** Clean scans the art canvas; on a rotated tablet that canvas can exceed 7M pixels, and the all-empty case is the full scan with no early exit. Must stay under 150ms and must not throw on a zero-sized canvas. Test in Task 4.

---

### Task 1: Create write_v6.html and a shared test target

Establishes the new file and makes every existing suite runnable against either version, so later tasks have a regression net.

**Files:**
- Create: `write_v6.html` (copied from `write_v5.html`)
- Create: `tests/app_target.py`
- Modify: `tests/browser_checks.py:4`, `tests/touch_checks.py:7`, `tests/rainbow_checks.py:7`, `tests/toddler_checks.py:4`
- Modify: `index.html`

**Interfaces:**
- Consumes: nothing.
- Produces: `tests/app_target.py` exporting `APP_URL: str` (a `file://` URI) and `APP_PATH: pathlib.Path`. Every later task's tests import `from app_target import APP_URL`.

- [ ] **Step 1: Write the failing test**

Create `tests/app_target.py` with no content yet, then write `tests/target_checks.py`:

```python
"""The shared app target resolves to write_v6.html by default, v5 on request."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.pop('ART_APP', None)
import app_target
assert app_target.APP_PATH.name == 'write_v6.html', app_target.APP_PATH
assert app_target.APP_PATH.exists(), 'write_v6.html must exist'
assert app_target.APP_URL.startswith('file://'), app_target.APP_URL

os.environ['ART_APP'] = 'write_v5.html'
import importlib
importlib.reload(app_target)
assert app_target.APP_PATH.name == 'write_v5.html', app_target.APP_PATH
print('PASS: shared app target defaults to v6 and honours ART_APP')
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python tests/target_checks.py`
Expected: FAIL — `AttributeError: module 'app_target' has no attribute 'APP_PATH'`

- [ ] **Step 3: Copy the app and write the target module**

```bash
cp write_v5.html write_v6.html
```

Write `tests/app_target.py`:

```python
"""Which app file the checks drive. Defaults to write_v6.html; set ART_APP to override."""
import os
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / os.environ.get('ART_APP', 'write_v6.html')
APP_URL = APP_PATH.as_uri()
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python tests/target_checks.py`
Expected: PASS

- [ ] **Step 5: Retarget the four existing suites**

In each of `tests/browser_checks.py`, `tests/touch_checks.py`, `tests/rainbow_checks.py`, `tests/toddler_checks.py`, add these three lines after the existing `from pathlib import Path` line:

```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app_target import APP_URL
```

Then replace each hardcoded target:

- `tests/browser_checks.py:4` — replace `URL=(Path(__file__).resolve().parents[1]/'write_v5.html').as_uri()` with `URL=APP_URL`
- `tests/toddler_checks.py:4` — same replacement
- `tests/touch_checks.py:7` — replace `page.goto((Path(__file__).resolve().parents[1]/'write_v5.html').as_uri())` with `page.goto(APP_URL)`
- `tests/rainbow_checks.py:7` — same replacement as touch_checks

- [ ] **Step 6: Point index.html at v6, keeping v5 reachable**

Replace the whole of `index.html`:

```html
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0;url=write_v6.html">
<title>Little Art Studio</title>
<a href="write_v6.html">Open Little Art Studio</a>
<p><a href="write_v5.html">Open the previous version</a></p>
</html>
```

- [ ] **Step 7: Run all five suites against v6 to confirm the copy behaves identically**

Run:
```bash
python tests/target_checks.py && python tests/browser_checks.py && \
python tests/touch_checks.py && python tests/rainbow_checks.py && python tests/toddler_checks.py
```
Expected: all PASS. They are driving `write_v6.html`, which is byte-identical to v5, so every assertion that passed before passes now.

- [ ] **Step 8: Confirm v5 is untouched and commit**

```bash
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html index.html tests/app_target.py tests/target_checks.py \
  tests/browser_checks.py tests/touch_checks.py tests/rainbow_checks.py tests/toddler_checks.py
git commit -m "Fork write_v6.html and give the checks a shared app target"
```

---

### Task 2: Replace the tap engine

The root fix. Controls fire on `pointerdown` via a `toddlertap` event, the five timing guards go, and ambiguous gap taps are refused.

**Files:**
- Modify: `write_v6.html` — section 10 "Touch controls", currently lines 1774-1838
- Modify: `write_v6.html:399,400,407` — remove `data-cooldown` attributes
- Modify: `write_v6.html:1872,1997,2021,2045,2128,2129,2130,2131` — `forgiving()` call sites keep working unchanged
- Modify: `write_v6.html:1951,2031,2108,2109,2110,2159,2160` — direct `click` listeners on child controls migrate to `toddlertap`
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `APP_URL` from Task 1.
- Produces, all callable from tests via `page.evaluate`:
  - `TAP_EVENT: string` — the constant `'toddlertap'`.
  - `forgiving(container: Element, selector: string, pick: (el: Element) => void): void` — unchanged signature, now listening for `toddlertap`.
  - `onTap(el: Element, handler: (ev: Event) => void): void` — binds a single element.
  - `resolveTapTarget(panel: Element, x: number, y: number): Element | null` — exported for the ambiguity test.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 2: the tap engine answers every tap ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')

    # No cooldown attributes survive.
    assert page.evaluate("document.querySelectorAll('[data-cooldown]').length")==0

    # Ten rapid taps on a tool all register, none suppressed.
    page.evaluate("()=>{window.toolCalls=0;const o=setTool;setTool=k=>{toolCalls++;o(k)}}")
    box=page.locator('[data-tool="pencil"]').bounding_box()
    cx,cy=box['x']+box['width']/2,box['y']+box['height']/2
    for _ in range(10):
        page.touchscreen.tap(cx,cy);page.wait_for_timeout(30)
    assert page.evaluate('toolCalls')==10,page.evaluate('toolCalls')
    assert page.evaluate('tool')=='pencil'

    # One gesture fires one action: pointerdown activation must not double-fire
    # alongside the browser's native click. (Review Focus 1)
    page.evaluate("()=>{window.toolCalls=0}")
    page.locator('[data-tool="marker"]').tap();page.wait_for_timeout(120)
    assert page.evaluate('toolCalls')==1,page.evaluate('toolCalls')
    page.evaluate("()=>{window.toolCalls=0}")
    page.locator('[data-tool="crayon"]').click();page.wait_for_timeout(120)
    assert page.evaluate('toolCalls')==1,page.evaluate('toolCalls')

    # Two fingers landing on two controls at once: both register, neither
    # button stays stuck in .press. (Review Focus 2)
    page.evaluate("()=>{window.toolCalls=0}")
    page.evaluate('''()=>{
      const a=document.querySelector('[data-tool="pencil"]'),b=document.querySelector('[data-tool="spray"]');
      const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
      const send=(el,r,id,type)=>el.dispatchEvent(new PointerEvent(type,
        {bubbles:true,pointerId:id,pointerType:'touch',clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
      a.setPointerCapture=()=>{};b.setPointerCapture=()=>{};
      send(a,ra,21,'pointerdown');send(b,rb,22,'pointerdown');
      send(a,ra,21,'pointerup');send(b,rb,22,'pointerup');
    }''')
    page.wait_for_timeout(120)
    assert page.evaluate('toolCalls')==2,page.evaluate('toolCalls')
    assert page.evaluate("document.querySelectorAll('.press').length")==0

    # A tap equidistant between two action tiles selects neither.
    gap=page.evaluate('''()=>{
      const u=document.getElementById('btnUndo'),p=document.getElementById('btnPaper');
      const a=u.getBoundingClientRect(),b=p.getBoundingClientRect();
      return [(a.right+b.left)/2,(a.top+a.bottom)/2];
    }''')
    assert page.evaluate('([x,y])=>resolveTapTarget(document.getElementById("actions"),x,y)===null',gap)

    # An unambiguous near miss still snaps to the nearest tile.
    near=page.evaluate('''()=>{const u=document.getElementById('btnUndo');
      const r=u.getBoundingClientRect();return [r.left-12,(r.top+r.bottom)/2];}''')
    assert page.evaluate('([x,y])=>resolveTapTarget(document.getElementById("actions"),x,y)?.id==="btnUndo"',near)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL at the `data-cooldown` assertion — three attributes still present at `write_v6.html:399,400,407`.

- [ ] **Step 3: Strip the cooldown attributes**

In `write_v6.html`, delete ` data-cooldown="1000"` from all three buttons:

```html
<button class="b act" id="btnPaper"><span class="ico">📄</span><span class="cap">New page</span></button>
<button class="b act" id="btnNew"><span class="ico">🧼</span><span class="cap">Clean</span></button>
```

and at line 407:

```html
<button class="b" id="btnNext" aria-label="Next picture"><span class="ico">🖼️</span><span class="cap">Next picture</span></button>
```

- [ ] **Step 4: Replace section 10 with the tap engine**

Replace everything in `write_v6.html` from `/* ==================================================================\n   10. Touch controls` through the end of `function forgiving(...)` (lines 1774-1838) with:

```javascript
/* ==================================================================
   10. Tap engine

   A two-year-old taps immediately, repeatedly, and often slightly off
   target. So controls act on pointerDOWN, under the finger, and no tap is
   ever silently discarded. Resolution happens once, here; every control
   then listens for one custom event.

   The browser still delivers a native click after a touch or mouse
   gesture. Because we already acted on pointerdown, that click would run
   the action a second time, so clicks on engine-owned panels are
   swallowed.
=================================================================== */
const TAP_EVENT='toddlertap';
const TAP_PANELS=['actions','rail','bottom','side','paperCard','phoneDock'];
const SNAP_PX=40;          // how far outside a button a tap still counts
const AMBIGUOUS=1.25;      // two candidates this close in distance: refuse
let lastPointerType='mouse';
document.addEventListener('pointerdown',e=>{lastPointerType=e.pointerType;},true);

// Clean is the only destructive control, so it alone waits for a release.
const UP_ONLY=new Set(['btnNew']);

function distanceTo(el,x,y){
  const r=el.getBoundingClientRect();
  if(!r.width||!r.height||!el.offsetParent)return Infinity;
  return Math.hypot(Math.max(r.left-x,0,x-r.right),Math.max(r.top-y,0,y-r.bottom));
}
// Exported for tests: which button a point belongs to, or null when a guess
// would be a coin flip. Between Undo and Clean, nothing beats a wrong guess.
function resolveTapTarget(panel,x,y){
  let best=null,bestD=Infinity,runnerUp=Infinity;
  for(const el of panel.querySelectorAll('button:not(:disabled):not([hidden])')){
    const d=distanceTo(el,x,y);
    if(d<bestD){runnerUp=bestD;bestD=d;best=el;}
    else if(d<runnerUp)runnerUp=d;
  }
  if(!best||bestD>SNAP_PX)return null;
  if(bestD>0 && runnerUp<=bestD*AMBIGUOUS)return null;
  return best;
}
function fireTap(button){
  pressFlash(button);
  button.dispatchEvent(new CustomEvent(TAP_EVENT,{bubbles:true}));
}
function pressFlash(button){
  button.classList.remove('press');void button.offsetWidth;button.classList.add('press');
  setTimeout(()=>button.classList.remove('press'),140);
}
for(const id of TAP_PANELS){
  const panel=document.getElementById(id);
  const pending=new Map();   // pointerId -> button, so two fingers both count
  panel.addEventListener('pointerdown',e=>{
    if(e.target.closest('input'))return;
    if(drawingNow())return;
    if(activeId!==null)finish();          // commit a resting finger's stroke
    const button=e.target.closest('button')||resolveTapTarget(panel,e.clientX,e.clientY);
    if(!button||button.disabled)return;
    e.preventDefault();
    swallowNextClick(button);
    if(UP_ONLY.has(button.id)){
      pending.set(e.pointerId,button);
      button.classList.add('press');
      try{button.setPointerCapture(e.pointerId);}catch(err){}
      return;
    }
    fireTap(button);
  });
  panel.addEventListener('pointerup',e=>{
    const button=pending.get(e.pointerId);
    if(!button)return;
    pending.delete(e.pointerId);
    button.classList.remove('press');
    // A generous slip: the release only has to land near where it started.
    if(distanceTo(button,e.clientX,e.clientY)<=SNAP_PX*2)fireTap(button);
  });
  const drop=e=>{
    const button=pending.get(e.pointerId);
    if(button){button.classList.remove('press');pending.delete(e.pointerId);}
  };
  panel.addEventListener('pointercancel',drop);
  panel.addEventListener('lostpointercapture',drop);
}
// One gesture, one action. The native click that follows our pointerdown is
// discarded; anything else on the page still clicks normally.
const swallowed=new Map();
function swallowNextClick(button){swallowed.set(button,performance.now());}
document.addEventListener('click',e=>{
  if(!e.isTrusted)return;
  for(const [button,when] of swallowed){
    if(performance.now()-when>900){swallowed.delete(button);continue;}
    if(button===e.target||button.contains(e.target)){
      swallowed.delete(button);
      e.preventDefault();e.stopImmediatePropagation();
      return;
    }
  }
},true);
// Keyboard parity: a focused control answers Enter and Space like a tap.
document.addEventListener('keydown',e=>{
  if(e.key!=='Enter'&&e.key!==' ')return;
  const button=e.target.closest&&e.target.closest('button');
  if(!button||button.disabled)return;
  if(!TAP_PANELS.some(id=>document.getElementById(id).contains(button)))return;
  e.preventDefault();fireTap(button);
});
function forgiving(container, sel, pick){
  container.addEventListener(TAP_EVENT,e=>{
    if(drawingNow())return;
    const el=e.target.closest(sel);
    if(!el||!container.contains(el)||el.disabled)return;
    pick(el);
  });
}
function onTap(el,handler){el.addEventListener(TAP_EVENT,handler);}
```

- [ ] **Step 5: Add the temporary `drawingNow` stub**

Task 3 implements it properly. For now, immediately above section 10, add:

```javascript
// Replaced in Task 3 by a movement-aware predicate.
function drawingNow(){return activeId!==null;}
```

- [ ] **Step 6: Migrate the child-facing `click` listeners to `toddlertap`**

Six sites. Replace each `addEventListener('click', ...)` with `onTap(...)`:

At `write_v6.html:1951` (Next picture):

```javascript
onTap(document.getElementById('btnNext'), e => {
  if(drawingNow())return;
  e.preventDefault();
  const favorites=['white','butterfly','fish','cat','dino','flower','rocket'];
  choosePaper({dataset:{paper:favorites[(favorites.indexOf(paperId)+1)%favorites.length]}});
  toast('New picture · Undo brings it back');
});
```

At `write_v6.html:2031` (mirror) change `document.getElementById('btnMirror').addEventListener('click', e => {` to `onTap(document.getElementById('btnMirror'), e => {` and its closing `});` stays as is, and change the inner `if(activeId!==null)return;` to `if(drawingNow())return;`.

At `write_v6.html:1993` (the More-colours button), replace:

```javascript
more.addEventListener('click',()=>{if(activeId!==null)return;palettePage++;buildBottom();});
```
with:
```javascript
onTap(more,()=>{if(drawingNow())return;palettePage++;buildBottom();});
```

At `write_v6.html:2108-2110` (gallery tabs and arrows):

```javascript
document.querySelectorAll('#paperTabs button').forEach(b=>onTap(b,()=>{
  if(paperCategory===b.dataset.category){chime(500,'sine',.04);return;}
  paperCategory=b.dataset.category;paperPage=0;buildPaperSheet();chime(640,'triangle');
}));
onTap(document.getElementById('paperPrev'),()=>{paperPage--;buildPaperSheet();chime(560,'triangle');});
onTap(document.getElementById('paperNext'),()=>{paperPage++;buildPaperSheet();chime(700,'triangle');});
```

At `write_v6.html:2159-2160` (phone dock):

```javascript
onTap(document.getElementById('phoneTools'),()=>openPhoneChoices('tools'));
onTap(document.getElementById('phoneColors'),()=>openPhoneChoices('colors'));
```

The `.closeSheet` buttons at `write_v6.html:2136` stay on `click`: they sit inside `paperCard` for the gallery (so the engine fires a tap, and the swallow stops the double) and inside grown-up sheets elsewhere, which the engine does not own. Change it to cover both:

```javascript
document.querySelectorAll('.closeSheet').forEach(b=>{b.addEventListener('click',closeSheets);onTap(b,closeSheets);});
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: the three pre-existing assertions at lines 17, 30 and the settle check now FAIL — they encode behaviour this task deliberately reverses. The new Task 2 assertions must PASS. If any new assertion fails, fix the engine before moving on.

- [ ] **Step 8: Rewrite the three obsolete assertions**

In `tests/toddler_checks.py`, replace the block at lines 12-30 with:

```python
        # The picker opens on the tap that presses New page.
        page.locator('#btnPaper').tap();page.wait_for_timeout(120)
        assert page.locator('#paperSheet').is_visible(),w
        # An eager second tap on a card is honoured at once: no dead half-second.
        page.locator('[data-paper="fish"]').tap();page.wait_for_timeout(120)
        assert page.locator('#paperSheet').is_hidden() and page.evaluate('paperId')=='fish',w
        # Tapping beside the cards never closes the picker.
        page.locator('#btnPaper').tap();page.wait_for_timeout(120)
        page.touchscreen.tap(3,h/2);page.wait_for_timeout(120)
        assert page.locator('#paperSheet').is_visible(),w
        page.locator('[data-paper="butterfly"]').tap();before=page.evaluate('artRevision')
        # The finger that just chose a page does not scribble on it.
        page.wait_for_timeout(160)
        assert page.evaluate('artRevision')==before,w
        assert page.locator('#paperSheet').is_hidden() and page.evaluate('paperId')=='butterfly',w
        # Three taps on Next picture advance three times: silence is what frustrates him.
        page.wait_for_timeout(200)
        page.evaluate("()=>{window.pageChanges=0;const o=choosePaper;window.choosePaper=el=>{pageChanges++;o(el)}}")
        box=page.locator('#btnNext').bounding_box()
        for _ in range(3):
            page.touchscreen.tap(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(120)
        assert page.evaluate('paperId')=='dino',(w,page.evaluate('paperId'))
        assert not errors,errors
```

Also update the module docstring at `tests/toddler_checks.py:1`:

```python
"""Toddler-proofing: instant taps, harmless mashing, stay-in-lines help, and tracing rewards."""
```

- [ ] **Step 9: Run the whole suite**

Run:
```bash
python tests/toddler_checks.py && python tests/touch_checks.py && \
python tests/browser_checks.py && python tests/rainbow_checks.py
```
Expected: all PASS.

- [ ] **Step 10: Confirm v5 untouched and commit**

```bash
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py
git commit -m "Answer every tap on pointerdown and drop the silent timing guards"
```

---

### Task 3: Stop a resting finger from killing the interface

`drawingNow()` becomes movement-aware, and a stale stroke no longer locks the paper.

**Files:**
- Modify: `write_v6.html` — `drawingNow()` stub from Task 2
- Modify: `write_v6.html:1484-1490` — `hit` pointerdown gate
- Modify: `write_v6.html:1525-1545` — `hit` pointermove, record movement time
- Modify: `write_v6.html:1833,2032,2153,2188,2426` — remaining `activeId!==null` guards
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `drawingNow()` stub, `TAP_EVENT` from Task 2.
- Produces:
  - `drawingNow(): boolean` — true only while a stroke has moved within `STROKE_IDLE_MS`.
  - `strokeIdleFor(): number` — milliseconds since the active stroke last moved, `Infinity` when none.
  - `STROKE_IDLE_MS: number` = `400`, `STROKE_STALE_MS: number` = `2500`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 3: a resting finger must not kill the interface ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("choosePaper({dataset:{paper:'white'}});setTool('crayon')")
    page.wait_for_timeout(200)

    hit=page.locator('#hit').bounding_box()
    hx,hy=hit['x']+hit['width']/2,hit['y']+hit['height']/2
    def finger(type_,pid,x,y):
        page.evaluate('''([type,pid,x,y])=>{
          const h=document.getElementById('hit');
          h.setPointerCapture=()=>{};
          h.dispatchEvent(new PointerEvent(type,{bubbles:true,pointerId:pid,pointerType:'touch',
            isPrimary:true,clientX:x,clientY:y,pressure:.5}));
        }''',[type_,pid,x,y])

    # A finger parked on the paper: the tool still changes.
    finger('pointerdown',31,hx,hy)
    page.wait_for_timeout(500)
    assert page.evaluate('activeId')==31
    assert page.evaluate('drawingNow()')==False
    page.locator('[data-tool="pencil"]').tap();page.wait_for_timeout(120)
    assert page.evaluate('tool')=='pencil',page.evaluate('tool')
    finger('pointerup',31,hx,hy)

    # A stroke that is actively moving still blocks a tool change.
    finger('pointerdown',32,hx,hy)
    for i in range(6):
        finger('pointermove',32,hx+i*9,hy+i*7);page.wait_for_timeout(16)
    assert page.evaluate('drawingNow()')==True
    page.locator('[data-tool="marker"]').tap();page.wait_for_timeout(60)
    assert page.evaluate('tool')=='pencil',page.evaluate('tool')
    finger('pointerup',32,hx+60,hy+50)

    # A lost pointerup must not lock the paper forever. (Review Focus 4)
    finger('pointerdown',33,hx,hy)
    page.wait_for_timeout(120)
    page.evaluate('()=>{stroke.lastMoveAt=performance.now()-9999}')
    assert page.evaluate('strokeIdleFor()')>2500
    before=page.evaluate('artRevision')
    finger('pointerdown',34,hx+40,hy+40)
    page.wait_for_timeout(60)
    assert page.evaluate('activeId')==34,page.evaluate('activeId')
    assert page.evaluate('artRevision')>before
    finger('pointerup',34,hx+40,hy+40)
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL — `page.evaluate('drawingNow()')` returns `True` for the parked finger, because the Task 2 stub only checks `activeId`.

- [ ] **Step 3: Implement the movement-aware predicate**

Replace the Task 2 stub with:

```javascript
/* A finger parked on the paper is not drawing. The old code could not tell
   the difference, so a toddler steadying a tablet with one hand silenced
   every control. Movement within the last STROKE_IDLE_MS is drawing;
   anything stiller than that yields to a deliberate tap. */
const STROKE_IDLE_MS=400,STROKE_STALE_MS=2500;
function strokeIdleFor(){
  if(activeId===null)return Infinity;
  return performance.now()-(stroke.lastMoveAt||0);
}
function drawingNow(){return activeId!==null && strokeIdleFor()<STROKE_IDLE_MS;}
```

- [ ] **Step 4: Record movement time**

In `hit`'s pointerdown handler at `write_v6.html:1489`, immediately after `activeId = e.pointerId;` add:

```javascript
  stroke.lastMoveAt = performance.now();
```

In `hit`'s pointermove handler, inside the `for (const ev of batch){` loop immediately after `const p = at(ev);` add:

```javascript
    stroke.lastMoveAt = performance.now();
```

- [ ] **Step 5: Let a new finger take over a stale stroke**

Replace the first line of `hit`'s pointerdown handler at `write_v6.html:1485`:

```javascript
  if (sheetOpen() || (e.pointerType === 'mouse' && e.button !== 0)) return;
  // A lost pointerup would otherwise lock the paper for good.
  if (activeId !== null){ if (strokeIdleFor() > STROKE_STALE_MS) finish(); else return; }
```

and drop the 350ms post-close guard on the next line to 150ms:

```javascript
  if (e.pointerType !== 'mouse' && performance.now()-sheetClosedAt < 150) return;
```

- [ ] **Step 6: Swap the remaining `activeId` guards**

Replace `activeId!==null` with `drawingNow()` at these five sites in `write_v6.html`: the `forgiving` body (already done in Task 2), the mirror handler (done in Task 2), `openPhoneChoices` (`if(activeId!==null)return;`), the grown-up hold handler (`if(holdTimer || activeId!==null)return;` becomes `if(holdTimer || drawingNow())return;`), and the keydown handler (`if(activeId!==null || (locked && !sheetOpen()))` becomes `if(drawingNow() || (locked && !sheetOpen()))`).

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: PASS

- [ ] **Step 8: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/touch_checks.py && python tests/browser_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py
git commit -m "Tell a resting finger apart from a drawing one"
```

---

### Task 4: Make mashing harmless

Repeat taps stop costing him anything: Clean on a clean page is free, re-choosing the open page just closes the gallery.

**Files:**
- Modify: `write_v6.html:1704-1710` — `freshPage()`
- Modify: `write_v6.html:2111-2122` — `choosePaper`
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `drawingNow()` from Task 3.
- Produces: `artIsEmpty(): boolean` — true when the art canvas holds no pixel with alpha above zero.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 4: mashing must cost him nothing ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("choosePaper({dataset:{paper:'white'}});setTool('crayon')")
    page.wait_for_timeout(200)
    page.evaluate('history_.reset()')

    assert page.evaluate('artIsEmpty()')==True

    # artIsEmpty must be cheap even on the largest canvas, and never throw. (Review Focus 5)
    cost=page.evaluate('()=>{const t=performance.now();artIsEmpty();return performance.now()-t}')
    assert cost<150,cost

    # Draw something, then mash Clean ten times.
    hit=page.locator('#hit').bounding_box()
    page.mouse.move(hit['x']+hit['width']*.4,hit['y']+hit['height']*.4)
    page.mouse.down()
    for i in range(10):page.mouse.move(hit['x']+hit['width']*.4+i*12,hit['y']+hit['height']*.4+i*9)
    page.mouse.up();page.wait_for_timeout(200)
    assert page.evaluate('artIsEmpty()')==False
    depth=page.evaluate('()=>undoDepth()')

    box=page.locator('#btnNew').bounding_box()
    cx,cy=box['x']+box['width']/2,box['y']+box['height']/2
    for _ in range(10):
        page.touchscreen.tap(cx,cy);page.wait_for_timeout(60)
    assert page.evaluate('artIsEmpty()')==True
    # Exactly one history entry for ten taps: the nine no-ops are free.
    assert page.evaluate('()=>undoDepth()')==depth+1,page.evaluate('()=>undoDepth()')
    # And one Undo brings his drawing back.
    page.locator('#btnUndo').tap();page.wait_for_timeout(300)
    assert page.evaluate('artIsEmpty()')==False

    # Re-choosing the page already open just closes the gallery.
    page.locator('#btnPaper').tap();page.wait_for_timeout(120)
    depth=page.evaluate('()=>undoDepth()')
    revision=page.evaluate('artRevision')
    page.locator('[data-paper="white"]').tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_hidden()
    assert page.evaluate('()=>undoDepth()')==depth,page.evaluate('()=>undoDepth()')
    assert page.evaluate('artRevision')==revision
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL — `artIsEmpty is not defined`.

- [ ] **Step 3: Add `artIsEmpty` and `undoDepth`**

Immediately above `function freshPage(){` in `write_v6.html`, add:

```javascript
/* Ten taps on Clean must not cost him ten undo slots, so a Clean that would
   change nothing records nothing. Early exit means the common case (art
   present) stops within a few rows; the full scan only happens when the page
   really is blank. */
function artIsEmpty(){
  const W=art.width,H=art.height;
  if(!W||!H)return true;
  let data;
  try{data=actx.getImageData(0,0,W,H).data;}catch(err){return false;}
  for(let i=3;i<data.length;i+=4)if(data[i])return false;
  return true;
}
```

Inside the `history_` IIFE at `write_v6.html:1690`, add a depth reader to the `api` object so tests can see history size without reaching into closures:

```javascript
    depth(){ return undo.length; },
```

and immediately after the IIFE's closing `})();` add:

```javascript
function undoDepth(){return history_.depth();}
```

- [ ] **Step 4: Make `freshPage` idempotent**

Replace `freshPage()` at `write_v6.html:1704`:

```javascript
function freshPage(){
  finish();
  if(artIsEmpty()){ chime(300,'sine',.04); return; }   // already clean: free
  history_.push();
  actx.save(); actx.setTransform(1,0,0,1,0,0);
  actx.clearRect(0,0,art.width,art.height); actx.restore();
  clearScratch(); chime(240,'sine'); toast('Fresh page'); scheduleSave();
}
```

- [ ] **Step 5: Make re-choosing the open page a no-op**

At the top of `choosePaper` in `write_v6.html:2112`, before `finish();history_.push();`:

```javascript
const choosePaper = el => {
  // Tapping the page he is already on just puts the gallery away.
  if(el.dataset.paper===paperId && el.dataset.paper!=='surprise'){
    closeSheets(); chime(520,'sine',.04); return;
  }
  finish();history_.push();
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: PASS

- [ ] **Step 7: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/touch_checks.py && python tests/browser_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py
git commit -m "Make repeat taps free instead of blocked"
```

---

### Task 5: New page becomes a real on/off toggle

**Files:**
- Modify: `write_v6.html:2045-2051` — the `actions` handler
- Modify: `write_v6.html:2164-2172` — `openSheet` / `closeSheets`
- Modify: `write_v6.html:310-314` — `#paperSheet` and `#paperCard` CSS
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `onTap`, `forgiving` from Task 2.
- Produces: `toggleSheet(id: string): void` — opens the sheet if closed, closes it if open, reading the live `.open` class.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 5: New page is an on/off toggle ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')

    paper=page.locator('#btnPaper')
    paper.tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_visible()
    # The button he pressed stays visible and reachable above the gallery.
    assert paper.is_visible()
    assert page.evaluate('''()=>{const b=document.getElementById('btnPaper');
      const r=b.getBoundingClientRect();
      return document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===b
          || b.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));}''')
    assert paper.get_attribute('aria-expanded')=='true'
    # Second tap closes it.
    paper.tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_hidden()
    assert paper.get_attribute('aria-expanded')=='false'
    # Third tap reopens immediately: no cooldown.
    paper.tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_visible()
    # The toggle reads the DOM, so closing by Back keeps it in step.
    page.locator('#paperFoot .closeSheet').tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_hidden()
    paper.tap();page.wait_for_timeout(150)
    assert page.locator('#paperSheet').is_visible()
    page.locator('#paperFoot .closeSheet').tap();page.wait_for_timeout(150)
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL — the second tap does not close the gallery; `#paperSheet` is still visible.

- [ ] **Step 3: Add `toggleSheet` and wire New page to it**

Immediately after `function sheetOpen(){ ... }` in `write_v6.html`, add:

```javascript
/* He asked for a switch, not a door that only opens. Reading the class
   rather than a tracked flag means Back and Escape keep the switch in step. */
function toggleSheet(id){
  const sheet=document.getElementById(id);
  if(sheet.classList.contains('open')){closeSheets();chime(430,'sine');}
  else openSheet(id);
  updateSheetToggles();
}
function updateSheetToggles(){
  const open=document.getElementById('paperSheet').classList.contains('open');
  const button=document.getElementById('btnPaper');
  button.setAttribute('aria-expanded',String(open));
  button.classList.toggle('sheetOpen',open);
  document.body.classList.toggle('pickingPaper',open);
}
```

Call `updateSheetToggles()` at the end of both `openSheet` and `closeSheets`.

In the `actions` handler at `write_v6.html:2049`, replace `else if (id === 'btnPaper') openSheet('paperSheet');` with:

```javascript
  else if (id === 'btnPaper') toggleSheet('paperSheet');
```

Add the initial attribute to the markup at `write_v6.html:399`:

```html
<button class="b act" id="btnPaper" aria-controls="paperSheet" aria-expanded="false"><span class="ico">📄</span><span class="cap">New page</span></button>
```

- [ ] **Step 4: Lift the cluster above the gallery and inset the card**

In the `#paperSheet` CSS block at `write_v6.html:310`, add:

```css
/* The button he pressed must stay under his finger, so the gallery makes room
   for the action cluster instead of covering it. */
body.pickingPaper #topRow{z-index:60}
body.pickingPaper #actions{pointer-events:auto}
#btnPaper.sheetOpen{box-shadow:0 0 0 5px var(--ink),0 6px 16px rgba(10,15,45,.3)}
#paperSheet{padding:12px;padding-top:calc(16px + var(--cluster-h,96px));background:#1d1f4acc}
#paperCard{height:calc(var(--app-h) - 28px - var(--cluster-h,96px))}
```

In `fitUI`, after the `applyStep(...)` call, publish the cluster height so the card can subtract it:

```javascript
  const cluster=document.getElementById('actions').getBoundingClientRect().height;
  r.setProperty('--cluster-h',Math.round(cluster)+'px');
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: PASS

- [ ] **Step 6: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/touch_checks.py && python tests/browser_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py
git commit -m "Turn New page into an on/off switch that stays reachable"
```

---

### Task 6: Six bold gallery cards

**Files:**
- Modify: `write_v6.html:2080-2086` — `paperGridSize()`
- Modify: `write_v6.html:2069-2071` — preview rendering in `paperButton`
- Modify: `write_v6.html:426` — `#paperTabs` markup, Words tab removed
- Modify: `write_v6.html:315` — `#paperTabs` CSS, five columns to four
- Modify: `write_v6.html` grown-up sheet markup at line 446 — add the Words entry
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `buildPaperSheet()`, `paperButton(p, index)` as they already exist.
- Produces: `paperGridSize(): {cols: number, rows: number}` — always 6 cells, `{cols:3,rows:2}` or `{cols:2,rows:3}` on phone portrait.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 6: six bold cards he can actually tell apart ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    for vw_,vh_ in [(1366,768),(1024,768),(768,1024),(390,844),(320,568),
                    (375,667),(600,960),(844,390),(667,375),(568,320)]:
        page.set_viewport_size({'width':vw_,'height':vh_});page.wait_for_timeout(250)
        size=page.evaluate('paperGridSize()')
        assert size['cols']*size['rows']==6,(vw_,vh_,size)
        if vh_>vw_ and page.evaluate('phoneLayout()'):
            assert size=={'cols':2,'rows':3},(vw_,vh_,size)
        else:
            assert size=={'cols':3,'rows':2},(vw_,vh_,size)
        page.locator('#btnPaper').tap();page.wait_for_timeout(200)
        cards=page.locator('#pictureGrid .b:visible').count()
        assert cards<=6 and cards>0,(vw_,vh_,cards)
        # No scrolling anywhere in the picker.
        assert page.evaluate("()=>{const c=document.getElementById('paperCard');"
                             "return c.scrollHeight<=c.clientHeight+1 && c.scrollWidth<=c.clientWidth+1}"),(vw_,vh_)
        # Previews are drawn boldly enough to read at arm's length.
        assert page.evaluate("()=>PREVIEW_LINE>=2.5")
        page.locator('#btnPaper').tap();page.wait_for_timeout(150)
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(250)

    # Four tabs: Words needs typing, so it lives with the grown-ups now.
    page.locator('#btnPaper').tap();page.wait_for_timeout(200)
    assert page.locator('#paperTabs button').count()==4
    assert page.locator('#paperTabs [data-category="words"]').count()==0
    page.locator('#btnPaper').tap();page.wait_for_timeout(150)
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL — `paperGridSize()` returns computed values such as `{cols:4,rows:3}` on 1366×768, not 6 cells.

- [ ] **Step 3: Fix the grid at six cells**

Replace `paperGridSize()` at `write_v6.html:2080`:

```javascript
/* Six cards, never twelve. A two-year-old cannot pick out a silhouette from a
   grid of tiny tiles, and he would rather tap a big arrow than squint. */
function paperGridSize(){
  const portraitPhone=phoneLayout() && viewH()>viewW();
  return portraitPhone?{cols:2,rows:3}:{cols:3,rows:2};
}
```

- [ ] **Step 4: Draw the previews boldly**

Replace the preview branch in `paperButton` at `write_v6.html:2069`:

```javascript
  if(PICTURE_ART[p.id]){
    // Thick lines over the card's own colour: the silhouette has to read from
    // across the room, not at reading distance.
    const preview=document.createElement('canvas');
    preview.width=560;preview.height=420;preview.className='preview';
    const c=preview.getContext('2d');
    c.fillStyle=TILE_COLORS[index%TILE_COLORS.length];
    c.fillRect(0,0,preview.width,preview.height);
    c.translate(105,35);c.scale(3.5,3.5);
    c.lineWidth=PREVIEW_LINE;c.traceWidth=PREVIEW_LINE*.76;
    c.strokeStyle='#232746';c.lineJoin='round';c.lineCap='round';
    PICTURE_ART[p.id](c);
    el.appendChild(preview);
  }
```

Define the constant immediately above `function paperButton(`:

```javascript
const PREVIEW_LINE=2.6;
```

- [ ] **Step 5: Move the Words tab into the grown-up sheet**

At `write_v6.html:426`, drop the Words tab:

```html
<div id="paperTabs"><button data-category="picture"><b>🎨</b>Color</button><button data-category="pattern"><b>🔷</b>Patterns</button><button data-category="trace"><b>✏️</b>Trace</button><button data-category="plain"><b>📄</b>Blank</button></div>
```

At `write_v6.html:315`, change the tab grid to four columns:

```css
#paperTabs{grid-area:tabs;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
```

Move `#wordForm` out of `#paperCard` and into the grown-up sheet, immediately before `<div id="grownOptions"></div>` at `write_v6.html:446`. Then in `buildPaperSheet`, delete the line `document.getElementById('wordForm').hidden=paperCategory!=='words';` and simplify the pager lines, since `words` is no longer a category:

```javascript
  const pager=document.getElementById('paperPager');
  pager.innerHTML=Array.from({length:pages},(_,i)=>`<i class="${i===paperPage?'on':''}"></i>`).join('');
  pager.setAttribute('aria-label',`Page ${paperPage+1} of ${pages}`);
  document.getElementById('paperPrev').disabled=paperPage===0;
  document.getElementById('paperNext').disabled=paperPage===pages-1;
```

In the `wordForm` submit handler, add `closeSheets();` after `scheduleSave();` so making tracing paper returns the grown-up to the art.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: PASS

- [ ] **Step 7: Check the word-paper path still works end to end**

Run: `python tests/browser_checks.py`
Expected: PASS. `browser_checks.py` drives `select_paper` by category; if it referenced the `words` category it must now open the grown-up sheet by holding `#grown`. Inspect and update that helper if it fails.

- [ ] **Step 8: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/touch_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py tests/browser_checks.py
git commit -m "Show six bold gallery cards and move word paper to the grown-ups"
```

---

### Task 7: Rebuild the action cluster and right edge

**Files:**
- Modify: `write_v6.html:396-402` — `#topRow` markup, Redo removed
- Modify: `write_v6.html:406-412` — `#side` markup, Mirror removed
- Modify: `write_v6.html:446` — grown-up sheet gains Mirror
- Modify: `write_v6.html:502-516` — delete `SIZE_STEPS` and `rowsNeeded`
- Modify: `write_v6.html:549-556` — `fitUI` sizes and the phone `btnNext` injection
- Modify: `write_v6.html:238-242,264-268,279-284` — cluster CSS
- Test: `tests/toddler_checks.py`, `tests/touch_checks.py`

**Interfaces:**
- Consumes: `fitUI()`, `applyStep(step)` as they already exist.
- Produces: `clusterMinSize(): number` — `68` on phone layouts, `96` otherwise; used by tests and by `applyStep`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 7: three tiles he can tell apart and cannot confuse ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    for vw_,vh_ in [(1366,768),(1024,768),(768,1024),(390,844),(320,568),
                    (375,667),(600,960),(844,390),(667,375),(568,320)]:
        page.set_viewport_size({'width':vw_,'height':vh_});page.wait_for_timeout(250)
        phone=page.evaluate('phoneLayout()')
        ids=page.evaluate("()=>[...document.querySelectorAll('#actions button')]"
                          ".filter(b=>b.offsetParent).map(b=>b.id)")
        assert ids==['btnUndo','btnPaper','btnNew'],(vw_,vh_,ids)
        floor=page.evaluate('clusterMinSize()')
        assert floor==(68 if phone else 96),(vw_,vh_,floor)
        for id_ in ids:
            box=page.locator('#'+id_).bounding_box()
            assert box['w']>=floor-.5 and box['h']>=floor-.5,(vw_,vh_,id_,box,floor)
        # A slip off New page must not be able to reach Clean.
        gap=page.evaluate('''()=>{const p=document.getElementById('btnPaper').getBoundingClientRect();
          const n=document.getElementById('btnNew').getBoundingClientRect();return n.left-p.right;}''')
        assert gap>=15.5,(vw_,vh_,gap)
        # Three channels of difference: colour, shape, icon size.
        shapes=page.evaluate("()=>['btnUndo','btnPaper','btnNew'].map(i=>{"
                             "const s=getComputedStyle(document.getElementById(i));"
                             "return s.borderRadius+'|'+s.backgroundColor})")
        assert len(set(shapes))==3,(vw_,vh_,shapes)
        # Larger controls must not starve the paper. (Review Focus 3)
        assert page.evaluate('drawingBounds().height/viewH()')>=.5,(vw_,vh_,page.evaluate('drawingBounds()'))
        # Right edge: Next picture plus three sizes, no mirror.
        if not phone:
            side=page.evaluate("()=>[...document.querySelectorAll('#side button')]"
                               ".filter(b=>b.offsetParent).map(b=>b.id||b.dataset.size)")
            assert side==['btnNext','small','medium','large'],(vw_,vh_,side)
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(250)
    assert page.evaluate("!!document.getElementById('btnRedo')")==False
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL — the cluster still lists `btnUndo, btnRedo, btnPaper, btnNew`.

- [ ] **Step 3: Rebuild the markup**

Replace the `#actions` panel at `write_v6.html:398-402`:

```html
    <div class="panel" id="actions">
      <button class="b act" id="btnUndo"><span class="ico">↩️</span><span class="cap">Undo</span></button>
      <button class="b act" id="btnPaper" aria-controls="paperSheet" aria-expanded="false"><span class="ico">📄</span><span class="cap">New page</span></button>
      <button class="b act" id="btnNew"><span class="ico">🧼</span><span class="cap">Clean</span></button>
    </div>
```

Replace `#side` at `write_v6.html:406-412`:

```html
  <div class="panel" id="side">
    <button class="b" id="btnNext" aria-label="Next picture"><span class="ico">🖼️</span><span class="cap">Next picture</span></button>
    <button class="b size" data-size="small"><i style="width:8px;height:8px"></i></button>
    <button class="b size on" data-size="medium"><i style="width:16px;height:16px"></i></button>
    <button class="b size" data-size="large"><i style="width:26px;height:26px"></i></button>
  </div>
```

Remove the now-dangling references: in `history_.ui()` delete the line setting `btnRedo.disabled`, and in the `actions` handler delete `else if (id === 'btnRedo') history_.redo();`. The grown-up sheet already carries `gRedo` and `gMirror`, so nothing is lost.

Delete the CSS rules that referenced the removed buttons: `#actions #btnRedo{display:none}` and `.phone #actions #btnRedo{display:none}`.

- [ ] **Step 4: Differentiate the three tiles**

Replace the toddler-sized-controls CSS block at `write_v6.html:238-242`:

```css
/* Colour, shape and icon size all differ, because he reads none of the words.
   Clean sits last behind a wide gap: a slip off New page must not wipe his
   picture. */
#actions{gap:8px}
#actions .cap{display:block;font-size:13px;opacity:1}
#actions .ico{font-size:32px}
#btnUndo{background:#f6a93b;border-radius:50%}
#btnUndo .ico{font-size:36px}
#btnPaper{background:#b9a7ff;border-radius:20px}
#btnNew{background:#6fd8c2;border-radius:34%;margin-left:16px}
#btnNew .ico{font-size:28px}
```

- [ ] **Step 5: Enlarge the targets and stop the phone injection**

Delete `SIZE_STEPS` (lines 502-511) and `rowsNeeded` (lines 513-516) entirely: `fitUI` has always ignored them, and they misreport the real sizes.

Add above `fitUI`:

```javascript
function clusterMinSize(){return phoneLayout()?68:96;}
```

In `fitUI`, replace the final `applyStep(...)` call:

```javascript
  applyStep(compact ? {toolW:56,toolH:64,sw:60,act:68,ico:28,cap:11,st:32} :
    {toolW:96,toolH:88,sw:80,act:96,ico:34,cap:13,st:38});
```

and delete the phone injection of Next picture, replacing this block:

```javascript
  if(compact){
    const actionsPanel=document.getElementById('actions');
    if(nextPicture.parentElement!==actionsPanel)actionsPanel.insertBefore(nextPicture,document.getElementById('btnPaper'));
  }else if(nextPicture.parentElement!==sidePanel)sidePanel.prepend(nextPicture);
```

with:

```javascript
  // Four cramped tiles was the worst target in the app. On phones the gallery
  // covers picture-changing, so Next picture travels with the side panel.
  if(nextPicture.parentElement!==sidePanel)sidePanel.prepend(nextPicture);
```

- [ ] **Step 6: Add Mirror to the grown-up sheet and remove the child one**

`gMirror` already exists at `write_v6.html:446` and currently works by clicking `#btnMirror`, which no longer exists. Delete `write_v6.html:2029-2041` entirely — that is the `const MIRROR = [...]` declaration through the closing `});` of the `btnMirror` listener — and delete the `gMirror` listener at `write_v6.html:2138`. Replace both with one block placed where line 2029 was:

```javascript
const MIRROR=[{n:1,ico:'🦋',cap:'Off'},{n:2,ico:'🪞',cap:'Mirror'},
              {n:4,ico:'🍀',cap:'Four'},{n:8,ico:'❄️',cap:'Snowflake'}];
function cycleMirror(){
  const next=MIRROR[(MIRROR.findIndex(m=>m.n===symmetry)+1)%MIRROR.length];
  symmetry=next.n;
  const b=document.getElementById('gMirror');
  b.querySelector('.ico').textContent=next.ico;
  b.querySelector('.cap').textContent=next.n===1?'Mirror off':next.cap;
  toast(next.n===1?'Mirror off':next.cap+' magic');
  chime(400+next.n*40,'triangle');
}
document.getElementById('gMirror').addEventListener('click',()=>{cycleMirror();});
```

Verify nothing references the removed button: `grep -n "btnMirror" write_v6.html` must print nothing.

- [ ] **Step 7: Raise the target minimums in touch_checks**

In `tests/touch_checks.py:14`, change the default minimum and the cluster call:

```python
        def targets(selector,minimum=None):
            floor=minimum if minimum is not None else page.evaluate('clusterMinSize()')
            for box in page.locator(selector).evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})'):
                assert box['w']>=floor-.5 and box['h']>=floor-.5,(w,h,selector,box,floor)
                assert box['x']>=0 and box['y']>=0 and box['x']+box['w']<=w+.1 and box['y']+box['h']<=h+.1,(w,h,selector,box)
```

Leave `targets('#rail .tool')` and `targets('#phoneDock button')` calling with `minimum=56`, since tools and the dock keep their size.

Then fix the two assertions at `tests/touch_checks.py:72-76` that drive `#btnNext` on a phone layout — `btnNext` now lives in `#side`, which moves into `grownOptions` on phones. That block runs at 1280×900, which is not a phone layout, so it keeps working; confirm by running the suite.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py && python tests/touch_checks.py`
Expected: PASS. If `drawingBounds().height/viewH() >= .5` fails on 320×568 or 568×320, reduce the phone `act` value from 68 toward 64 and re-run; the 68px floor is a target, the half-viewport canvas is a hard constraint, so lower the floor and record the real value in `clusterMinSize()`.

- [ ] **Step 9: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/browser_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py tests/touch_checks.py
git commit -m "Rebuild the action cluster as three unmistakable tiles"
```

---

### Task 8: Every tap answers, including the ones that change nothing

**Files:**
- Modify: `write_v6.html:1937-1950` — `setTool`
- Modify: `write_v6.html:2003-2011` — `setColor`
- Test: `tests/toddler_checks.py`

**Interfaces:**
- Consumes: `pressFlash` from Task 2, `chime(freq, type, volume, length)` as it exists.
- Produces: no new exports. `window.chimes` is instrumented by the test only.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toddler_checks.py`, before the final `print`:

```python
    # --- Task 8: a tap that changes nothing still answers ---
    page.goto(URL);page.click('#setupDone');page.wait_for_timeout(300)
    page.evaluate('soundOn=false')
    page.evaluate("()=>{window.chimes=[];const o=chime;window.chime=(f,t,v,l)=>{chimes.push([f,v===undefined?.07:v]);o(f,t,v,l)}}")

    # Re-tapping the tool already chosen: press animation and a softer chime.
    page.evaluate("setTool('crayon')")
    page.evaluate('()=>{chimes.length=0}')
    page.locator('[data-tool="crayon"]').tap();page.wait_for_timeout(200)
    assert page.evaluate('chimes.length')>=1,page.evaluate('chimes')
    quiet=page.evaluate('chimes[chimes.length-1][1]')

    page.evaluate('()=>{chimes.length=0}')
    page.locator('[data-tool="pencil"]').tap();page.wait_for_timeout(200)
    loud=page.evaluate('chimes[chimes.length-1][1]')
    assert quiet<loud,(quiet,loud)

    # Every engine-owned tap flashes .press, changed or not.
    flashed=page.evaluate('''()=>new Promise(resolve=>{
      const b=document.querySelector('[data-tool="pencil"]');
      let seen=false;
      const mo=new MutationObserver(()=>{if(b.classList.contains('press'))seen=true});
      mo.observe(b,{attributes:true,attributeFilter:['class']});
      const r=b.getBoundingClientRect();
      b.setPointerCapture=()=>{};
      b.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:41,pointerType:'touch',
        clientX:r.left+r.width/2,clientY:r.top+r.height/2}));
      setTimeout(()=>{mo.disconnect();resolve(seen)},80);
    })''')
    assert flashed==True
    assert not errors,errors
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python tests/toddler_checks.py`
Expected: FAIL at `quiet<loud` — `setTool` chimes at the same volume whether or not the tool changed.

- [ ] **Step 3: Soften the no-op chime**

Replace the last two lines of `setTool` at `write_v6.html:1948`:

```javascript
  // A tap that changes nothing still has to feel answered, just quieter.
  if(changed){pop(toolBtn[key]);pop(document.getElementById('phoneTools'));}
  chime(320 + TOOL_ORDER.indexOf(key)*38, 'triangle', changed?.07:.03);
```

Replace the last two lines of `setColor` at `write_v6.html:2009`:

```javascript
  const changed = color !== col;
  ...
  pop(bottom.querySelector('.sw.on'));pop(document.getElementById('phoneColors'));
  chime(500,'sine',changed?.07:.03);
```

`setColor` assigns `color = col` on its first line, so capture `changed` before that assignment:

```javascript
function setColor(col){
  const changed = color !== col;
  color = col;
  if (tool === 'eraser') setTool('crayon');
  else buildBottom();
  drawAllSamples();
  document.getElementById('stDot').style.background = col;
  pop(bottom.querySelector('.sw.on'));pop(document.getElementById('phoneColors'));
  chime(500,'sine',changed?.07:.03);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python tests/toddler_checks.py`
Expected: PASS

- [ ] **Step 5: Run the whole suite, confirm v5 untouched, commit**

```bash
python tests/touch_checks.py && python tests/browser_checks.py && python tests/rainbow_checks.py
git diff --quiet -- write_v5.html && echo "v5 clean"
git add write_v6.html tests/toddler_checks.py
git commit -m "Answer no-op taps with a softer chime instead of silence"
```

---

### Task 9: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/` — whichever workflow publishes the app
- Test: all five suites

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Publish v6 as the site, keeping v5 reachable**

`.github/workflows/pages.yml:22-27` copies a hardcoded file list, and today that
list is v5 only. Replace the `Prepare standalone site` run block:

```yaml
      - name: Prepare standalone site
        run: |
          mkdir _site
          cp write_v6.html _site/index.html
          cp write_v6.html _site/write_v6.html
          cp write_v5.html _site/write_v5.html
          touch _site/.nojekyll
```

Verify the YAML still parses:

```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pages.yml')); print('ok')"
```
Expected: `ok`

- [ ] **Step 2: Rewrite the README sections that describe the old behaviour**

The "Toddler-friendly help" section currently promises the opposite of what v6 does. Replace its first two bullets:

```markdown
- **Every tap answers.** Controls act the moment his finger lands, not when
  it lifts, and no tap is ever silently discarded. Mashing a button is free
  rather than blocked: Clean on an already-clean page costs nothing and eats
  no undo step, and tapping the picture he is already on simply puts the
  gallery away. A tap that changes nothing still flashes and chimes, softly,
  so "nothing happened" still feels answered. Only Clean waits for the
  finger to lift, so a graze cannot wipe the page.
- **New page is a switch.** Tapping 📄 opens the picture gallery; tapping it
  again closes it. The button stays visible and reachable above the open
  gallery, and the big Back button is still there. A finger resting on the
  paper no longer silences the controls — only a stroke that is actually
  moving blocks a tool change.
- **Forgiving taps.** A tap up to 40px outside a button still counts, and a
  finger that slides while pressing still selects the button it started on.
  A tap landing equidistant between two buttons selects neither, because
  between Undo and Clean a wrong guess is worse than nothing.
- **Picture picker.** Six big cards per page with thick outlines over colour,
  a Surprise card, large arrows, and page dots.
```

Add to the "Touch layouts and publishing" section:

```markdown
The top-right cluster holds three controls — Undo (amber circle), New page
(violet rounded square), and Clean (teal squircle behind a 16px gap) — at
96px on laptops and tablets and 68px on phones. Redo, Mirror, and the
word-tracing form live in the grown-up menu. Word paper is made there.
```

Add near the top of the README:

```markdown
Open **write_v6.html** for the current app. **write_v5.html** is kept
unchanged as the previous version; `index.html` opens v6 and links to v5.
The optional checks drive v6 by default — set `ART_APP=write_v5.html` to
run them against the old one.
```

- [ ] **Step 3: Update the development-checks list**

In the "Development checks" section, add `python tests/target_checks.py` to the command list and replace the coverage sentence's tail with:

```markdown
instant pointerdown activation, no-op taps that still answer, two-finger
taps, ambiguous gap taps, resting fingers that no longer block controls,
stale-stroke recovery, free Clean mashing, the New page toggle, six-card
gallery pages across ten viewports, and the 68/96px action cluster.
```

- [ ] **Step 4: Run every suite against v6**

Run:
```bash
python tests/target_checks.py && python tests/browser_checks.py && \
python tests/touch_checks.py && python tests/rainbow_checks.py && python tests/toddler_checks.py
```
Expected: all five PASS.

- [ ] **Step 5: Run the old suites against v5 to prove it still works**

Run:
```bash
ART_APP=write_v5.html python tests/touch_checks.py
ART_APP=write_v5.html python tests/rainbow_checks.py
```
Expected: PASS. `toddler_checks.py` and parts of `touch_checks.py` now assert v6 behaviour, so failures there against v5 are expected and correct — note which, and do not "fix" them.

- [ ] **Step 6: Confirm v5 untouched and commit**

```bash
git diff --quiet -- write_v5.html && echo "v5 clean"
git add README.md .github
git commit -m "Document the v6 touch overhaul and keep v5 as the previous version"
```

- [ ] **Step 7: Verify the whole branch**

Run: `git log --oneline main..HEAD` and confirm nine commits, none touching `write_v5.html`:

```bash
git log --oneline --name-only main..HEAD | grep -c write_v5.html
```
Expected: `0`
