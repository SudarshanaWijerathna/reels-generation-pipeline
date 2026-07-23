"""
subtitle_boil.py
================
Hand-Drawn Line Boil Animation System for Video Subtitle Overlays & SVG Assets.

This module replaces static PIL subtitles with organic, frame-by-frame animated
subtitle clips that mimic traditional pencil-test / flipbook hand-drawn animation.

ANIMATION TECHNIQUE
-------------------
Each character glyph is extracted as an SVG <path> from the TTF font using fonttools.
Paths are assembled into a full sentence SVG with proper advance-width kerning.
For each animation frame, tiny Gaussian noise is added to every bezier control point
(C, Q, S commands) — simulating the natural "redrawing" imperfection of hand animation.
Frames are rendered to PNGs via cairosvg and assembled into a MoviePy ImageSequenceClip.
The same pipeline works for arbitrary decorative SVG assets (flowers, doodle lines, etc.).

DEPENDENCIES
------------
    pip install fonttools svglib reportlab numpy Pillow moviepy
    (fonttools, svglib, Pillow are already installed in this project)

QUICK USAGE
-----------
    from subtitle_boil import create_animated_subtitle_clip, boil_animate_svg_asset

    # Animated subtitle clip (MoviePy)
    clip = create_animated_subtitle_clip(
        text="If you see your friend with your enemy",
        duration=4.5,
        font_path="fonts/IndieFlower-Regular.ttf",
        canvas_w=720,
        canvas_h=1280,
    )

    # Animated decorative SVG asset
    flower_clip = boil_animate_svg_asset(
        svg_path="assets/flower.svg",
        duration=4.5,
    )
"""

import os
import re
import math
import random
import shutil
import hashlib
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# ██  CONFIGURABLE ANIMATION PARAMETERS  ██
# Adjust these to dial in the exact boil feel you want.
# ─────────────────────────────────────────────────────────────────────────────

# ── Boil Timing ──────────────────────────────────────────────────────────────

BOIL_FPS = 12
"""
Frames per second for the boil animation cycle.
  - 8   → rough flipbook feel
  - 12  → classic hand-drawn animation (RECOMMENDED)
  - 24  → smooth, barely-visible breathing
"""

BOIL_N_FRAMES = 12
"""
Number of unique frames in one boil cycle (loops seamlessly).
  - 6   → snappier, more jittery
  - 12  → balanced organic motion (RECOMMENDED)
  - 18  → very slow, gentle morph
"""

# ── Path Perturbation (the "boil" wobble) ────────────────────────────────────

BOIL_INTENSITY = 0.4
"""
Base intensity of the path-point micro-perturbation in SCREEN PIXELS.
Controls the maximum displacement applied to bezier control points.
  - 0.4 → very low, gentle micro-distortion (RECOMMENDED for clean readable boil)
  - 1.0 → medium wobble
  - 2.0 → strong distortion
"""

BOIL_SMOOTH_BLEND = 0.35
"""
How much each frame blends toward the PREVIOUS frame's perturbation.
Prevents sudden jumps between frames, creating the smooth easing effect.
  - 0.0 → no blending (pure random per-frame, jittery)
  - 0.35 → gentle smooth drift (RECOMMENDED)
"""

BOIL_POSITIONAL_DRIFT = 1.0
"""
Maximum subtle whole-glyph positional drift in SCREEN PIXELS.
Simulates the hand-placement variation of redrawing each letter.
  - 0.0 → no drift
  - 1.0 → clear character micro-drift (RECOMMENDED)
  - 2.0 → exaggerated floating
"""

BOIL_STROKE_THICKNESS_VARIATION = 0.08
"""
How much the stroke width varies per frame (as a fraction of base stroke width).
  - 0.0  → constant stroke (no variation)
  - 0.08 → ±8% stroke width variation (RECOMMENDED for organic ink feel)
  - 0.20 → high variation, very hand-inked look
"""

# ── Text & Visual Style ───────────────────────────────────────────────────────

FONT_SIZE_PX = 72
"""
Rendered font size in pixels at the output canvas resolution.
  - 72 → clear, readable size (RECOMMENDED for 1080x1920 HD canvas)
"""

TEXT_COLOR = (255, 255, 255)
"""RGB fill color of the subtitle text (white)."""

STROKE_COLOR = (0, 0, 0)
"""RGB color of the text outline/stroke."""

