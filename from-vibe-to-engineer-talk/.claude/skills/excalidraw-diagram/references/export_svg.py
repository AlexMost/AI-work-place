"""Export Excalidraw JSON to a standalone .svg file (vector, embeddable in slides).

Unlike render_excalidraw.py (which screenshots a PNG for visual validation), this
serializes the real SVG that Excalidraw produces — crisp at any size and, by default,
transparent so it blends onto any slide background.

Usage:
    cd .claude/skills/excalidraw-diagram/references
    uv run python export_svg.py <path-to-file.excalidraw> [--output path.svg] [--solid]

--solid keeps the file's viewBackgroundColor instead of exporting transparent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def export(excalidraw_path: Path, output_path: Path | None, transparent: bool) -> Path:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: uv sync && uv run playwright install chromium", file=sys.stderr)
        sys.exit(1)

    raw = excalidraw_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {excalidraw_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if data.get("type") != "excalidraw" or not data.get("elements"):
        print("ERROR: Not a valid non-empty Excalidraw file.", file=sys.stderr)
        sys.exit(1)

    data.setdefault("appState", {})
    if transparent:
        data["appState"]["exportBackground"] = False

    if output_path is None:
        output_path = excalidraw_path.with_suffix(".svg")

    template_url = (Path(__file__).parent / "render_template.html").as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(template_url)
        page.wait_for_function("window.__moduleReady === true", timeout=60000)
        result = page.evaluate(f"window.renderDiagram({json.dumps(data)})")
        if not result or not result.get("success"):
            err = result.get("error") if result else "renderDiagram returned null"
            print(f"ERROR: Export failed: {err}", file=sys.stderr)
            browser.close()
            sys.exit(1)
        page.wait_for_function("window.__renderComplete === true", timeout=15000)
        svg_markup = page.eval_on_selector("#root svg", "el => el.outerHTML")
        browser.close()

    output_path.write_text(svg_markup, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Excalidraw JSON to SVG")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", type=Path, default=None)
    parser.add_argument("--solid", action="store_true", help="Keep the file background instead of transparent")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    out = export(args.input, args.output, transparent=not args.solid)
    print(str(out))


if __name__ == "__main__":
    main()
