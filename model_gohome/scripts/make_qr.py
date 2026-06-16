"""make_qr.py — generate a poster-styled QR code that points to a URL (e.g. a page
or folder hosting the field GIFs).

A QR can only encode a URL, so the GIFs must first live at a PUBLIC link (GitHub /
GitHub Pages, a shared Google Drive / Dropbox folder, a personal site, etc.). Pass that
link with --url and this writes a high-contrast, colorblind-safe QR (dark navy modules
on white) as SVG (vector, best for print) and PNG.

Requires segno (pure-Python, no other deps):  pip install segno

Usage:
    python3 scripts/make_qr.py --url "https://your-link-to-the-gifs"
    python3 scripts/make_qr.py --url "https://..." --out poster_qr --scale 12 \
        --dark "#1B2A4A" --light "#FFFFFF" --output-dir out_gohome_events
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402


def main():
    url = C.get_opt("--url")
    if not url:
        print("ERROR: provide the public URL the QR should open, e.g.")
        print('   python3 scripts/make_qr.py --url "https://your-link-to-the-gifs"')
        sys.exit(2)
    try:
        import segno
    except ImportError:
        print("ERROR: segno not installed. Run:  pip install segno")
        sys.exit(2)

    output_dir = C.get_opt("--output-dir")
    name = C.get_opt("--out", "poster_qr")
    scale = int(C.get_opt("--scale", "12"))
    border = int(C.get_opt("--border", "4"))            # quiet zone (>=4 recommended)
    dark = C.get_opt("--dark", C.PALETTE["ink"])        # navy modules = high contrast
    light = C.get_opt("--light", "#FFFFFF")             # white background = scannable
    fig_dir = C.figures_dir(output_dir)

    # error correction 'H' (~30%) so a small logo/scuff won't break scanning on a poster
    qr = segno.make(url, error="h")
    svg_path = os.path.join(fig_dir, name + ".svg")
    png_path = os.path.join(fig_dir, name + ".png")
    qr.save(svg_path, scale=scale, border=border, dark=dark, light=light)
    qr.save(png_path, scale=scale, border=border, dark=dark, light=light)
    print("encoded URL:", url)
    print("saved", svg_path)
    print("saved", png_path)
    print("tip: print from the SVG (vector, crisp at any size); test-scan before printing.")


if __name__ == "__main__":
    main()
