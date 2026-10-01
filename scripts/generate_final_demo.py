import os
import sys
import math
import subprocess
import cv2
import numpy as np

# Audio duration is exactly 100.59 seconds
FPS = 30
TOTAL_DURATION = 100.59
TOTAL_FRAMES = int(round(TOTAL_DURATION * FPS))
WIDTH = 1920
HEIGHT = 1080

import shutil

FFMPEG_PATH = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"C:\Python311\ffmpeg.exe"
AUDIO_FILE = "preimpact_audio.mp4"
OUTPUT_FILE = "preimpact_demo.mp4"

print(f"Target duration: {TOTAL_DURATION}s | {TOTAL_FRAMES} frames @ {FPS} FPS | Resolution: {WIDTH}x{HEIGHT}")

# ── Load Base Images ──────────────────────────────────────────────────────────
print("Loading HD frames...")
frame_01 = cv2.imread("demo_frames_hd/01_real_overview.png")
frame_02 = cv2.imread("demo_frames_hd/02_sim_phase1.png")
frame_03 = cv2.imread("demo_frames_hd/03_sim_phase2.png")
frame_04 = cv2.imread("demo_frames_hd/04_sim_phase3_rerouted.png")
frame_05 = cv2.imread("demo_frames_hd/05_final_overview.png")

# Load scroll frames for smooth right-panel scrolling
scroll_frames = []
for s in range(0, 451, 45):
    path = f"demo_frames_hd/scroll/scroll_{s:03d}.png"
    img = cv2.imread(path)
    scroll_frames.append(img)
print(f"Loaded {len(scroll_frames)} scroll frames.")

# Load cursor
cursor_img = cv2.imread("demo_frames/cursor.png", cv2.IMREAD_UNCHANGED)
cursor_h, cursor_w = cursor_img.shape[:2]

# ── Smooth Spline / Bezier Math ──────────────────────────────────────────────
def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    else:
        p = 2 * t - 2
        return 0.5 * p * p * p + 1

def lerp(a, b, t):
    return a + (b - a) * t

# Key cursor waypoints: (time_start, time_end, x_start, y_start, x_end, y_end, curve_x, curve_y)
# Engineered precisely for the narration timeline:
cursor_segments = [
    # 0.0s - 12.0s: Intro overview, gentle exploring movement over Kendrapara map
    (0.0, 5.0, 750, 480, 750, 480, 0, 0),
    (5.0, 12.0, 750, 480, 860, 520, 20, -15),
    (12.0, 20.0, 860, 520, 880, 500, -10, 10),
    # 20.0s - 26.0s: Gliding towards the Cyclone Scenario ribbon
    (20.0, 25.0, 880, 500, 420, 115, -40, -50),
    (25.0, 28.0, 420, 115, 620, 115, 0, -5),
    # 28.0s - 36.0s: Gliding back down across storm surge zone and core wind swath
    (28.0, 34.0, 620, 115, 850, 530, 40, 60),
    (34.0, 36.5, 850, 530, 850, 530, 0, 0),
    # 36.5s - 39.5s: "Let's select an exposed bridge" -> Smooth move to Bridge B006 (822, 556)
    (36.5, 39.2, 850, 530, 822, 556, -15, 20),
    (39.2, 39.6, 822, 556, 822, 556, 0, 0),  # Pause before click
    # 39.6s is CLICK!
    (39.6, 42.5, 822, 556, 822, 556, 0, 0),  # Hold on bridge marker
    # 42.5s - 45.5s: "baseline emergency travel time of 16.7 minutes" -> Move to baseline box
    (42.5, 45.2, 822, 556, 1616, 413, 60, -30),
    (45.2, 48.5, 1616, 413, 1616, 413, 0, 0), # Hold on 16.7 min baseline
    # 48.5s - 50.3s: "Now we run the counterfactual simulation" -> Move to Sim button
    (48.5, 50.2, 1616, 413, 894, 62, -80, -60),
    (50.2, 50.6, 894, 62, 894, 62, 0, 0),   # Pause before click
    # 50.6s is CLICK!
    (50.6, 52.0, 894, 62, 894, 62, 0, 0),
    # 52.0s - 55.5s: Move to map center to watch bridge severance / Phase 2
    (52.0, 55.0, 894, 62, 822, 556, 30, 80),
    (55.0, 56.5, 822, 556, 822, 556, 0, 0),
    # 56.5s - 59.0s: "travel time increases to 26.3 minutes" -> Move to Counterfactual box
    (56.5, 59.0, 822, 556, 1750, 413, 40, -20),
    (59.0, 61.0, 1750, 413, 1750, 413, 0, 0), # Hold on 26.3 min
    # 61.0s - 63.5s: "disruption of approximately 9.5 minutes" -> Point to +9.5 min callout
    (61.0, 63.0, 1750, 413, 1640, 515, -20, 20),
    (63.0, 64.5, 1640, 515, 1640, 515, 0, 0), # Hold on +9.5 min callout
    # 64.5s - 75.0s: "5 hospitals, 4 shelters, ~89,400 population" -> Impact grid
    (64.5, 66.5, 1640, 515, 1580, 615, -10, 20),
    (66.5, 69.5, 1580, 615, 1700, 615, 0, 0),
    (69.5, 74.5, 1700, 615, 1810, 615, 10, 0),
    # 74.5s - 83.0s: "resilience priority score" -> Priority meter (0.391)
    (74.5, 77.0, 1810, 615, 1705, 685, -20, 20),
    (77.0, 80.0, 1705, 685, 1705, 685, 0, 0), # Hold on Priority 0.391
    (80.0, 83.0, 1705, 685, 1705, 720, 0, 10), # Components breakdown
    # 83.0s - 90.0s: "Gemini converts computed evidence into structured briefing" -> Scroll & point to Briefing
    (83.0, 86.0, 1705, 720, 1680, 520, 0, -30),
    (86.0, 90.0, 1680, 520, 1680, 780, 0, 40), # Indicating preparation options
    # 90.0s - 100.59s: Closing statement -> Move cursor back to center map, peaceful hold
    (90.0, 94.0, 1680, 780, 760, 520, -100, -50),
    (94.0, 100.59, 760, 520, 760, 520, 0, 0),
]

