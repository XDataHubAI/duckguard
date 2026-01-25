#!/usr/bin/env python3
"""
Create a POLISHED animated GIF demo showcasing ALL DuckGuard features.

Style: CLI commands like `duckguard discover`, tables, warning boxes.
Timing: Slower, more readable pace.

Usage:
    python create_polished_gif.py
"""

import sys
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)


# === DESIGN CONSTANTS ===

WIDTH = 780
HEIGHT = 500
PADDING_X = 20
PADDING_Y = 14
LINE_HEIGHT = 22
FONT_SIZE = 15
HEADER_HEIGHT = 36

# Colors - Matching the screenshot exactly
COLORS = {
    'bg': (30, 30, 40),           # Dark charcoal background (like screenshot)
    'header_bg': (55, 55, 65),    # Lighter gray header bar
    'fg': (255, 255, 255),        # Pure white text
    'dim': (180, 180, 180),       # Light gray for secondary text
    'cyan': (0, 255, 136),        # Bright green for $ prompt
    'green': (0, 255, 136),       # Bright green for success
    'red': (255, 95, 135),        # Bright red/pink for errors
    'yellow': (255, 170, 0),      # Bright orange for WARNING
    'magenta': (255, 85, 255),    # Bright magenta
    'blue': (0, 175, 215),        # Teal/cyan blue for DuckGuard
    'white': (255, 255, 255),     # Pure white
    'cursor': (255, 255, 255),    # White cursor
    'orange': (255, 170, 0),      # Same as yellow for WARNING
}

# Timing - SLOWER for better readability
PAUSE_SHORT = 40      # ~2 sec
PAUSE_MEDIUM = 60     # ~3 sec
PAUSE_LONG = 100      # ~5 sec