STROKE_WIDTH_PX = 0.0
"""Base stroke (outline) width in pixels (0.0 = no stroke/outline)."""

TEXT_Y_POSITION_RATIO = 0.72
"""Vertical position of text center (0.72 = lower-center)."""

LINE_SPACING_RATIO = 1.35
"""Line height multiplier."""

MAX_CHARS_PER_LINE = 28
"""Approximate maximum characters per line before word-wrapping."""

# ── Background Pill / Bar ─────────────────────────────────────────────────────

SUBTITLE_BACKGROUND_ENABLED = False
"""Whether to draw a semi-transparent rounded rectangle behind the subtitle text."""


SUBTITLE_BACKGROUND_COLOR = "rgba(0,0,0,0.55)"
"""
SVG fill color of the subtitle background pill.
  'rgba(0,0,0,0.55)'      → semi-transparent black (RECOMMENDED)
  'rgba(20,10,40,0.65)'   → dark indigo tint
  'rgba(255,255,255,0.15)' → frosted glass effect (light)
"""

SUBTITLE_BACKGROUND_PADDING_X = 36
"""Horizontal padding (px) inside the subtitle background pill."""

SUBTITLE_BACKGROUND_PADDING_Y = 18
"""Vertical padding (px) inside the subtitle background pill."""

SUBTITLE_BACKGROUND_CORNER_RADIUS = 16
"""Corner radius (px) of the subtitle background pill."""

# ── Rendering ─────────────────────────────────────────────────────────────────

RENDER_SCALE = 1.0
"""
Output resolution multiplier. 1.0 = canvas_w × canvas_h native.
  - 1.0 → native canvas resolution (RECOMMENDED for video pipeline)
  - 2.0 → 2× supersampling for sharper edges (slower render)
"""

GLYPH_CACHE_ENABLED = True
"""
Cache extracted glyph SVG paths to disk to avoid re-extracting on every run.
Disable if you change fonts or suspect cache corruption.
"""

# ─────────────────────────────────────────────────────────────────────────────
# END OF CONFIGURABLE PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────

# High-performance Rust SVG renderer (resvg_py)
import resvg_py
from io import BytesIO
from PIL import Image as PilImage

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(WORKSPACE_DIR, "fonts")
DEFAULT_FONT_PATH = os.path.join(FONTS_DIR, "IndieFlower-Regular.ttf")
GLYPH_CACHE_DIR = os.path.join(WORKSPACE_DIR, "temp_build", "_glyph_cache")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Glyph Extraction
# ─────────────────────────────────────────────────────────────────────────────

def _get_font_metrics(font: TTFont):
    """Returns (units_per_em, ascender, descender) from font tables."""
    upm = font["head"].unitsPerEm
    ascender = font["hhea"].ascent
    descender = font["hhea"].descent  # negative value
    return upm, ascender, descender


