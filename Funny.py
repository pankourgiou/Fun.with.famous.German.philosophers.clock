"""
philosopher_clock.py
Analog clock with 12 famous German philosophers at hour marks.
Every second the philosopher for the current hour 'says' the time in 24-hour format.
Uses Tkinter for the GUI and pyttsx3 for offline TTS.

Dependencies:
    pip install pyttsx3 pillow
"""

import math
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk
from datetime import datetime

try:
    import pyttsx3
except Exception:
    raise RuntimeError("pyttsx3 is required. Install with: pip install pyttsx3")

# --- Configuration -----------------------------------------------------------
SIZE = 500                 # canvas size (px)
RADIUS = SIZE // 2 - 40    # clock face radius
CENTER = SIZE // 2
UPDATE_MS = 1000           # update every 1000 ms

# 12 famous German philosophers (simple, recognisable list)
PHILOSOPHERS = [
    "Leibniz",      # hour 1 (maps to 1 or 13)
    "Kant",         # 2
    "Hegel",        # 3
    "Fichte",       # 4
    "Schopenhauer", # 5
    "Nietzsche",    # 6
    "Marx",         # 7
    "Engels",       # 8
    "Herder",       # 9
    "Lessing",      # 10
    "Heidegger",    # 11
    "Habermas"      # 12 (maps to 12 or 0)
]

# Humorous short 'voices' or sayings for each philosopher (kept generic)
PHRASES = {
    "Leibniz":      "Ah, the best of all possible times: {h} hours, {m} minutes and {s} seconds.",
    "Kant":         "By duty I declare: it is {h} hours, {m} minutes and {s} seconds.",
    "Hegel":        "The time is (in dialectical motion) {h}:{m}:{s}.",
    "Fichte":       "Consciousness proclaims: {h} hours, {m} minutes, {s} seconds.",
    "Schopenhauer": "Time, the will's annoying companion: {h}h {m}m {s}s.",
    "Nietzsche":    "Behold the hour: {h} hours, {m} minutes, {s} seconds — become who you are.",
    "Marx":         "Workers of the world note the time: {h}:{m}:{s}.",
    "Engels":       "Material conditions indicate: {h} hours {m} minutes {s} seconds.",
    "Herder":       "Time tells culture: it's {h} hours and {m} minutes, {s} seconds.",
    "Lessing":      "In the theatre of life — the clock says {h}:{m}:{s}.",
    "Heidegger":    "Time is (being): {h} hours, {m} minutes, {s} seconds.",
    "Habermas":     "Communicative act: the time is {h}:{m}:{s}."
}

# TTS engine and a queue to avoid overlap
tts_engine = pyttsx3.init()
tts_queue = queue.Queue()

# Optionally tweak rate/volume globally here:
tts_engine.setProperty("rate", 160)
tts_engine.setProperty("volume", 0.9)

def tts_worker(q):
    """Thread target to speak queued texts sequentially."""
    while True:
        text = q.get()
        if text is None:
            break
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print("TTS error:", e)
        q.task_done()

# Start TTS worker thread
threading.Thread(target=tts_worker, args=(tts_queue,), daemon=True).start()

# --- Helper functions --------------------------------------------------------
def hour_to_philosopher(hour24):
    """Map a 24-hour hour to one of the 12 philosophers.
    E.g., hour24 0 -> position 12 -> Habermas, 13 -> 1 -> Leibniz, etc."""
    # convert to 12-hour index: 1..12
    h12 = hour24 % 12
    if h12 == 0:
        h12 = 12
    idx = (h12 - 1) % 12
    return PHILOSOPHERS[idx]

def format_time_phrase(h, m, s):
    """Return the philosopher's line for the given time (24-hour)."""
    phil = hour_to_philosopher(h)
    template = PHRASES.get(phil, "It's {h}:{m}:{s}.")
    # zero-pad minutes and seconds for nicer speech sometimes but keep hours numeric
    return phil + " says: " + template.format(h=str(h), m=str(m).zfill(2), s=str(s).zfill(2))

def polar_to_cart(center_x, center_y, angle_deg, radius):
    """Convert polar coords (angle in degrees, 0 degrees pointing up) to canvas coordinates."""
    # Convert so 0 degrees is at top and angle increases clockwise
    angle_rad = math.radians(angle_deg - 90)
    x = center_x + radius * math.cos(angle_rad)
    y = center_y + radius * math.sin(angle_rad)
    return x, y

