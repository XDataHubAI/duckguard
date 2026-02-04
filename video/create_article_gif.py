#!/usr/bin/env python3
"""
Create animated GIF for the weekly article showcasing the Python API.

Focus: pytest-like simplicity, 3 lines of code, assertions.

Usage:
    python create_article_gif.py
"""

import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)


# === DESIGN CONSTANTS (matching create_polished_gif.py) ===

WIDTH = 800
HEIGHT = 520
PADDING_X = 20
PADDING_Y = 14
LINE_HEIGHT = 24
FONT_SIZE = 16
HEADER_HEIGHT = 38

# Colors - Pure black background like the original
COLORS = {
    'bg': (0, 0, 0),              # Pure black background
    'header_bg': (40, 40, 40),    # Dark gray header bar
    'fg': (255, 255, 255),        # Pure white text
    'dim': (150, 150, 150),       # Gray for secondary text
    'cyan': (0, 255, 136),        # Bright green for $ prompt
    'green': (0, 255, 136),       # Bright green for success
    'red': (255, 85, 85),         # Bright red for errors
    'yellow': (255, 170, 0),      # Bright orange for WARNING
    'magenta': (255, 85, 255),    # Bright magenta
    'blue': (0, 175, 215),        # Teal/cyan blue for DuckGuard
    'white': (255, 255, 255),     # Pure white
    'cursor': (255, 255, 255),    # White cursor
    'orange': (255, 170, 0),      # Same as yellow
    'purple': (255, 85, 255),     # Same as magenta for keywords
}

# Timing
PAUSE_SHORT = 30       # ~1.5 sec
PAUSE_MEDIUM = 50      # ~2.5 sec
PAUSE_LONG = 80        # ~4 sec
PAUSE_XLLONG = 120     # ~6 sec