def extract_glyph_path(font: TTFont, char: str) -> Optional[dict]:
    """
    Extracts the SVG path data for a single character from the font.

    Returns a dict with:
        path_d      : SVG path `d` attribute string (Y-flipped for SVG)
        advance_w   : Advance width in font units
        lsb         : Left side bearing in font units
        upm         : Units per em
        ascender    : Font ascender in font units
        descender   : Font descender in font units (negative)
    Returns None if the character has no glyph (e.g. space).
    """
    cmap = font.getBestCmap()
    glyph_name = cmap.get(ord(char))
    if not glyph_name:
        return None

    glyph_set = font.getGlyphSet()
    if glyph_name not in glyph_set:
        return None

    upm, ascender, descender = _get_font_metrics(font)

    # Y-flip: font coords origin=bottom-left → SVG origin=top-left
    # Transform: scale(1, -1) translate(0, -ascender)
    svg_pen = SVGPathPen(glyph_set)
    t_pen = TransformPen(svg_pen, (1, 0, 0, -1, 0, ascender))
    glyph_set[glyph_name].draw(t_pen)

    path_d = svg_pen.getCommands()

    hmtx = font["hmtx"].metrics
    advance_w, lsb = hmtx.get(glyph_name, (upm // 2, 0))

    return {
        "path_d": path_d,
        "advance_w": advance_w,
        "lsb": lsb,
        "upm": upm,
        "ascender": ascender,
        "descender": descender,
    }


def extract_all_glyphs(font_path: str, text: str, cache_dir: Optional[str] = None) -> dict:
    """
    Extracts SVG path data for every unique character in `text`.

    Returns a dict mapping char → glyph_info (from extract_glyph_path).
    Space characters return a dict with path_d=None and only advance_w.
    """
    if cache_dir is None and GLYPH_CACHE_ENABLED:
        cache_dir = GLYPH_CACHE_DIR

    font = TTFont(font_path)
    upm, ascender, descender = _get_font_metrics(font)
    hmtx = font["hmtx"].metrics
    cmap = font.getBestCmap()

    # Space advance width
    space_glyph = cmap.get(ord(" "))
    space_adv = upm // 3
    if space_glyph and space_glyph in hmtx:
        space_adv = hmtx[space_glyph][0]

    glyphs = {}
    unique_chars = set(text)

    for char in unique_chars:
        if char == " ":
            glyphs[" "] = {
                "path_d": None,
                "advance_w": space_adv,
                "lsb": 0,
                "upm": upm,
                "ascender": ascender,
                "descender": descender,
            }
            continue

        # Try disk cache first
        if cache_dir and GLYPH_CACHE_ENABLED:
            os.makedirs(cache_dir, exist_ok=True)
            font_hash = hashlib.md5(open(font_path, "rb").read()).hexdigest()[:8]
            cache_file = os.path.join(cache_dir, f"{font_hash}_{ord(char):05d}.txt")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    import json
                    glyphs[char] = json.loads(f.read())
                continue

        info = extract_glyph_path(font, char)
        if info is None:
            # Fallback: treat as space
            info = {
                "path_d": None,
                "advance_w": space_adv,
                "lsb": 0,
                "upm": upm,
                "ascender": ascender,
                "descender": descender,
            }

        glyphs[char] = info

        if cache_dir and GLYPH_CACHE_ENABLED:
            import json
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(info))

    return glyphs


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Sentence SVG Assembly
# ─────────────────────────────────────────────────────────────────────────────

def _word_wrap(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> list[str]:
    """Word-wraps text into lines of at most max_chars characters."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _compute_scale(upm: int, font_size_px: float) -> float:
    """Returns the scale factor to convert font units → pixels at font_size_px."""
    return font_size_px / upm


def _measure_line_width(line: str, glyphs: dict, scale: float) -> float:
    """Returns the pixel width of a single line of text."""
    return sum(glyphs.get(c, glyphs.get(" ", {})).get("advance_w", 0) * scale for c in line)


def assemble_sentence_svg(
    text: str,
    glyphs: dict,
    canvas_w: int,
    canvas_h: int,
    font_size_px: float = FONT_SIZE_PX,
    text_color: tuple = TEXT_COLOR,
    stroke_color: tuple = STROKE_COLOR,
    stroke_width: float = STROKE_WIDTH_PX,
    text_y_ratio: float = TEXT_Y_POSITION_RATIO,
    line_spacing_ratio: float = LINE_SPACING_RATIO,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    bg_enabled: bool = SUBTITLE_BACKGROUND_ENABLED,
    bg_color: str = SUBTITLE_BACKGROUND_COLOR,
    bg_pad_x: int = SUBTITLE_BACKGROUND_PADDING_X,
    bg_pad_y: int = SUBTITLE_BACKGROUND_PADDING_Y,
    bg_radius: int = SUBTITLE_BACKGROUND_CORNER_RADIUS,
    positional_drift_px: float = 0.0,  # applied during boil, 0 for base SVG
) -> str:
    """
    Assembles a complete sentence SVG string from individual glyph path data.

    Each character is placed as a <path> element with its proper advance-width offset.
    Lines are centered horizontally on the canvas.
    Returns the full SVG XML string.
    """
    if not glyphs:
        return ""

    # Use the first glyph's font metrics (all same font)
    sample = next(iter(glyphs.values()))
    upm = sample["upm"]
    ascender = sample["ascender"]
    descender = sample["descender"]

    scale = _compute_scale(upm, font_size_px)
    line_height = font_size_px * line_spacing_ratio
    glyph_height = (ascender - descender) * scale  # full em height in px

    lines = _word_wrap(text, max_chars_per_line)
    n_lines = len(lines)

    total_text_h = n_lines * line_height
    text_block_center_y = canvas_h * text_y_ratio
    block_top_y = text_block_center_y - total_text_h / 2

    # Measure the widest line for background pill sizing
    max_line_w = max(_measure_line_width(line, glyphs, scale) for line in lines) if lines else 0

    fill_hex = "#{:02x}{:02x}{:02x}".format(*text_color)
    stroke_hex = "#{:02x}{:02x}{:02x}".format(*stroke_color)

    # Build SVG elements
    path_elements = []

    # Background pill rect
    if bg_enabled:
        pill_w = max_line_w + bg_pad_x * 2
        pill_h = total_text_h + bg_pad_y * 2
        pill_x = (canvas_w - pill_w) / 2
        pill_y = block_top_y - bg_pad_y
        path_elements.append(
            f'<rect x="{pill_x:.2f}" y="{pill_y:.2f}" '
            f'width="{pill_w:.2f}" height="{pill_h:.2f}" '
            f'rx="{bg_radius}" ry="{bg_radius}" '
            f'fill="{bg_color}" />'
        )

    # Character paths per line
    for line_idx, line in enumerate(lines):
        line_w = _measure_line_width(line, glyphs, scale)
        line_start_x = (canvas_w - line_w) / 2
        # baseline_y: block_top_y + line offset. (Glyph origin is top of em box in our Y-flipped pen)
        baseline_y = block_top_y + line_idx * line_height + (line_height - font_size_px) / 2

        cursor_x = line_start_x

        for char in line:
            glyph = glyphs.get(char)
            if glyph is None:
                glyph = glyphs.get(" ")
            if glyph is None:
                continue

            adv = glyph["advance_w"] * scale

            if glyph["path_d"]:
                # Translate glyph to its canvas position
                path_elements.append(
                    f'<path '
                    f'd="{glyph["path_d"]}" '
                    f'transform="translate({cursor_x:.3f},{baseline_y:.3f}) scale({scale:.6f})" '
                    f'fill="{fill_hex}" '
                    f'stroke="{stroke_hex}" '
                    f'stroke-width="{stroke_width / scale:.4f}" '
                    f'stroke-linejoin="round" stroke-linecap="round" '
                    f'paint-order="stroke fill" />'
                )

            cursor_x += adv

    svg_content = "\n  ".join(path_elements)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}">\n'
        f'  {svg_content}\n'
        f'</svg>'
    )
    return svg


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Path Point Perturbation (The Boil Engine)
# ─────────────────────────────────────────────────────────────────────────────

# Regex to capture SVG path command tokens
_PATH_TOKEN_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])|(-?\d*\.?\d+(?:[eE][+-]?\d+)?)"
)


def _parse_path_tokens(d: str) -> list:
    """Tokenizes an SVG path `d` string into (type, value) pairs."""
    tokens = []
    for match in _PATH_TOKEN_RE.finditer(d):
        cmd, num = match.group(1), match.group(2)
        if cmd:
            tokens.append(("cmd", cmd))
        elif num:
            tokens.append(("num", float(num)))
    return tokens


def _tokens_to_string(tokens: list) -> str:
    """Reconstructs a path `d` string from tokens."""
    parts = []
    for kind, val in tokens:
        if kind == "cmd":
            parts.append(val)
        else:
            parts.append(f"{val:.4f}")
    return " ".join(parts)


def _perturb_tokens(
    tokens: list,
    intensity: float,
    prev_offsets: Optional[list],
    blend: float,
    rng: np.random.Generator,
) -> tuple[list, list]:
    """
    Applies Gaussian perturbation to numeric tokens in a path.

    Blends with prev_offsets for smooth inter-frame continuity.
    Returns (perturbed_tokens, new_offsets).
    """
    new_tokens = []
    new_offsets = []
    num_indices = [i for i, (k, _) in enumerate(tokens) if k == "num"]

    # Generate fresh offsets
    fresh = rng.normal(0, intensity, len(num_indices))

    for j, i in enumerate(num_indices):
        if prev_offsets is not None and j < len(prev_offsets):
            offset = blend * prev_offsets[j] + (1 - blend) * fresh[j]
        else:
            offset = fresh[j]
        new_offsets.append(offset)

    # Apply offsets only to coordinate tokens (not command letters)
    offset_idx = 0
    for i, (kind, val) in enumerate(tokens):
        if kind == "num":
            new_tokens.append(("num", val + new_offsets[offset_idx]))
            offset_idx += 1
        else:
            new_tokens.append((kind, val))

    return new_tokens, new_offsets


def perturb_svg_paths(
    svg_string: str,
    intensity: float = BOIL_INTENSITY,
    prev_offsets_map: Optional[dict] = None,
    blend: float = BOIL_SMOOTH_BLEND,
    stroke_variation: float = BOIL_STROKE_THICKNESS_VARIATION,
    positional_drift_px: float = BOIL_POSITIONAL_DRIFT,
    rng: Optional[np.random.Generator] = None,
) -> tuple[str, dict]:
    """
    Applies per-frame micro-perturbation to all <path> elements in an SVG string.

    Parameters
    ----------
    svg_string : str
        Source SVG XML string (output of assemble_sentence_svg or any SVG file).
    intensity : float
        Max displacement amplitude in SVG user units. See BOIL_INTENSITY.
    prev_offsets_map : dict or None
        Offset vectors from the previous frame (keyed by path index).
        Pass None for the first frame.
    blend : float
        Blending factor toward previous frame offsets. See BOIL_SMOOTH_BLEND.
    stroke_variation : float
        Fractional variation in stroke-width per frame. See BOIL_STROKE_THICKNESS_VARIATION.
    rng : numpy.random.Generator or None
        Random number generator for reproducibility. Created if None.

    Returns
    -------
    (perturbed_svg_string, new_offsets_map)
    """
    if rng is None:
        rng = np.random.default_rng()

    try:
        root = ET.fromstring(svg_string)
    except ET.ParseError:
        return svg_string, {}

    ns = {"svg": SVG_NS}
    paths = root.findall(".//{%s}path" % SVG_NS)
    new_offsets_map = {}

    for path_idx, path_elem in enumerate(paths):
        d = path_elem.get("d", "")
        if not d:
            continue

        tokens = _parse_path_tokens(d)
        prev_off = prev_offsets_map.get(path_idx) if prev_offsets_map else None
        new_tokens, new_off = _perturb_tokens(tokens, intensity, prev_off, blend, rng)
        new_offsets_map[path_idx] = new_off
        path_elem.set("d", _tokens_to_string(new_tokens))

        # Positional translate drift per character per frame
        if positional_drift_px > 0:
            transform_str = path_elem.get("transform", "")
            t_match = re.search(r"translate\(([\d.eE+\-]+),([\d.eE+\-]+)\)", transform_str)
            s_match = re.search(r"scale\(([\d.eE+\-]+)\)", transform_str)
            if t_match:
                orig_tx, orig_ty = float(t_match.group(1)), float(t_match.group(2))
                scale_part = s_match.group(0) if s_match else ""
                dx = rng.uniform(-positional_drift_px, positional_drift_px)
                dy = rng.uniform(-positional_drift_px, positional_drift_px)
                new_tx = orig_tx + dx
                new_ty = orig_ty + dy
                new_t_str = f"translate({new_tx:.3f},{new_ty:.3f}) {scale_part}".strip()
                path_elem.set("transform", new_t_str)

        # Stroke width variation
        sw_attr = path_elem.get("stroke-width")
        if sw_attr and stroke_variation > 0:
            try:
                base_sw = float(sw_attr)
                variation = rng.uniform(-stroke_variation, stroke_variation)
                new_sw = max(0.1, base_sw * (1.0 + variation))
                path_elem.set("stroke-width", f"{new_sw:.4f}")
            except ValueError:
                pass

    perturbed = ET.tostring(root, encoding="unicode")
    return perturbed, new_offsets_map


def _render_svg_to_png(svg_string: str, output_path: str, out_w: int = 1080, out_h: int = 1920):
    """
    Renders a subtitle SVG string to a high-resolution PNG file using resvg_py.

    resvg is a high-performance Rust-based SVG renderer that produces crystal-clear,
    perfectly anti-aliased vector rendering at 1080x1920 resolution with full
    support for even-odd path filling rules (preserving font counter-holes).
    """
    png_bytes = resvg_py.svg_to_bytes(
        svg_string=svg_string,
        width=out_w,
        height=out_h,
        shape_rendering="geometric_precision",
        text_rendering="optimize_legibility",
    )
    with open(output_path, "wb") as f:
        f.write(png_bytes)


def generate_boil_frames(
    base_svg_string: str,
    output_dir: str,
    n_frames: int = BOIL_N_FRAMES,
    intensity: float = BOIL_INTENSITY,
    blend: float = BOIL_SMOOTH_BLEND,
    stroke_variation: float = BOIL_STROKE_THICKNESS_VARIATION,
    positional_drift_px: float = BOIL_POSITIONAL_DRIFT,
    canvas_w: int = 720,
    canvas_h: int = 1280,
    render_scale: float = RENDER_SCALE,
    seed: Optional[int] = None,
) -> list[str]:
    """
    Generates a sequence of PNG frames with boil animation applied.

    Each frame applies a slightly different perturbation to the SVG paths,
    blended smoothly with the previous frame for organic, continuous motion.

    Parameters
    ----------
    base_svg_string : str
        The base SVG to animate (from assemble_sentence_svg or any SVG source).
    output_dir : str
        Directory where frame PNGs will be saved.
    n_frames : int
        Number of unique frames to generate. See BOIL_N_FRAMES.
    intensity : float
        Path perturbation amplitude. See BOIL_INTENSITY.
    blend : float
        Inter-frame smoothing. See BOIL_SMOOTH_BLEND.
    stroke_variation : float
        Stroke width variation per frame. See BOIL_STROKE_THICKNESS_VARIATION.
    positional_drift_px : float
        Max whole-glyph positional drift in pixels. See BOIL_POSITIONAL_DRIFT.
    canvas_w, canvas_h : int
        Output image dimensions in pixels.
    render_scale : float
        Resolution multiplier. See RENDER_SCALE.
    seed : int or None
        RNG seed for reproducible animations.

    Returns
    -------
    list[str] : Absolute paths to the generated PNG frame files (sorted).
    """
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    out_w = int(canvas_w * render_scale)
    out_h = int(canvas_h * render_scale)

    frame_paths = []
    prev_offsets_map = None
    current_svg = base_svg_string

    for frame_idx in range(n_frames):
        # Perturb paths
        perturbed_svg, new_offsets_map = perturb_svg_paths(
            current_svg,
            intensity=intensity,
            prev_offsets_map=prev_offsets_map,
            blend=blend,
            stroke_variation=stroke_variation,
            positional_drift_px=positional_drift_px,
            rng=rng,
        )
        prev_offsets_map = new_offsets_map

        # Render SVG → PNG via svglib + reportlab (pure Python, no Cairo DLLs)
        frame_path = os.path.join(output_dir, f"boil_frame_{frame_idx:04d}.png")
        try:
            _render_svg_to_png(perturbed_svg, frame_path, out_w, out_h)
            frame_paths.append(frame_path)
        except Exception as e:
            print(f"  [subtitle_boil] Frame {frame_idx} render error: {e}")

    print(f"  [subtitle_boil] Generated {len(frame_paths)} boil frames -> {output_dir}")
    return sorted(frame_paths)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — High-Level MoviePy Integration
# ─────────────────────────────────────────────────────────────────────────────

def create_animated_subtitle_clip(
    text: str,
    duration: float,
    font_path: str = DEFAULT_FONT_PATH,
    canvas_w: int = 720,
    canvas_h: int = 1280,
    output_temp_dir: Optional[str] = None,
    # Animation params (all default to module-level constants)
    boil_fps: int = BOIL_FPS,
    boil_n_frames: int = BOIL_N_FRAMES,
    boil_intensity: float = BOIL_INTENSITY,
    boil_blend: float = BOIL_SMOOTH_BLEND,
    boil_stroke_variation: float = BOIL_STROKE_THICKNESS_VARIATION,
    boil_positional_drift: float = BOIL_POSITIONAL_DRIFT,
    # Text style params
    font_size_px: float = FONT_SIZE_PX,
    text_color: tuple = TEXT_COLOR,
    stroke_color: tuple = STROKE_COLOR,
    stroke_width: float = STROKE_WIDTH_PX,
    text_y_ratio: float = TEXT_Y_POSITION_RATIO,
    line_spacing_ratio: float = LINE_SPACING_RATIO,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    bg_enabled: bool = SUBTITLE_BACKGROUND_ENABLED,
    bg_color: str = SUBTITLE_BACKGROUND_COLOR,
    bg_pad_x: int = SUBTITLE_BACKGROUND_PADDING_X,
    bg_pad_y: int = SUBTITLE_BACKGROUND_PADDING_Y,
    bg_radius: int = SUBTITLE_BACKGROUND_CORNER_RADIUS,
    render_scale: float = RENDER_SCALE,
    seed: Optional[int] = None,
):
    """
    Creates a MoviePy ImageSequenceClip of animated hand-drawn boil subtitles.

    This is the main entry point for the video pipeline. It:
    1. Extracts glyph paths from the font TTF
    2. Assembles the sentence into an SVG layout
    3. Generates `boil_n_frames` perturbed PNG frames
    4. Returns an ImageSequenceClip looped to match `duration`

    Parameters
    ----------
    text : str
        The subtitle text to render.
    duration : float
        Clip duration in seconds (matches the audio segment duration).
    font_path : str
        Path to the TTF font file.
    canvas_w, canvas_h : int
        Output video dimensions (pixels).
    output_temp_dir : str or None
        Directory for temporary frame PNGs. Auto-created if None.
    ... (all other params mirror module-level constants for per-call override)

    Returns
    -------
    moviepy.ImageSequenceClip — ready to composite over a background ImageClip.
    """
    from moviepy import ImageSequenceClip

    print(f"  [subtitle_boil] Rendering boil subtitle: '{text[:40]}...' " if len(text) > 40 else f"  [subtitle_boil] Rendering boil subtitle: '{text}'")

    # Temp directory for this subtitle's frames
    if output_temp_dir is None:
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output_temp_dir = os.path.join(
            WORKSPACE_DIR, "temp_build", f"boil_subtitle_{text_hash}"
        )

    # Step 1: Extract glyph paths
    glyphs = extract_all_glyphs(font_path, text)

    # Step 2: Assemble base sentence SVG
    base_svg = assemble_sentence_svg(
        text=text,
        glyphs=glyphs,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        font_size_px=font_size_px,
        text_color=text_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        text_y_ratio=text_y_ratio,
        line_spacing_ratio=line_spacing_ratio,
        max_chars_per_line=max_chars_per_line,
        bg_enabled=bg_enabled,
        bg_color=bg_color,
        bg_pad_x=bg_pad_x,
        bg_pad_y=bg_pad_y,
        bg_radius=bg_radius,
        positional_drift_px=0.0,  # drift applied per-frame below
    )

    # Step 3: Generate boil frames
    # Convert pixel boil intensity → font units based on font size and UPM
    upm = next(iter(glyphs.values()))["upm"] if glyphs else 1024
    scale = font_size_px / upm
    font_unit_intensity = (boil_intensity / scale) if scale > 0 else boil_intensity

    unit_scale = canvas_w / 720.0  # normalise to 720px baseline
    frame_paths = generate_boil_frames(
        base_svg_string=base_svg,
        output_dir=output_temp_dir,
        n_frames=boil_n_frames,
        intensity=font_unit_intensity * unit_scale,
        blend=boil_blend,
        stroke_variation=boil_stroke_variation,
        positional_drift_px=boil_positional_drift * unit_scale,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        render_scale=render_scale,
        seed=seed,
    )

    if not frame_paths:
        print("  [subtitle_boil] WARNING: No frames generated. Falling back to static subtitle.")
        return _fallback_static_clip(text, duration, canvas_w, canvas_h)

    # Step 4: Build MoviePy clip by repeating frame sequence to cover full duration
    import math
    total_frames_needed = max(1, int(math.ceil(duration * boil_fps)))
    repeated_paths = [frame_paths[i % len(frame_paths)] for i in range(total_frames_needed)]

    clip = ImageSequenceClip(repeated_paths, fps=boil_fps).with_duration(duration)
    return clip


def boil_animate_svg_asset(
    svg_path: str,
    duration: float,
    canvas_w: int = 720,
    canvas_h: int = 1280,
    output_temp_dir: Optional[str] = None,
    # Animation params
    boil_fps: int = BOIL_FPS,
    boil_n_frames: int = BOIL_N_FRAMES,
    boil_intensity: float = BOIL_INTENSITY,
    boil_blend: float = BOIL_SMOOTH_BLEND,
    boil_stroke_variation: float = BOIL_STROKE_THICKNESS_VARIATION,
    render_scale: float = RENDER_SCALE,
    seed: Optional[int] = None,
):
    """
    Applies the same line boil animation to any external SVG file (flowers, doodles, etc.).

    Parameters
    ----------
    svg_path : str
        Path to an existing SVG file (flowers, leaf borders, doodle lines, etc.).
    duration : float
        How long the animated clip should last (seconds).
    ... (all animation params mirror the subtitle function)

    Returns
    -------
    moviepy.ImageSequenceClip — ready to composite into the video.
    """
    from moviepy import ImageSequenceClip

    print(f"  [subtitle_boil] Animating SVG asset: {os.path.basename(svg_path)}")

    with open(svg_path, "r", encoding="utf-8") as f:
        base_svg = f.read()

    if output_temp_dir is None:
        svg_hash = hashlib.md5(base_svg.encode()).hexdigest()[:8]
        output_temp_dir = os.path.join(
            WORKSPACE_DIR, "temp_build", f"boil_asset_{svg_hash}"
        )

    unit_scale = canvas_w / 720.0
    frame_paths = generate_boil_frames(
        base_svg_string=base_svg,
        output_dir=output_temp_dir,
        n_frames=boil_n_frames,
        intensity=boil_intensity * unit_scale,
        blend=boil_blend,
        stroke_variation=boil_stroke_variation,
        positional_drift_px=0.0,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        render_scale=render_scale,
        seed=seed,
    )

    if not frame_paths:
        print(f"  [subtitle_boil] WARNING: No frames for asset {svg_path}")
        return None

    import math
    total_frames_needed = max(1, int(math.ceil(duration * boil_fps)))
    repeated_paths = [frame_paths[i % len(frame_paths)] for i in range(total_frames_needed)]

    clip = ImageSequenceClip(repeated_paths, fps=boil_fps).with_duration(duration)
    return clip


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Fallback & Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_static_clip(text: str, duration: float, canvas_w: int, canvas_h: int):
    """
    Emergency fallback: generates a static PIL subtitle image clip.
    Used if cairosvg/fonttools fail for any reason.
    """
    from moviepy import ImageClip
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(DEFAULT_FONT_PATH), FONT_SIZE_PX)
    except Exception:
        font = ImageFont.load_default()

    words = text.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        if draw.textlength(test, font=font) < canvas_w - 100:
            line.append(w)
        else:
            if line:
                lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))

    full_text = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), full_text, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (canvas_w - tw) // 2
    y = int(canvas_h * TEXT_Y_POSITION_RATIO) - th // 2

    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if dx or dy:
                draw.multiline_text((x + dx, y + dy), full_text, font=font,
                                    fill=(0, 0, 0, 220), align="center")
    draw.multiline_text((x, y), full_text, font=font,
                        fill=(255, 255, 255, 255), align="center")

    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name, "PNG")
    return ImageClip(tmp.name).with_duration(duration)


def cleanup_boil_frames(temp_dir: str):
    """Removes a boil frame temp directory after the video has been rendered."""
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Quick Test / Preview
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Quick standalone test: generates 12 boil frames for a sample sentence
    and saves them to temp_build/boil_test/

    Run with:
        python subtitle_boil.py
    """
    import sys
    print("=" * 60)
    print("subtitle_boil.py — Quick Test")
    print("=" * 60)

    test_text = sys.argv[1] if len(sys.argv) > 1 else "If you see your friend with your enemy"
    test_font = DEFAULT_FONT_PATH
    test_out = os.path.join(WORKSPACE_DIR, "temp_build", "boil_test")

    print(f"\nFont     : {test_font}")
    print(f"Text     : {test_text}")
    print(f"Output   : {test_out}")
    print(f"Frames   : {BOIL_N_FRAMES} @ {BOIL_FPS}fps")
    print(f"Intensity: {BOIL_INTENSITY}  Blend: {BOIL_SMOOTH_BLEND}")
    print()

    if not os.path.exists(test_font):
        print(f"ERROR: Font not found at {test_font}")
        sys.exit(1)

    glyphs = extract_all_glyphs(test_font, test_text)
    print(f"Extracted glyphs for {len(glyphs)} unique characters.")

    base_svg = assemble_sentence_svg(test_text, glyphs, 720, 1280)

    # Save base SVG for inspection
    base_svg_path = os.path.join(WORKSPACE_DIR, "temp_build", "boil_base.svg")
    os.makedirs(os.path.dirname(base_svg_path), exist_ok=True)
    with open(base_svg_path, "w", encoding="utf-8") as f:
        f.write(base_svg)
    print(f"Base SVG saved -> {base_svg_path}")

    frames = generate_boil_frames(base_svg, test_out, n_frames=BOIL_N_FRAMES, seed=42)
    print(f"\nSUCCESS -- {len(frames)} frames generated in: {test_out}")
    print("Open the frames to inspect the boil animation effect.")
    print()
    for fp in frames:
        print(f"  {fp}")
