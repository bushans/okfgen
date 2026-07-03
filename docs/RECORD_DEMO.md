# The hero demo GIF

The README hero is `docs/demo.gif`.

## Option A — generate it (zero effort, no screen recorder)

```bash
python scripts/make_demo_gif.py     # -> docs/demo.gif
```

This renders the animated terminal + settling knowledge graph entirely with
Pillow — deterministic, offline, free. It's what currently ships as the hero.
Tweak the transcript or nodes in `scripts/make_demo_gif.py` and re-run.

## Option B — record the real thing (more authentic)

A screen capture of the actual interactive graph is even more compelling
(~15–20s):

**Storyboard**
1. `okfgen generate ./samples/recipes/acme_sales.schema.json -o out/acme`
2. `okfgen enrich out/acme`
3. `okfgen visualize out/acme -o out/acme/graph.html`
4. Open `graph.html` — drag a node, scroll to zoom, click a table to show its
   join paths. End on the graph in motion.

**Tools that make a clean terminal GIF**
- [vhs](https://github.com/charmbracelet/vhs) (scriptable, best for reproducibility) — write a `.tape` file for steps 1–3.
- or [terminalizer](https://github.com/faressoft/terminalizer) / [asciinema](https://asciinema.org) + `agg`.
- Capture the browser graph with [ScreenToGif](https://www.screentogif.com/) (Windows) or Kap (macOS).

**Export**
- Target width ~860px, < 5 MB, 12–15 fps. Save as `docs/demo.gif`.
- The README's hero `<img>` already points at it — once committed, it replaces
  the SVG automatically (uncomment the demo `<img>` block at the top of README).