clicks = [
    (39.6, 822, 556),  # Bridge B006 click
    (50.6, 894, 62),   # Run Counterfactual Simulation click
]

def get_cursor_pos(t):
    for seg in cursor_segments:
        t0, t1, x0, y0, x1, y1, cx, cy = seg
        if t0 <= t <= t1:
            dur = max(0.001, t1 - t0)
            u = (t - t0) / dur
            factor = ease_in_out_cubic(u)
            # Quadratic bezier with natural arc
            # P(u) = (1-u)^2 * P0 + 2*(1-u)*u * (Pmid + offset) + u^2 * P1
            mx = (x0 + x1) / 2 + cx
            my = (y0 + y1) / 2 + cy
            inv = 1.0 - factor
            x = inv * inv * x0 + 2 * inv * factor * mx + factor * factor * x1
            y = inv * inv * y0 + 2 * inv * factor * my + factor * factor * y1
            return int(round(x)), int(round(y))
    # Fallback
    return cursor_segments[-1][4], cursor_segments[-1][5]

def get_base_frame(t):
    # Base UI state selection
    if t < 50.6:
        base = frame_01
    elif t < 53.0:
        base = frame_02 # Phase 1
    elif t < 55.5:
        base = frame_03 # Phase 2 (bridge severed ✖)
    elif t < 83.0:
        base = frame_04 # Phase 3 (rerouted, +9.5m)
    elif t < 84.5:
        # Smooth scroll down to Gemini Brief
        # 1.5 seconds scroll duration across 11 frames
        u = (t - 83.0) / 1.5
        u_eased = ease_in_out_cubic(u)
        idx = int(round(u_eased * (len(scroll_frames) - 1)))
        base = scroll_frames[min(idx, len(scroll_frames) - 1)]
    elif t < 90.0:
        # Fully scrolled Gemini Brief
        base = scroll_frames[-1]
    elif t < 91.5:
        # Smooth scroll back up
        u = (t - 90.0) / 1.5
        u_eased = ease_in_out_cubic(u)
        idx = int(round((1.0 - u_eased) * (len(scroll_frames) - 1)))
        base = scroll_frames[max(0, min(idx, len(scroll_frames) - 1))]
    else:
        # Clean final overview
        base = frame_05

    return base.copy()

def overlay_cursor(canvas, x, y):
    h, w = canvas.shape[:2]
    # Bound cursor
    x = max(0, min(w - cursor_w - 1, x))
    y = max(0, min(h - cursor_h - 1, y))

    alpha = cursor_img[:, :, 3] / 255.0
    for c in range(3):
        canvas[y:y+cursor_h, x:x+cursor_w, c] = (
            alpha * cursor_img[:, :, c] +
            (1.0 - alpha) * canvas[y:y+cursor_h, x:x+cursor_w, c]
        )

def overlay_click_ripple(canvas, t):
    for c_time, cx, cy in clicks:
        dt = t - c_time
        if 0.0 <= dt <= 0.40:
            progress = dt / 0.40
            radius = int(5 + progress * 24)
            alpha = max(0.0, 1.0 - progress)

            overlay = canvas.copy()
            # Draw concentric ripple ring
            cv2.circle(overlay, (cx, cy), radius, (235, 99, 37), 2, cv2.LINE_AA)
            cv2.circle(overlay, (cx, cy), max(2, radius - 4), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha * 0.75, canvas, 1.0 - alpha * 0.75, 0, canvas)

# ── Launch FFmpeg Video Pipe ──────────────────────────────────────────────────
ffmpeg_cmd = [
    FFMPEG_PATH,
    "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-pix_fmt", "bgr24",
    "-r", str(FPS),
    "-i", "-",                     # Pipe raw video frames from stdin
    "-i", AUDIO_FILE,              # Input audio file
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-shortest",                   # Exactly match audio duration
    OUTPUT_FILE
]

print("Launching FFmpeg process...")
proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

print(f"Rendering {TOTAL_FRAMES} frames...")
for f in range(TOTAL_FRAMES):
    t = f / FPS

    # 1. Base frame
    canvas = get_base_frame(t)

    # 2. Click ripples
    overlay_click_ripple(canvas, t)

    # 3. Cursor
    cx, cy = get_cursor_pos(t)
    overlay_cursor(canvas, cx, cy)

    # Write frame to FFmpeg stdin
    proc.stdin.write(canvas.tobytes())

    if f % 150 == 0:
        print(f"Rendered frame {f}/{TOTAL_FRAMES} ({t:.1f}s / {TOTAL_DURATION}s)...")

proc.stdin.close()
proc.wait()
print(f"\nFinal demo video generated successfully: {OUTPUT_FILE}")
