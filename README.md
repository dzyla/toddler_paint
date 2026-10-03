# Little Art Studio

Open **write_v6.html** directly in your browser. It is the complete app: no server, installation, downloads, fonts, accounts, or internet connection required.

**write_v5.html** is kept unchanged as the previous version. `index.html` opens v6 and links to v5, and GitHub Pages publishes both. The optional checks drive v6 by default; set `ART_APP=write_v5.html` to run them against the old one.

- All 12 original tools remain: crayon, pencil, marker, paint, spray, rainbow, neon, glitter, bubbles, stamps, bucket, and eraser. Brush sizes and all four symmetry settings remain available. Laptops and tablets show all 12 tools and 14 colors. On phones, the large Tools and Colors buttons open the complete set in a tray, with no scrolling or paging; choosing one returns to drawing. Only the stamp collection uses More.
- 31 coloring pages, including an offline shape-page generator, 10 fillable pattern pages (mosaics, honeycombs, stained glass, quilts, color wheels, and more), plus 24 tracing activities, including two mazes, looping trails, spirals, branching trees, a fractal snowflake, alphabet, numbers, shapes, and custom words. Type a name or favorite word to make personal writing paper. New paper starts clean; Undo restores the previous paper and its artwork.
- Bucket colors stay within printed regions. Tap a painted region again to recolor it. Printed vector outlines stay above the paint, with smooth antialiased edges and no erased white fringes; tapping a printed line with the bucket does nothing. Plain paper uses your drawing as the bucket boundary.
- Textured crayons and pencils, bristled paint with color pickup, fine spray and glitter, translucent bubbles, and continuous rainbow strokes. Live previews use the same blending as finished marks. All ten drawing tools build pigment, coverage, or glow during uninterrupted retracing, including pressure-sensitive crayon strokes. Bucket fills replace regions; the eraser removes paint.
- The drawing surface fills the viewport; artwork fits into the space between controls so pictures remain reachable. Resizing uses a single uniform scale, so circles, templates, and drawings keep their proportions. The retained workspace expands into newly exposed margins, preserving marks across orientation changes. Printed guides redraw at native device resolution; previews use higher-resolution canvases. Undo/redo, PNG export, and local autosave are included. Browser storage can be unavailable or cleared, so export pictures you want to keep.

Tap the padlock to request fullscreen and child mode. Hold it for **three seconds** for grown-up controls. This reduces accidental interruptions, but a webpage cannot prevent tab switching, operating-system shortcuts, or leaving the browser. Device parental controls, iOS Guided Access, or Android app pinning can provide additional restrictions. Desktop kiosk mode hides browser controls; it does not disable system shortcuts.

For example, on Linux, a separate Firefox kiosk window can be started with:

```sh
firefox --kiosk file:///absolute/path/to/write_v6.html
```

## Toddler-friendly help

- **Every tap answers.** Controls act the moment his finger lands, not when it lifts, and no tap is ever silently discarded. Mashing is free rather than blocked: Clean on an already-clean page costs nothing and eats no undo step, and tapping the picture he is already on simply puts the gallery away. A tap that changes nothing still flashes and chimes, softly, so "nothing happened" still feels answered. Only Clean waits for the finger to lift, so a graze cannot wipe the page.
- **New page is a switch.** Tapping 📄 opens the picture gallery; tapping it again closes it. The button stays visible and reachable above the open gallery, and the big **Back** button is still there. Tapping beside the cards does nothing.
- **A resting finger no longer silences the app.** Only a stroke that is actually moving blocks a tool change, so a hand steadying the tablet costs him nothing. A stroke left stale by a lost touch no longer locks the paper either.
- **Forgiving taps.** A tap up to 40px outside a button still counts, and a finger or pen that slides while pressing still selects the button it started on. A tap landing equidistant between two buttons selects neither, because between Undo and Clean a wrong guess is worse than nothing.
- **Picture picker.** Six big cards per page with thick outlines over colour, a Surprise card, large arrows, and page dots. It always opens on the first page, so the cards he knows stay in the same places.
- **Stay in the lines.** On coloring and pattern pages, a stroke that starts inside a shape stays inside that shape, so wobbly scribbles still look tidy. Strokes that start on the open background draw freely. It can be turned off in the grown-up menu.
- **Rewards and practice.** Sparkles for fills, stamps and new pages. On tracing pages, sparkles and rising notes follow the pen while it stays on the dotted line, and a well-traced stroke earns a ⭐. Six fills on a coloring page also earn a star. Stars are counted on tablets and laptops. Soft notes play while drawing, higher near the top of the page; this can be turned off in the grown-up menu.

## Development checks

The optional tests are separate from the standalone app. With Python, Playwright, and its Chromium browser installed:

```sh
python tests/target_checks.py
python tests/browser_checks.py
python tests/touch_checks.py
python tests/rainbow_checks.py
python tests/toddler_checks.py
```

Checks cover bucket boundaries/recoloring, page undo/redo, generated page restoration, tracing, resize preservation, accidental tool changes during drawing, autosave, the parent hold, PNG download, every brush/template, continuous buildup for every drawing tool, simulated pressed-pen crayon input, smooth outline edges, isolated pattern fills, native Retina guide resolution, uniform scaling across repeated rotations, retained workspace margins, consistent preview blending, and four viewport layouts with no scrolling in child-facing controls or page pickers. They also cover instant pointerdown activation, no-op taps that still answer, two-finger taps, ambiguous gap taps that select neither button, resting fingers that no longer block controls, stale-stroke recovery, free Clean mashing, the New page toggle, six-card gallery pages across ten viewports, and the 64/96px action cluster. Real-device fullscreen, operating-system gestures, and stylus pressure still need device testing.

## Touch layouts and publishing

Crayon is selected when the app opens. The top-right cluster holds three controls — Undo (amber circle), New page (violet rounded square), and Clean (teal squircle behind a 16px gap) — at 96px on laptops and tablets and 64px on phones. Redo, Mirror, and the word-tracing form live in the grown-up menu; word paper is made there. Laptop and tablet controls use 96px action buttons, 96px-wide tools, and 80px color tiles. Smartphones (up to 600px wide, or up to 1000px wide in short landscape view) use a compact top action bar and two large bottom buttons for Tools and Colors. The canvas gets most of the screen. Each button opens a tray containing every tool or every color at once, with targets at least 56px wide. Choosing one automatically closes the tray; the artwork does not resize or shift. The buttons show the current tool and color, and Colors becomes Stamps when that tool is selected.

Pen and touch taps tolerate small slips; drawing still blocks accidental tool changes. The picture button cycles familiar pictures in one tap. The page picker offers the full collection, and changing paper keeps the chosen drawing tool. Page changes and Clean remain undoable. On phones, brush sizes, mirror settings, Redo, and Next picture are in the grown-up menu; the gallery covers picture-changing there. Rainbow uses brighter, gently layered color that stays vivid when scribbled over repeatedly. The touch checks cover ten viewport sizes, including small phones in both orientations.

The GitHub Actions workflow publishes the standalone app on each push to `main`. In repository Settings → Pages, choose **GitHub Actions** as the source. The intended address is https://dzyla.github.io/toddler_paint/. `index.html` also opens the app when serving this repository directly.