# --- GUI ---------------------------------------------------------------------
class PhilosopherClock(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clock of German Philosophers — 24h, 60m, 60s (funny!)")
        self.resizable(False, False)

        self.canvas = tk.Canvas(self, width=SIZE, height=SIZE, bg="white")
        self.canvas.grid(row=0, column=0, columnspan=3)

        # Controls
        self.speak_var = tk.BooleanVar(value=True)
        self.speak_check = ttk.Checkbutton(self, text="Speak time (toggle)", variable=self.speak_var)
        self.speak_check.grid(row=1, column=0, sticky="w", padx=10, pady=6)

        self.mute_btn = ttk.Button(self, text="Mute Now", command=self.mute_now)
        self.mute_btn.grid(row=1, column=1)

        self.quit_btn = ttk.Button(self, text="Quit", command=self.quit_app)
        self.quit_btn.grid(row=1, column=2, sticky="e", padx=10)

        # Draw static clock face
        self.draw_face()

        # Hand ids for updating
        self.hour_hand = None
        self.min_hand = None
        self.sec_hand = None

        # last second spoken so we don't repeat too fast
        self.last_spoken_second = -1

        # start the update loop
        self.update_clock()

    def draw_face(self):
        c = self.canvas
        # Outer circle
        c.create_oval(CENTER - RADIUS, CENTER - RADIUS, CENTER + RADIUS, CENTER + RADIUS, width=4, outline="#444")
        # Center dot
        c.create_oval(CENTER - 6, CENTER - 6, CENTER + 6, CENTER + 6, fill="#000")
        # Hour markers and philosopher names
        for i in range(12):
            angle = i * 30  # 360 / 12
            # mark positions slightly inside the rim
            mark_outer = RADIUS - 8
            mark_inner = RADIUS - 22
            x1, y1 = polar_to_cart(CENTER, CENTER, angle, mark_inner)
            x2, y2 = polar_to_cart(CENTER, CENTER, angle, mark_outer)
            c.create_line(x1, y1, x2, y2, width=3)
            # names slightly further inward
            name_pos = RADIUS - 50
            nx, ny = polar_to_cart(CENTER, CENTER, angle, name_pos)
            # philosopher name: index mapping: i=0 -> 12 o'clock -> PHILOSOPHERS[11]
            # We'll align so that 12 o'clock is PHILOSOPHERS[11] (Habermas)
            # Compute label index:
            label_idx = (i + 11) % 12
            name = PHILOSOPHERS[label_idx]
            c.create_text(nx, ny, text=name, font=("Helvetica", 10, "bold"))

    def draw_hands(self, now):
        h = now.hour
        m = now.minute
        s = now.second

        # compute angles
        # For 24-hour display we still use 12-hour circle for positioning hands
        # Hour hand angle: each hour is 30 degrees; include minute fraction
        hour_in_12 = (h % 12) + m / 60.0
        hour_angle = hour_in_12 * 30

        minute_angle = (m + s / 60.0) * 6  # 360/60 = 6 deg per minute
        second_angle = s * 6

        # compute end points
        hx, hy = polar_to_cart(CENTER, CENTER, hour_angle, RADIUS * 0.5)
        mx, my = polar_to_cart(CENTER, CENTER, minute_angle, RADIUS * 0.75)
        sx, sy = polar_to_cart(CENTER, CENTER, second_angle, RADIUS * 0.9)

        c = self.canvas
        # remove previous hands
        if self.hour_hand:
            c.delete(self.hour_hand)
        if self.min_hand:
            c.delete(self.min_hand)
        if self.sec_hand:
            c.delete(self.sec_hand)

        # draw new hands
        self.hour_hand = c.create_line(CENTER, CENTER, hx, hy, width=6, capstyle='round')
        self.min_hand = c.create_line(CENTER, CENTER, mx, my, width=4, capstyle='round')
        self.sec_hand = c.create_line(CENTER, CENTER, sx, sy, width=2, fill='red', capstyle='round')

        # digital readout at bottom
        time_str = now.strftime("%H:%M:%S")
        # remove previous digital if exists by tag
        c.delete("digital")
        c.create_text(CENTER, SIZE - 20, text=time_str + "  (24h format)", font=("Helvetica", 12), tags="digital")

    def update_clock(self):
        now = datetime.now()
        self.draw_hands(now)

        # Decide whether to speak. We'll speak every second if speak_var True.
        if self.speak_var.get():
            # Avoid enqueuing the same second multiple times if update floods
            cur_second = now.second
            if cur_second != self.last_spoken_second:
                phrase = format_time_phrase(now.hour, now.minute, now.second)
                # Queue the TTS in a separate thread
                try:
                    tts_queue.put_nowait(phrase)
                except queue.Full:
                    pass
                self.last_spoken_second = cur_second

        # schedule the next update roughly on the next second boundary
        self.after(UPDATE_MS, self.update_clock)

    def mute_now(self):
        # clear queued items (best-effort) and stop any immediate speaking by putting a short message
        while not tts_queue.empty():
            try:
                tts_queue.get_nowait()
                tts_queue.task_done()
            except queue.Empty:
                break
        # Announce mute briefly
        if self.speak_var.get():
            tts_queue.put_nowait("Muted. Philosophy will be silent, temporarily.")
        self.speak_var.set(False)

    def quit_app(self):
        # Put sentinel to stop tts worker (not strictly necessary as daemon thread)
        try:
            tts_queue.put_nowait(None)
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    app = PhilosopherClock()
    app.mainloop()