def get_font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Get a good monospace font."""
    font_names = [
        'Consolas', 'Cascadia Code', 'Cascadia Mono', 'JetBrains Mono',
        'Fira Code', 'Source Code Pro', 'DejaVu Sans Mono', 'Courier New',
    ]
    for font_name in font_names:
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

    def create_base_frame(self) -> Image.Image:
        img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['bg'])
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=COLORS['header_bg'])

        button_y = HEADER_HEIGHT // 2
        draw.ellipse([12, button_y - 6, 24, button_y + 6], fill=COLORS['red'])
        draw.ellipse([32, button_y - 6, 44, button_y + 6], fill=COLORS['yellow'])
        draw.ellipse([52, button_y - 6, 64, button_y + 6], fill=COLORS['green'])

        title = "DuckGuard Demo"
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
        bbox = draw.textbbox((x, y), text, font=self.font)
        return bbox[2]

    def draw_cursor(self, draw: ImageDraw.Draw, x: int, y: int, visible: bool = True):
        if visible:
            cursor_height = LINE_HEIGHT - 4
            draw.rectangle([x, y + 2, x + self.char_width - 2, y + cursor_height],
                          fill=COLORS['cursor'])


class Scene:
    def __init__(self, lines: List[dict], pause_after: int = PAUSE_MEDIUM,
                 clear_before: bool = False):
        self.lines = lines
        self.pause_after = pause_after
        self.clear_before = clear_before


# === DEMO SCRIPT - CLI STYLE (Single page per feature) ===

DEMO_SCENES = [
    # Scene 1: Title
    Scene([
        {'text': ''},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': '[>]<', 'color': 'yellow'},
            {'text': '  DuckGuard', 'color': 'blue'},
            {'text': ' - Data Quality That Just Works', 'color': 'dim'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '    ', 'color': 'bg'},
            {'text': 'Powered by DuckDB  |  Zero Config  |  Blazing Fast', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG),

    # Scene 2: Install (type command then show result)
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'pip install duckguard'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'pip install duckguard', 'color': 'fg'},
        ], 'instant': True},
        {'segments': [
            {'text': '[OK]', 'color': 'green'},
            {'text': ' Successfully installed duckguard-2.2.1', 'color': 'fg'},
        ], 'instant': True},
    ], pause_after=PAUSE_MEDIUM),

    # Scene 3: Discover command + FULL output on ONE page
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard discover orders.csv'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard discover orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Discovering: orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': 'Discovered 9 columns', 'color': 'fg'},
        {'text': ''},
        {'text': '+----------------------------------------------------------+', 'color': 'yellow'},
        {'text': '| WARNING: PII Detected                                    |', 'color': 'yellow'},
        {'text': '|   - email                                                |', 'color': 'fg'},
        {'text': '|   - created_at                                           |', 'color': 'fg'},
        {'text': '+----------------------------------------------------------+', 'color': 'yellow'},
        {'text': ''},
        {'text': '                    Column Analysis', 'color': 'white'},
        {'text': '+--------------+--------------+-----------------------+', 'color': 'fg'},
        {'text': '| Column       | Semantic     | Suggested Rules       |', 'color': 'fg'},
        {'text': '+--------------+--------------+-----------------------+', 'color': 'fg'},
        {'text': '| order_id     | identifier   | not_null              |', 'color': 'fg'},
        {'text': '| customer_id  | identifier   | not_null              |', 'color': 'fg'},
        {'text': '| product_name | unknown      | -                     |', 'color': 'fg'},
        {'text': '| quantity     | slug         | -                     |', 'color': 'fg'},
        {'text': '| unit_price   | longitude    | range: [-180, 180]    |', 'color': 'fg'},
        {'text': '+--------------+--------------+-----------------------+', 'color': 'fg'},
    ], pause_after=PAUSE_LONG),

    # Scene 4: Check command (matching actual CLI output)
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard check orders.csv'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard check orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Checking: examples/sample_data/orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': '  Rows       25', 'color': 'fg'},
        {'text': '  Columns    9', 'color': 'fg'},
        {'text': ''},
        {'text': '+----------------+--------+----------+', 'color': 'fg'},
        {'text': '| Check          | Status | Details  |', 'color': 'fg'},
        {'text': '+----------------+--------+----------+', 'color': 'fg'},
        {'text': '| Row count > 0  | PASS   | 25 rows  |', 'color': 'fg'},
        {'text': '+----------------+--------+----------+', 'color': 'fg'},
        {'text': ''},
        {'text': '+-----------------------------------------------------+', 'color': 'fg'},
        {'text': '| Quality Score: 97/100 (Grade: A)                    |', 'color': 'fg'},
        {'text': '+-----------------------------------------------------+', 'color': 'fg'},
    ], pause_after=PAUSE_LONG),

    # Scene 5: Anomaly detection (matching actual CLI output)
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard anomaly orders.csv -c total_amount'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard anomaly orders.csv -c total_amount', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Detecting anomalies in: examples/sample_data/orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'WARNING:', 'color': 'yellow'},
            {'text': ' 1 anomalies detected', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': '                       Anomalies', 'color': 'white'},
        {'text': '+--------------+---------------+-------+----------------------+', 'color': 'fg'},
        {'text': '| Column       | Type          | Score | Message              |', 'color': 'fg'},
        {'text': '+--------------+---------------+-------+----------------------+', 'color': 'fg'},
        {'text': '| total_amount | value_outlier |  3.27 | anomalous values     |', 'color': 'fg'},
        {'text': '+--------------+---------------+-------+----------------------+', 'color': 'fg'},
        {'text': ''},
        {'text': 'Anomalies found: 1', 'color': 'yellow'},
    ], pause_after=PAUSE_LONG),

    # Scene 6: Freshness check
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard freshness orders.csv'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard freshness orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Freshness Check', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '  File modified:  ', 'color': 'dim'},
            {'text': '2 hours ago', 'color': 'green'},
        ], 'instant': True},
        {'segments': [
            {'text': '  Latest record:  ', 'color': 'dim'},
            {'text': '45 minutes ago', 'color': 'green'},
        ], 'instant': True},
        {'segments': [
            {'text': '  Status:         ', 'color': 'dim'},
            {'text': 'FRESH', 'color': 'green'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '  [PASS]', 'color': 'green'},
            {'text': ' Data is within 24h threshold', 'color': 'fg'},
        ], 'instant': True},
    ], pause_after=PAUSE_MEDIUM),

    # Scene 7: Schema evolution
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard schema orders.csv --track'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard schema orders.csv --track', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Schema Evolution', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '  [!]', 'color': 'yellow'},
            {'text': ' Changes detected since last run:', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '    + ', 'color': 'green'},
            {'text': 'discount_code', 'color': 'green'},
            {'text': ' (VARCHAR) - new column', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '    ~ ', 'color': 'yellow'},
            {'text': 'price', 'color': 'yellow'},
            {'text': ': INTEGER -> DOUBLE', 'color': 'dim'},
        ], 'instant': True},
        {'segments': [
            {'text': '    - ', 'color': 'red'},
            {'text': 'legacy_id', 'color': 'red'},
            {'text': ' - column removed', 'color': 'dim'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG),

    # Scene 8: Report generation (matching actual CLI output)
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard report orders.csv'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard report orders.csv', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Generating HTML report', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'text': 'Source: examples/sample_data/orders.csv', 'color': 'fg'},
        {'text': 'Rows: 25 | Columns: 9', 'color': 'fg'},
        {'text': ''},
        {'segments': [
            {'text': 'Validation: ', 'color': 'fg'},
            {'text': 'PASS', 'color': 'green'},
            {'text': 'ED', 'color': 'fg'},
        ], 'instant': True},
        {'text': 'Quality Score: 100.0%', 'color': 'fg'},
        {'text': 'Checks: 24/24 passed', 'color': 'fg'},
        {'text': ''},
        {'segments': [
            {'text': 'SAVED', 'color': 'green'},
            {'text': ' Report saved to', 'color': 'fg'},
        ], 'instant': True},
        {'text': 'C:\\Users\\...\\temp.html', 'color': 'fg'},
        {'text': 'Open in browser to view the report', 'color': 'fg'},
    ], pause_after=PAUSE_MEDIUM),

    # Scene 9: History/trends
    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
        ], 'type': True, 'type_text': 'duckguard history orders.csv --days 7'},
    ], pause_after=PAUSE_SHORT, clear_before=True),

    Scene([
        {'segments': [
            {'text': '$ ', 'color': 'cyan'},
            {'text': 'duckguard history orders.csv --days 7', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': 'DuckGuard', 'color': 'blue'},
            {'text': ' Quality Trends (last 7 days)', 'color': 'fg'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '  Mon: ', 'color': 'dim'},
            {'text': '78', 'color': 'yellow'},
            {'text': '  Tue: ', 'color': 'dim'},
            {'text': '80', 'color': 'yellow'},
            {'text': '  Wed: ', 'color': 'dim'},
            {'text': '82', 'color': 'green'},
            {'text': '  Thu: ', 'color': 'dim'},
            {'text': '81', 'color': 'green'},
            {'text': '  Fri: ', 'color': 'dim'},
            {'text': '84', 'color': 'green'},
        ], 'instant': True},
        {'text': ''},
        {'segments': [
            {'text': '  [^]', 'color': 'green'},
            {'text': ' Quality improving: +7.7% this week', 'color': 'green'},
        ], 'instant': True},
    ], pause_after=PAUSE_MEDIUM),

    # Scene 10: Performance comparison
    Scene([
        {'text': '         Performance Comparison (1GB CSV)', 'color': 'white'},
        {'text': ''},
        {'text': '  +--------------------+--------+--------+------+', 'color': 'fg'},
        {'text': '  | Tool               |  Time  | Memory | Code |', 'color': 'fg'},
        {'text': '  +--------------------+--------+--------+------+', 'color': 'fg'},
        {'text': '  | DuckGuard          |  4 sec | 200 MB |   3  |', 'color': 'green'},
        {'text': '  | Great Expectations | 45 sec |   4 GB |  50+ |', 'color': 'red'},
        {'text': '  +--------------------+--------+--------+------+', 'color': 'fg'},
    ], pause_after=PAUSE_LONG, clear_before=True),

    # Scene 11: Final CTA
    Scene([
        {'text': ''},
        {'text': ''},
        {'segments': [
            {'text': '              ', 'color': 'bg'},
            {'text': '[>]<', 'color': 'yellow'},
            {'text': '  DuckGuard', 'color': 'blue'},
        ], 'instant': True},
        {'text': ''},
        {'text': '           pip install duckguard', 'color': 'white'},
        {'text': '        github.com/XDataHubAI/duckguard', 'color': 'dim'},
        {'text': ''},
        {'segments': [
            {'text': '              ', 'color': 'bg'},
            {'text': 'Star us on GitHub!', 'color': 'yellow'},
        ], 'instant': True},
    ], pause_after=PAUSE_LONG * 2, clear_before=True),
]


def generate_frames() -> Tuple[List[Image.Image], List[int]]:
    """Generate all animation frames with typing effects."""
    renderer = TerminalRenderer()
    frames = []
    durations = []
    frame_duration = 50

    current_lines = []

    print(f"Generating frames for {len(DEMO_SCENES)} scenes...")

    for scene_idx, scene in enumerate(DEMO_SCENES):
        print(f"  Scene {scene_idx + 1}/{len(DEMO_SCENES)}...")

        if scene.clear_before:
            current_lines = []

        for line in scene.lines:
            if line.get('type') and 'type_text' in line:
                prefix_segments = line.get('segments', [])
                type_text = line['type_text']

                for char_idx in range(len(type_text) + 1):
                    img = renderer.create_base_frame()
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

                img = renderer.create_base_frame()
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

            if line.get('pause'):
                pause_frames = line['pause']
                for _ in range(pause_frames):
                    img = renderer.create_base_frame()
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

        for _ in range(scene.pause_after):
            img = renderer.create_base_frame()
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
    """Create the polished animated GIF."""
    print("=" * 60)
    print("DuckGuard CLI-Style Demo GIF Generator")
    print("=" * 60)
    print()

    frames, durations = generate_frames()
    print(f"\nGenerated {len(frames)} raw frames")

    print("Optimizing frames...")
    frames, durations = optimize_gif(frames, durations)
    print(f"Optimized to {len(frames)} unique frames")

    total_ms = sum(durations)
    print(f"Total duration: {total_ms / 1000:.1f} seconds")

    output_path = Path(__file__).parent.parent / "assets" / "demo.gif"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Converting to optimized palette...")
    palette_frames = []
    for frame in frames:
        # Use 64 colors with MAXCOVERAGE to preserve dark charcoal background
        p_frame = frame.quantize(colors=64, method=Image.Quantize.MAXCOVERAGE)
        palette_frames.append(p_frame)

    print(f"\nSaving GIF to {output_path}...")
    palette_frames[0].save(
        output_path,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )

    file_size = output_path.stat().st_size
    print(f"\nDone!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size / 1024:.1f} KB")
    print(f"  Frames: {len(frames)}")
    print(f"  Duration: {total_ms / 1000:.1f}s")
    print()
    print("CLI Commands showcased:")
    print("  - duckguard discover (PII detection, column analysis)")
    print("  - duckguard check (validations)")
    print("  - duckguard anomaly (ML detection)")
    print("  - duckguard freshness (data freshness)")
    print("  - duckguard schema (evolution tracking)")
    print("  - duckguard report (HTML/PDF reports)")
    print("  - duckguard history (trends)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