def get_font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Get a monospace font."""
    import os

    windows_fonts = [
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\cascadiamono.ttf",
        r"C:\Windows\Fonts\cour.ttf",
    ]

    for font_path in windows_fonts:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except (IOError, OSError):
                continue

    # Fallback for other OS
    for font_name in ['Consolas', 'Monaco', 'Courier New', 'DejaVu Sans Mono']:
        try:
            return ImageFont.truetype(font_name, size)
        except (IOError, OSError):
            continue

    return ImageFont.load_default()


class TerminalRenderer:
    def __init__(self):
        self.font = get_font(FONT_SIZE)
        self.char_width = self._measure_char_width()

    def _measure_char_width(self) -> int:
        img = Image.new('RGB', (100, 100))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), "M", font=self.font)
        return bbox[2] - bbox[0]

    def create_base_frame(self, title: str = "Python") -> Image.Image:
        img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['bg'])
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=COLORS['header_bg'])

        # Traffic light buttons
        button_y = HEADER_HEIGHT // 2
        draw.ellipse([12, button_y - 6, 24, button_y + 6], fill=COLORS['red'])
        draw.ellipse([32, button_y - 6, 44, button_y + 6], fill=(255, 200, 50))
        draw.ellipse([52, button_y - 6, 64, button_y + 6], fill=COLORS['green'])

        # Title
        title_bbox = draw.textbbox((0, 0), title, font=self.font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (WIDTH - title_width) // 2
        title_y = (HEADER_HEIGHT - (title_bbox[3] - title_bbox[1])) // 2
        draw.text((title_x, title_y), title, fill=COLORS['dim'], font=self.font)

        return img

    def draw_text_segment(self, draw: ImageDraw.Draw, x: int, y: int,
                          text: str, color: str = 'fg') -> int:
        fill = COLORS.get(color, COLORS['fg'])
        draw.text((x, y), text, fill=fill, font=self.font)
        return x + (len(text) * self.char_width)

    def draw_cursor(self, draw: ImageDraw.Draw, x: int, y: int, visible: bool = True):
        if visible:
            cursor_height = LINE_HEIGHT - 4
            draw.rectangle([x, y + 2, x + self.char_width - 2, y + cursor_height],
                          fill=COLORS['cursor'])


class Scene:
    def __init__(self, lines: List[dict], pause_after: int = PAUSE_MEDIUM,
                 clear_before: bool = False, title: str = "Python"):
        self.lines = lines
        self.pause_after = pause_after
        self.clear_before = clear_before
        self.title = title


# === ARTICLE DEMO SCRIPT - Python API Focus ===

DEMO_SCENES = [
    # Scene 1: Title slide
    Scene([
        {'text': ''},
        {'text': ''},
        {'segments': [
            {'text': '      ', 'color': 'bg'},
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' - Data Quality in 3 Lines', 'color': 'white'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '      ', 'color': 'bg'},
            {'text': 'pytest-like assertions  |  DuckDB-powered', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, title="DuckGuard Demo"),

    # Scene 2: The Problem - Great Expectations boilerplate
    Scene([
        {'segments': [
            {'text': '# Great Expectations: ~50 lines for one check', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'from ', 'color': 'purple'},
            {'text': 'great_expectations.data_context ', 'color': 'fg'},
            {'text': 'import ', 'color': 'purple'},
            {'text': 'DataContext', 'color': 'blue'},
        ], 'instant': True},
        {'segments': [
            {'text': 'context = DataContext()', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': 'datasource = context.sources.add_pandas(...)', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': 'data_asset = datasource.add_csv_asset(...)', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': 'batch_request = data_asset.build_batch_request()', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': 'validator = context.get_validator(...)', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': 'validator.expect_column_values_to_not_be_null(...)', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '# ... 40 more lines of ceremony', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, clear_before=True, title="The Problem"),

    # Scene 3: DuckGuard - 3 lines (all typing in one scene)
    Scene([
        {'segments': [
            {'text': '# DuckGuard: Just 3 lines', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'from duckguard import connect'},
        {'pause': PAUSE_SHORT},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'orders = connect("orders.csv")'},
        {'pause': PAUSE_SHORT},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'assert orders.customer_id.null_percent == 0'},
        {'text': ''},
        {'segments': [
            {'text': '# ', 'color': 'dim'},
            {'text': 'PASSED', 'color': 'green'},
            {'text': ' - No nulls found!', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, clear_before=True, title="The Solution"),

    # Scene 4: More assertions
    Scene([
        {'segments': [
            {'text': '# More checks? Just keep asserting:', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'assert ', 'color': 'purple'},
            {'text': 'orders.amount.between(', 'color': 'fg'},
            {'text': '0', 'color': 'orange'},
            {'text': ', ', 'color': 'fg'},
            {'text': '10000', 'color': 'orange'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'assert ', 'color': 'purple'},
            {'text': 'orders.status.isin([', 'color': 'fg'},
            {'text': "'pending'", 'color': 'green'},
            {'text': ', ', 'color': 'fg'},
            {'text': "'shipped'", 'color': 'green'},
            {'text': ', ', 'color': 'fg'},
            {'text': "'delivered'", 'color': 'green'},
            {'text': '])', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'assert ', 'color': 'purple'},
            {'text': 'orders.email.matches(', 'color': 'fg'},
            {'text': "r'^[\\w.-]+@[\\w.-]+$'", 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'assert ', 'color': 'purple'},
            {'text': 'orders.order_id.is_unique', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '# All checks ', 'color': 'dim'},
            {'text': 'PASSED', 'color': 'green'},
            {'text': '!', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, clear_before=True, title="Assertions"),

    # Scene 5: Quality Score
    Scene([
        {'segments': [
            {'text': '# Get an ISO 8000 quality score:', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'orders.quality_score()', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': '{', 'color': 'fg'},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'grade'", 'color': 'green'},
            {'text': ':        ', 'color': 'fg'},
            {'text': "'A'", 'color': 'green'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'score'", 'color': 'green'},
            {'text': ':        ', 'color': 'fg'},
            {'text': '97', 'color': 'orange'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'completeness'", 'color': 'green'},
            {'text': ': ', 'color': 'fg'},
            {'text': '0.98', 'color': 'orange'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'validity'", 'color': 'green'},
            {'text': ':     ', 'color': 'fg'},
            {'text': '0.99', 'color': 'orange'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'uniqueness'", 'color': 'green'},
            {'text': ':   ', 'color': 'fg'},
            {'text': '1.00', 'color': 'orange'},
        ], 'instant': True},
        {'text': '}', 'color': 'fg'},
    ], pause_after=PAUSE_LONG, clear_before=True, title="Quality Score"),

    # Scene 6: PII Detection
    Scene([
        {'segments': [
            {'text': '# Auto-detect sensitive data:', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'orders.detect_pii()', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'WARNING:', 'color': 'yellow'},
            {'text': ' PII detected in 3 columns:', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': '{', 'color': 'fg'},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'email'", 'color': 'green'},
            {'text': ':       ', 'color': 'fg'},
            {'text': "'email_address'", 'color': 'green'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'phone'", 'color': 'green'},
            {'text': ':       ', 'color': 'fg'},
            {'text': "'phone_number'", 'color': 'green'},
            {'text': ',', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': "'customer_id'", 'color': 'green'},
            {'text': ': ', 'color': 'fg'},
            {'text': "'identifier'", 'color': 'green'},
        ], 'instant': True},
        {'text': '}', 'color': 'fg'},
    ], pause_after=PAUSE_LONG, clear_before=True, title="PII Detection"),

    # Scene 7: Cross-dataset validation
    Scene([
        {'segments': [
            {'text': '# Validate foreign keys across datasets:', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'customers = connect(', 'color': 'fg'},
            {'text': '"customers.csv"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'assert ', 'color': 'purple'},
            {'text': 'orders.customer_id.references(customers.id)', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '# ', 'color': 'dim'},
            {'text': 'PASSED', 'color': 'green'},
            {'text': ' - All customer_ids exist in customers table', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, clear_before=True, title="FK Validation"),

    # Scene 8: Connect to anything
    Scene([
        {'segments': [
            {'text': '# Works with any data source:', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': '# Local files', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'connect(', 'color': 'fg'},
            {'text': '"data.csv"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'connect(', 'color': 'fg'},
            {'text': '"data/*.parquet"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': '# Cloud storage', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'connect(', 'color': 'fg'},
            {'text': '"s3://bucket/data.csv"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': '# Databases', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'connect(', 'color': 'fg'},
            {'text': '"snowflake://...orders"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '>>> ', 'color': 'cyan'},
            {'text': 'connect(', 'color': 'fg'},
            {'text': '"bigquery://...orders"', 'color': 'green'},
            {'text': ')', 'color': 'fg'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG, clear_before=True, title="Universal Connect"),

    # Scene 9: Performance comparison
    Scene([
        {'text': ''},
        {'segments': [
            {'text': '          Performance Comparison (1GB CSV)', 'color': 'white'},
        ], 'instant': True},
        {'text': ''},
        {'text': '  +--------------------+--------+--------+-------+', 'color': 'fg'},
        {'text': '  | Tool               |  Time  | Memory | Lines |', 'color': 'fg'},
        {'text': '  +--------------------+--------+--------+-------+', 'color': 'fg'},
        {'segments': [
            {'text': '  | ', 'color': 'fg'},
            {'text': 'DuckGuard', 'color': 'green'},
            {'text': '          |  ', 'color': 'fg'},
            {'text': '4 sec', 'color': 'green'},
            {'text': ' | ', 'color': 'fg'},
            {'text': '200 MB', 'color': 'green'},
            {'text': ' |     ', 'color': 'fg'},
            {'text': '3', 'color': 'green'},
            {'text': ' |', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '  | ', 'color': 'fg'},
            {'text': 'Great Expectations', 'color': 'red'},
            {'text': ' | ', 'color': 'fg'},
            {'text': '45 sec', 'color': 'red'},
            {'text': ' |   ', 'color': 'fg'},
            {'text': '4 GB', 'color': 'red'},
            {'text': ' |   ', 'color': 'fg'},
            {'text': '50+', 'color': 'red'},
            {'text': ' |', 'color': 'fg'},
        ], 'instant': True},
        {'text': '  +--------------------+--------+--------+-------+', 'color': 'fg'},
        {'text': ''},
        {'segments': [
            {'text': '           ', 'color': 'bg'},
            {'text': '10x faster', 'color': 'green'},
            {'text': '  |  ', 'color': 'dim'},
            {'text': '20x less memory', 'color': 'green'},
        ], 'instant': True},
    ], pause_after=PAUSE_XLLONG, clear_before=True, title="Performance"),

    # Scene 10: Final CTA
    Scene([
        {'text': ''},
        {'text': ''},
        {'segments': [
            {'text': '               pip install duckguard', 'color': 'white'},
        ], 'instant': True},
        {'text': ''},
        {'text': ''},
        {'segments': [
            {'text': '        ', 'color': 'bg'},
            {'text': 'github.com/XDataHubAI/duckguard', 'color': 'blue'},
        ], 'instant': True},
        {'text': ''},
        {'text': ''},
        {'segments': [
            {'text': '     ', 'color': 'bg'},
            {'text': 'Data quality testing should be as simple', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '            ', 'color': 'bg'},
            {'text': 'as pytest. Now it is.', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_XLLONG, clear_before=True, title="Get Started"),
]


def generate_frames() -> Tuple[List[Image.Image], List[int]]:
    """Generate all animation frames with typing effects."""
    renderer = TerminalRenderer()
    frames = []
    durations = []
    frame_duration = 50

    current_lines = []
    current_title = "Python"

    print(f"Generating frames for {len(DEMO_SCENES)} scenes...")

    for scene_idx, scene in enumerate(DEMO_SCENES):
        print(f"  Scene {scene_idx + 1}/{len(DEMO_SCENES)}: {scene.title}")

        if scene.clear_before:
            current_lines = []

        current_title = scene.title

        for line in scene.lines:
            if line.get('type') and 'type_text' in line:
                prefix_segments = line.get('segments', [])
                type_text = line['type_text']

                for char_idx in range(len(type_text) + 1):
                    img = renderer.create_base_frame(current_title)
                    draw = ImageDraw.Draw(img)

                    y = HEADER_HEIGHT + PADDING_Y

                    for prev_line in current_lines:
                        x = PADDING_X
                        if 'segments' in prev_line:
                            for seg in prev_line['segments']:
                                x = renderer.draw_text_segment(draw, x, y,
                                    seg['text'], seg.get('color', 'fg'))
                        elif 'text' in prev_line:
                            renderer.draw_text_segment(draw, x, y,
                                prev_line['text'], prev_line.get('color', 'fg'))
                        y += LINE_HEIGHT

                    x = PADDING_X
                    for seg in prefix_segments:
                        x = renderer.draw_text_segment(draw, x, y,
                            seg['text'], seg.get('color', 'fg'))

                    typed_portion = type_text[:char_idx]
                    if typed_portion:
                        x = renderer.draw_text_segment(draw, x, y, typed_portion, 'fg')

                    cursor_visible = (len(frames) // 10) % 2 == 0
                    renderer.draw_cursor(draw, x, y, cursor_visible)

                    frames.append(img)
                    durations.append(frame_duration)

                completed_line = {'segments': prefix_segments + [{'text': type_text, 'color': 'fg'}]}
                current_lines.append(completed_line)

            elif line.get('instant') or 'segments' in line or 'text' in line:
                if 'segments' in line:
                    current_lines.append({'segments': line['segments']})
                elif 'text' in line:
                    current_lines.append({'text': line.get('text', ''), 'color': line.get('color', 'fg')})

                img = renderer.create_base_frame(current_title)
                draw = ImageDraw.Draw(img)

                y = HEADER_HEIGHT + PADDING_Y
                for prev_line in current_lines:
                    x = PADDING_X
                    if 'segments' in prev_line:
                        for seg in prev_line['segments']:
                            x = renderer.draw_text_segment(draw, x, y,
                                seg['text'], seg.get('color', 'fg'))
                    elif 'text' in prev_line:
                        renderer.draw_text_segment(draw, x, y,
                            prev_line['text'], prev_line.get('color', 'fg'))
                    y += LINE_HEIGHT

                frames.append(img)
                durations.append(frame_duration)

        # Pause after scene
        for _ in range(scene.pause_after):
            img = renderer.create_base_frame(current_title)
            draw = ImageDraw.Draw(img)

            y = HEADER_HEIGHT + PADDING_Y
            for prev_line in current_lines:
                x = PADDING_X
                if 'segments' in prev_line:
                    for seg in prev_line['segments']:
                        x = renderer.draw_text_segment(draw, x, y,
                            seg['text'], seg.get('color', 'fg'))
                elif 'text' in prev_line:
                    renderer.draw_text_segment(draw, x, y,
                        prev_line['text'], prev_line.get('color', 'fg'))
                y += LINE_HEIGHT

            frames.append(img)
            durations.append(frame_duration)

    return frames, durations


def optimize_gif(frames: List[Image.Image], durations: List[int]) -> Tuple[List[Image.Image], List[int]]:
    """Optimize GIF by removing duplicate consecutive frames."""
    if not frames:
        return frames, durations

    optimized_frames = [frames[0]]
    optimized_durations = [durations[0]]

    for i in range(1, len(frames)):
        if frames[i].tobytes() == frames[i-1].tobytes():
            optimized_durations[-1] += durations[i]
        else:
            optimized_frames.append(frames[i])
            optimized_durations.append(durations[i])

    return optimized_frames, optimized_durations


def main():
    """Create the article animated GIF."""
    print("=" * 60)
    print("DuckGuard Article Demo GIF Generator")
    print("=" * 60)
    print()

    frames, durations = generate_frames()
    print(f"\nGenerated {len(frames)} raw frames")

    print("Optimizing frames...")
    frames, durations = optimize_gif(frames, durations)
    print(f"Optimized to {len(frames)} unique frames")

    total_ms = sum(durations)
    print(f"Total duration: {total_ms / 1000:.1f} seconds")

    output_path = Path(__file__).parent.parent / "assets" / "article_demo.gif"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Converting to optimized palette...")
    palette_frames = []
    for frame in frames:
        p_frame = frame.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        palette_frames.append(p_frame)

    print(f"\nSaving GIF to {output_path}...")
    palette_frames[0].save(
        output_path,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )

    file_size = output_path.stat().st_size
    print(f"\nDone!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size / 1024:.1f} KB")
    print(f"  Frames: {len(frames)}")
    print(f"  Duration: {total_ms / 1000:.1f}s")
    print()
    print("Scenes showcased:")
    print("  1. Title slide")
    print("  2. The Problem (Great Expectations boilerplate)")
    print("  3. The Solution (3 lines of code)")
    print("  4. More assertions")
    print("  5. Quality Score")
    print("  6. PII Detection")
    print("  7. FK Validation")
    print("  8. Universal Connect")
    print("  9. Performance comparison")
    print("  10. Call to action")

    return 0


if __name__ == "__main__":
    sys.exit(main())
