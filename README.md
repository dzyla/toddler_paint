# Little Art Studio

Open **write_v5.html** directly in your browser. It is the complete app: no server, installation, downloads, fonts, accounts, or internet connection required.

- All 12 original tools remain: crayon, pencil, marker, paint, spray, rainbow, neon, glitter, bubbles, stamps, bucket, and eraser. Brush sizes, tool cycling, and all four symmetry settings remain available. Tap the large More buttons for additional tools, colors, and stamps; grown-ups can optionally simplify it.
- 31 coloring pages, including an offline shape-page generator, 10 fillable pattern pages (mosaics, honeycombs, stained glass, quilts, color wheels, and more), plus 24 tracing activities, including two mazes, looping trails, spirals, branching trees, a fractal snowflake, alphabet, numbers, shapes, and custom words. Type a name or favorite word to make personal writing paper. New paper starts clean; Undo restores the previous paper and its artwork.
- Bucket colors stay within printed regions. Tap a painted region again to recolor it. Printed vector outlines stay above the paint, with smooth antialiased edges and no erased white fringes; tapping a printed line with the bucket does nothing. Plain paper uses your drawing as the bucket boundary.
- Textured crayons and pencils, bristled paint with color pickup, fine spray and glitter, translucent bubbles, and continuous rainbow strokes. Live previews use the same blending as finished marks. All ten drawing tools build pigment, coverage, or glow during uninterrupted retracing, including pressure-sensitive crayon strokes. Bucket fills replace regions; the eraser removes paint.
- The drawing surface fills the viewport, with controls floating at its edges. Resizing uses a single uniform scale, so circles, templates, and drawings keep their proportions. The retained workspace expands into newly exposed margins, preserving marks across orientation changes. Printed guides redraw at native device resolution; previews use higher-resolution canvases. Undo/redo, PNG export, and local autosave are included. Browser storage can be unavailable or cleared, so export pictures you want to keep.

Tap the padlock to request fullscreen and child mode. Hold it for **three seconds** for grown-up controls. This reduces accidental interruptions, but a webpage cannot prevent tab switching, operating-system shortcuts, or leaving the browser. Device parental controls, iOS Guided Access, or Android app pinning can provide additional restrictions. Desktop kiosk mode hides browser controls; it does not disable system shortcuts.

For example, on Linux, a separate Firefox kiosk window can be started with:

```sh
firefox --kiosk file:///absolute/path/to/write_v5.html
```

## Development checks

The optional tests are separate from the standalone app. With Python, Playwright, and its Chromium browser installed:

```sh
python tests/browser_checks.py
python tests/touch_checks.py
```

Checks cover bucket boundaries/recoloring, page undo/redo, generated page restoration, tracing, resize preservation, accidental tool changes during drawing, autosave, the parent hold, PNG download, every brush/template, continuous buildup for every drawing tool, simulated pressed-pen crayon input, smooth outline edges, isolated pattern fills, native Retina guide resolution, uniform scaling across repeated rotations, retained workspace margins, consistent preview blending, and four viewport layouts with no scrolling in child-facing controls or page pickers. Real-device fullscreen, operating-system gestures, and stylus pressure still need device testing.

## Touch layouts and publishing

Crayon is selected when the app opens. Laptop and tablet controls use 80px action buttons, 96px-wide tools, and 76px color tiles. Phones use targets of at least 56px, with tools along the bottom; short landscape screens use a compact arrangement. The two-row palette shows all 14 colors on larger screens and large paged tiles on phones. A check mark identifies the selected color. Pen and touch taps tolerate up to 28px of movement; drawing still blocks accidental tool changes. New page and Clean remain undoable.

The GitHub Actions workflow publishes the standalone app on each push to `main`. In repository Settings → Pages, choose **GitHub Actions** as the source. The intended address is https://dzyla.github.io/toddler_paint/. `index.html` also opens the app when serving this repository directly.
