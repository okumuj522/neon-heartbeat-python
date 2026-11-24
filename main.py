"""A small, animated neon ECG display made with Python's standard library."""

import colorsys
import math
import struct
import time
import tkinter as tk
import wave
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None


WIDTH = 1000
HEIGHT = 640
BACKGROUND = "#07111f"


class NeonHeartbeat:
    """Draw a glowing ECG trace on a Tkinter canvas."""

    def __init__(self, root):
        self.root = root
        self.root.title("Neon Heartbeat | Python Animation")
        self.root.configure(bg=BACKGROUND)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg=BACKGROUND,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.bpm = 48
        self.pixels_per_beat = 180
        self.muted = False
        self.started_at = time.perf_counter()
        self.paused = False
        self.paused_at = None
        self.elapsed_before_pause = 0.0

        self._draw_panel()
        self._draw_trace()
        self._prepare_heartbeat_audio()
        self._start_heartbeat_sound()
        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("m", self.toggle_mute)
        self.root.bind("M", self.toggle_mute)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(30, self.animate)

    def _draw_panel(self):
        """Create the background grid and labels once."""
        self.canvas.create_rectangle(
            18, 18, WIDTH - 18, HEIGHT - 18,
            outline="#183449", width=1,
        )

        grid_left, grid_top = 42, 150
        grid_right, grid_bottom = WIDTH - 42, HEIGHT - 92
        for x in range(grid_left, grid_right, 32):
            color = "#173044" if (x - grid_left) % 160 == 0 else "#0d2234"
            self.canvas.create_line(x, grid_top, x, grid_bottom, fill=color)
        for y in range(grid_top, grid_bottom, 32):
            color = "#173044" if (y - grid_top) % 160 == 0 else "#0d2234"
            self.canvas.create_line(grid_left, y, grid_right, y, fill=color)

        self.canvas.create_text(
            54, 54, anchor="w", text="NEON HEARTBEAT",
            fill="#e8f7ff", font=("Segoe UI", 25, "bold"),
        )
        self.canvas.create_text(
            56, 88, anchor="w", text="A Python ECG animation",
            fill="#85a9bd", font=("Segoe UI", 11),
        )

        self.canvas.create_oval(804, 51, 816, 63, fill="#51f5b4", outline="")
        self.canvas.create_text(
            827, 57, anchor="w", text="SIGNAL ACTIVE",
            fill="#9be9cf", font=("Segoe UI", 10, "bold"),
        )
        self.canvas.create_text(
            WIDTH - 54, 91, anchor="e", text=f"{self.bpm} BPM",
            fill="#60eaff", font=("Segoe UI", 22, "bold"),
        )

        self.canvas.create_text(
            52, HEIGHT - 55, anchor="w",
            text="LIVE ECG  /  PYTHON CANVAS",
            fill="#62849a", font=("Consolas", 10, "bold"),
        )
        self.canvas.create_text(
            WIDTH - 52, HEIGHT - 55, anchor="e",
            text="SPACE  PAUSE   •   M  SOUND   •   ESC  EXIT",
            fill="#62849a", font=("Consolas", 10),
        )

        center_y = (grid_top + grid_bottom) / 2
        self.canvas.create_text(
            grid_left + 10, center_y - 25,
            anchor="w", text="ECG",
            fill="#57758a", font=("Consolas", 9, "bold"),
        )

    def _draw_trace(self):
        """Make layered lines; the wider layers create a simple neon glow."""
        self.trace_layers = []
        for color, width in (
            ("#ff1493", 20),
            ("#ff3d00", 13),
            ("#faff00", 8),
            ("#00ffb3", 4),
            ("#38f8ff", 2),
        ):
            line = self.canvas.create_line(
                0, 0, 1, 1,
                fill=color,
                width=width,
                smooth=True,
                splinesteps=18,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
            self.trace_layers.append(line)

    @staticmethod
    def _gaussian(distance, width):
        return math.exp(-((distance / width) ** 2))

    def _ecg_height(self, phase):
        """Return the vertical height of one stylized heartbeat cycle."""
        # Small P wave, sharp QRS spike, and rounded T wave.
        return (
            10 * self._gaussian(phase - 0.18, 0.045)
            - 17 * self._gaussian(phase - 0.385, 0.018)
            + 178 * self._gaussian(phase - 0.415, 0.012)
            - 42 * self._gaussian(phase - 0.445, 0.020)
            + 29 * self._gaussian(phase - 0.68, 0.080)
        )

    def animate(self):
        """Move the ECG trace and schedule the next animation frame."""
        if not self.paused:
            if self.paused_at is None:
                elapsed = time.perf_counter() - self.started_at
            else:
                elapsed = self.elapsed_before_pause + time.perf_counter() - self.paused_at

            left, right = 44, WIDTH - 44
            top, bottom = 152, HEIGHT - 94
            center_y = (top + bottom) / 2
            points = []
            step = 4
            beat_phase_offset = elapsed * (self.bpm / 60)

            for x in range(left, right + 1, step):
                phase = ((x - left) / self.pixels_per_beat - beat_phase_offset) % 1.0
                y = center_y - self._ecg_height(phase)
                y = max(top + 15, min(bottom - 15, y))
                points.extend((x, y))

            for line in self.trace_layers:
                self.canvas.coords(line, *points)

            # Cycle the glow through the rainbow while keeping a bright core.
            glow_colors = []
            for layer, brightness in enumerate((0.52, 0.68, 0.84, 1.0, 1.0)):
                hue = (elapsed * 0.10 + layer * 0.12) % 1.0
                red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, brightness)
                glow_colors.append(
                    f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"
                )
            for line, color in zip(self.trace_layers, glow_colors):
                self.canvas.itemconfigure(line, fill=color)

        self.root.after(30, self.animate)

    def toggle_pause(self, _event=None):
        """Pause or resume the animation with the space bar."""
        now = time.perf_counter()
        if self.paused:
            self.paused = False
            self.started_at = now - self.elapsed_before_pause
            self.paused_at = None
            if not self.muted:
                self._start_heartbeat_sound()
        else:
            if self.paused_at is None:
                self.elapsed_before_pause = now - self.started_at
            self.paused_at = now
            self.paused = True
            self._stop_heartbeat_sound()

    def _prepare_heartbeat_audio(self):
        """Create a short, soft double-beat WAV for Windows playback."""
        if winsound is None:
            return

        self.sound_path = Path(__file__).with_name("heartbeat.wav")
        sample_rate = 22050
        sample_count = int(sample_rate * 60 / self.bpm)
        samples = []
        thumps = ((0.0, 0.18, 76), (0.22, 0.21, 58))

        for index in range(sample_count):
            moment = index / sample_rate
            sound = 0.0
            for start, duration, frequency in thumps:
                local_time = moment - start
                if 0 <= local_time < duration:
                    envelope = math.exp(-local_time * 16) * (1 - local_time / duration)
                    tone = math.sin(2 * math.pi * frequency * local_time)
                    tone += 0.25 * math.sin(4 * math.pi * frequency * local_time)
                    sound += tone * envelope * 0.42
            samples.append(max(-32767, min(32767, int(sound * 32767))))

        with wave.open(str(self.sound_path), "wb") as sound_file:
            sound_file.setnchannels(1)
            sound_file.setsampwidth(2)
            sound_file.setframerate(sample_rate)
            sound_file.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def _start_heartbeat_sound(self):
        if winsound is not None and not self.paused and not self.muted:
            try:
                winsound.PlaySound(
                    str(self.sound_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
            except (RuntimeError, AttributeError):
                pass

    @staticmethod
    def _stop_heartbeat_sound():
        if winsound is not None:
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError:
                pass

    def toggle_mute(self, _event=None):
        self.muted = not self.muted
        if self.muted:
            self._stop_heartbeat_sound()
        else:
            self._start_heartbeat_sound()

    def close(self):
        self._stop_heartbeat_sound()
        self.root.destroy()


def main():
    root = tk.Tk()
    NeonHeartbeat(root)
    root.mainloop()


if __name__ == "__main__":
    main()
