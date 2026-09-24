"""Validated live settings and nonblocking audio; no camera or mouse side effects."""
import io
import json
import math
import os
from pathlib import Path
import queue
import struct
import tempfile
import threading
import wave

# MediaPipe canonical face mesh (zero-based landmark indices).
FACE_POINTS = {"Punta de nariz": 1, "Pera / mentón": 152, "Entrecejo": 168, "Frente": 10}
RANGES = {
    "gain_x": (5.0, 400.0, 62.0), "gain_y": (5.0, 400.0, 52.0),
    "mouth_threshold": (0.04, 0.15, 0.055),
    "dwell_time": (0.5, 5.0, 2.0), "dwell_radius": (3.0, 60.0, 20.0),
    "deadzone": (0.0, 2.0, 0.15), "smoothing": (0.1, 1.0, 0.65),
}
WINK_LEVELS = ["muy sensible", "sensible", "normal", "estricto", "muy estricto"]


def gain_index(value, levels):
    return max((i for i, level in enumerate(levels) if level <= value), default=0)


def step_gain(value, levels, direction, extra):
    if direction > 0:
        target = next((level for level in levels if level > value), value+extra)
    else:
        target = value-extra if value > levels[-1] else next((level for level in reversed(levels) if level < value), 5.0)
    return max(5.0, min(400.0, target))


def validated(values):
    result = dict(values)
    for key, (low, high, default) in RANGES.items():
        value = float(values.get(key, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key}: usá un valor entre {low:g} y {high:g}.")
        result[key] = value
    result["face_point"] = values.get("face_point", "Punta de nariz")
    if result["face_point"] not in FACE_POINTS:
        raise ValueError("Elegí un punto facial de la lista.")
    if result.get("wink_diff_sens", "normal") not in WINK_LEVELS:
        raise ValueError("Elegí una sensibilidad de guiño de la lista.")
    return result


def point_pixels(landmarks, name, width, height):
    point = landmarks[FACE_POINTS[name]]
    return (max(0.0, min(width-1.0, point.x*width)),
            max(0.0, min(height-1.0, point.y*height)))


def atomic_save_profiles(path, profiles):
    """A failed write leaves the previous profiles file intact."""
    path = Path(path).resolve()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".mouthclick-", suffix=".tmp", delete=False) as f:
            temporary = f.name
            json.dump(profiles, f, ensure_ascii=False, indent=4, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


class SettingsSession:
    def __init__(self, current, apply, save):
        self.original = dict(current)
        self.values = dict(current)
        self.apply, self.save = apply, save
        self.closed = False

    def preview(self, values):
        candidate = validated({**self.values, **values})
        self.apply(candidate)
        self.values = candidate

    def commit(self):
        self.save(self.values)  # Keep the panel open if saving fails.
        self.closed = True

    def cancel(self):
        if not self.closed:
            self.apply(self.original)
            self.closed = True


PATTERNS = {"Click izquierdo": [(880, 90)], "Doble click": [(880, 65), (1040, 65)],
            "Click derecho": [(520, 120)], "Drag toggle": [(700, 80), (420, 80)]}


def wave_bytes(pattern):
    rate = 22050
    samples = bytearray()
    for frequency, duration in pattern:
        count = rate * duration // 1000
        for i in range(count):
            envelope = min(1.0, i/110, (count-1-i)/110)
            samples.extend(struct.pack("<h", round(11000*envelope*math.sin(2*math.pi*frequency*i/rate))))
        samples.extend(b"\0\0" * (rate//100))
    result = io.BytesIO()
    with wave.open(result, "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(samples)
    return result.getvalue()


class ActionAudio:
    def __init__(self, backend=None):
        if backend is None:
            import winsound
            backend = winsound
        self.backend = backend
        self.sounds = {key: wave_bytes(pattern) for key, pattern in PATTERNS.items()}
        self.pending = queue.Queue(maxsize=1)
        self.error = ""
        self.stopped = threading.Event()
        self.worker = threading.Thread(target=self._run, name="MouthClick audio", daemon=True)
        self.worker.start()

    def play(self, action):
        if action not in self.sounds or self.stopped.is_set():
            return
        try:
            self.pending.put_nowait(action)
        except queue.Full:
            pass  # Do not build an audio backlog or block cursor control.

    def _run(self):
        while not self.stopped.is_set():
            try:
                action = self.pending.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.backend.PlaySound(self.sounds[action], self.backend.SND_MEMORY)
                self.error = ""
            except Exception as exc:
                self.error = f"No se pudo reproducir el sonido: {exc}"
            finally:
                self.pending.task_done()

    def close(self):
        self.stopped.set()
