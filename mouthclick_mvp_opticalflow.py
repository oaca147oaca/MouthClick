import os
import sys
from mouthclick_instance import acquire
if not acquire():
    raise SystemExit(0)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import time
import json
import math
import ctypes
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
from mouthclick_ui import Menu, field, toggle, hint, style_floating, draw_status, ActionsBubble
from mouthclick_ui import PagedMenu
from pynput import keyboard
import queue
from tkinter import messagebox
from mouthclick_runtime import FACE_POINTS, RANGES, validated, point_pixels, atomic_save_profiles, ActionAudio, gain_index, step_gain
from mouthclick_live_ui import LiveSettings, numeric, ConfirmAction, WindowChrome
from mouthclick_runtime import BrowGestures
from mouthclick_runtime import profile_save_name
from mouthclick_runtime import LatestFrameCapture
from mouthclick_alignment import AlignmentGuide

try:
    from pygrabber.dshow_graph import FilterGraph
except Exception:
    FilterGraph = None


# ============================================================
# MouthClick MVP Optical Flow
# - Movimiento del mouse por tracking óptico de un punto elegido
# - MediaPipe FaceMesh solo para gestos: boca / guiño
# - Perfiles JSON
# - Sensibilidad X/Y separada
# - Hotkeys: F12 salir | F11 pausa | F7 centrar | R re-seleccionar punto | M ventana
# ============================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

PROFILES_FILE = os.path.join(os.path.dirname(sys.executable), "profiles.json") if getattr(sys, "frozen", False) else "profiles.json"

AVAILABLE_ACTIONS = [
    "Nada",
    "Click izquierdo",
    "Doble click",
    "Click derecho",
    "Drag toggle"
]

SENS_LEVELS = ["baja", "media", "alta", "muy alta", "extrema"]
LEGACY_SENS_MAP = {
    "media-baja": "media",
    "media-alta": "alta",
}

WINK_DIFF_LEVELS = ["muy sensible", "sensible", "normal", "estricto", "muy estricto",
                    "extra estricto", "ultra estricto", "estricto máximo", "estricto extremo"]
WINK_DIFF_THR_BY_LEVEL = {
    "muy sensible": 0.030,
    "sensible": 0.045,
    "normal": 0.060,
    "estricto": 0.080,
    "muy estricto": 0.105,
    "extra estricto": 0.120,
    "ultra estricto": 0.135,
    "estricto máximo": 0.150,
    "estricto extremo": 0.165,
}
WINK_CLOSED_RATIO_BY_LEVEL = {
    "muy sensible": 0.78,
    "sensible": 0.72,
    "normal": 0.66,
    "estricto": 0.60,
    "muy estricto": 0.54,
    "extra estricto": 0.48,
    "ultra estricto": 0.42,
    "estricto máximo": 0.36,
    "estricto extremo": 0.30,
}

# Ganancia por pixel de cámara. Ajustable con F3/F4 y F1/F2
GAIN_X_BY_LEVEL = {
    "baja": 42.0,
    "media": 62.0,
    "alta": 74.0,
    "muy alta": 88.0,
    "extrema": 104.0,
}

GAIN_Y_BY_LEVEL = {
    "baja": 36.0,
    "media": 52.0,
    "alta": 64.0,
    "muy alta": 78.0,
    "extrema": 92.0,
}

DEFAULT_PROFILE = {
    "mouth": "Click izquierdo",
    "wink_left": "Nada",
    "wink_right": "Nada",
    "brow_raise": "Nada",
    "brow_frown": "Nada",
    "camera": 0,
    "sens_x": "media",
    "sens_y": "media",
    "sensitivity": "media",  # compatibilidad con profiles viejos
    "stabilize": True,
    "zoom": False,
    "dwell_time": 2.0,
    "wink_diff_sens": "normal",
    "tracking_mode": "Punto facial",
    "face_point": "Punta de nariz",
    "sound_enabled": True,
    "dwell_enabled": False,
}


def load_profiles():
    if not os.path.exists(PROFILES_FILE):
        return {"Default": DEFAULT_PROFILE.copy()}

    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or not data:
                return {"Default": DEFAULT_PROFILE.copy()}
            return data
    except Exception:
        return {"Default": DEFAULT_PROFILE.copy()}


def save_profiles(profiles):
    atomic_save_profiles(PROFILES_FILE, profiles)


def normalize_profile(p):
    """Soporta profiles viejos con 'sensitivity' única."""
    p = p or {}
    merged = DEFAULT_PROFILE.copy()
    merged.update(p or {})

    if "sens_x" not in p and "sensitivity" in p:
        merged["sens_x"] = p.get("sensitivity", "media")
    if "sens_y" not in p and "sensitivity" in p:
        merged["sens_y"] = p.get("sensitivity", "media")

    merged["sens_x"] = LEGACY_SENS_MAP.get(merged["sens_x"], merged["sens_x"])
    merged["sens_y"] = LEGACY_SENS_MAP.get(merged["sens_y"], merged["sens_y"])

    if merged["sens_x"] not in SENS_LEVELS:
        merged["sens_x"] = DEFAULT_PROFILE["sens_x"]
    if merged["sens_y"] not in SENS_LEVELS:
        merged["sens_y"] = DEFAULT_PROFILE["sens_y"]

    if merged.get("wink_diff_sens") not in WINK_DIFF_LEVELS:
        merged["wink_diff_sens"] = DEFAULT_PROFILE["wink_diff_sens"]

    if merged.get("face_point") not in FACE_POINTS:
        merged["face_point"] = "Punta de nariz"
    for key, (low, high, default) in RANGES.items():
        if key == "gain_x":
            default = GAIN_X_BY_LEVEL[merged["sens_x"]]
        elif key == "gain_y":
            default = GAIN_Y_BY_LEVEL[merged["sens_y"]]
        try:
            value = float(merged.get(key, default))
            merged[key] = value if math.isfinite(value) and low <= value <= high else default
        except (ValueError, TypeError):
            merged[key] = default
    return merged


def list_camera_names():
    if FilterGraph is None:
        return []
    try:
        graph = FilterGraph()
        devices = graph.get_input_devices()
        return devices if devices else []
    except Exception as e:
        print(f"[WARN] No se pudieron listar cámaras por nombre: {e}")
        return []


def get_camera_options():
    cam_names = list_camera_names()
    if not cam_names:
        cam_names = ["Cam 0", "Cam 1", "Cam 2"]
    cam_map = {name: idx for idx, name in enumerate(cam_names)}
    return cam_names, cam_map


def show_gui_menu(master=None, on_saved=None, persist_profiles=None):
    window = tk.Toplevel(master) if master is not None else tk.Tk()
    profiles = load_profiles()
    if not profiles:
        profiles = {"Default": DEFAULT_PROFILE.copy()}
    initial = ACTIVE_PROFILE if master is not None and ACTIVE_PROFILE in profiles else list(profiles.keys())[0]
    selected_profile = tk.StringVar(value=initial)
    profile_name_var = tk.StringVar(value=selected_profile.get())
    mouth_action_var = tk.StringVar(value="Click izquierdo")
    wink_left_action_var = tk.StringVar(value="Nada")
    wink_right_action_var = tk.StringVar(value="Nada")
    brow_raise_var = tk.StringVar(value="Nada")
    brow_frown_var = tk.StringVar(value="Nada")
    sens_x_var = tk.StringVar(value=DEFAULT_PROFILE["sens_x"])
    sens_y_var = tk.StringVar(value=DEFAULT_PROFILE["sens_y"])
    stabilize_var = tk.BooleanVar(value=True)
    zoom_var = tk.BooleanVar(value=False)
    dwell_time_var = tk.StringVar(value="2.0")
    wink_diff_sens_var = tk.StringVar(value=DEFAULT_PROFILE["wink_diff_sens"])
    tracking_mode_var = tk.StringVar(value="Punta de nariz")
    gain_x_var = tk.StringVar()
    gain_y_var = tk.StringVar()
    sound_var = tk.BooleanVar(value=True)
    dwell_enabled_var = tk.BooleanVar(value=False)
    cam_names, cam_map = get_camera_options()
    cam_index_var = tk.StringVar(value=cam_names[0] if cam_names else "Cam 0")
    selected_config = {}
    ui = PagedMenu(window)
    profile = ui.card("Tu perfil")
    profile_combo = field(profile, "Perfil guardado", selected_profile, list(profiles.keys()))
    field(profile, "Nombre para guardar / nuevo perfil", profile_name_var)
    hint(profile, "Tus ajustes se guardan al comenzar el control.")
    camera = ui.card("Cámara y seguimiento")
    camera_control = field(camera, "Cámara", cam_index_var, cam_names)
    hint(camera, "Elegí la cámara y pulsá Guardar y aplicar para cambiarla.")
    field(camera, "Punto facial que mueve el cursor", tracking_mode_var, list(FACE_POINTS))
    hint(camera, "El punto se detecta automáticamente. La vista de cámara permanece oculta.")
    gestures = ui.card("Acciones por gesto")
    field(gestures, "Boca", mouth_action_var, AVAILABLE_ACTIONS)
    field(gestures, "Guiño izquierdo", wink_left_action_var, AVAILABLE_ACTIONS)
    field(gestures, "Guiño derecho", wink_right_action_var, AVAILABLE_ACTIONS)
    brows = ui.card("Cejas · gestos experimentales")
    field(brows, "Levantar las cejas", brow_raise_var, AVAILABLE_ACTIONS)
    field(brows, "Fruncir el ceño", brow_frown_var, AVAILABLE_ACTIONS)
    hint(brows, "Al comenzar, mantené el rostro relajado unos segundos para calibrar. Nada desactiva el gesto.")
    motion = ui.card("Movimiento del cursor")
    field(motion, "Sensibilidad horizontal · Eje X", sens_x_var, SENS_LEVELS)
    field(motion, "Sensibilidad vertical · Eje Y", sens_y_var, SENS_LEVELS)
    fine = ui.card("Ajuste fino y estabilidad")
    numeric(fine, "Ajuste fino horizontal · X", gain_x_var, "gain_x")
    numeric(fine, "Ajuste fino vertical · Y", gain_y_var, "gain_y")
    sens_x_var.trace_add("write", lambda *args: gain_x_var.set(GAIN_X_BY_LEVEL.get(sens_x_var.get(), 62)))
    sens_y_var.trace_add("write", lambda *args: gain_y_var.set(GAIN_Y_BY_LEVEL.get(sens_y_var.get(), 52)))
    toggle(fine, "Suavizado del punto óptico", stabilize_var)
    wink = ui.card("Precisión del guiño")
    field(wink, "Sensibilidad del guiño", wink_diff_sens_var, WINK_DIFF_LEVELS)
    hint(wink, "Más sensible detecta un cierre menor. Más estricto exige cerrar más el ojo y reduce falsos positivos.")
    aids = ui.card("Ayudas de acceso")
    field(aids, "Tiempo de autoclick · segundos", dwell_time_var, ["0.5", "1.0", "1.5", "2.0", "2.5", "3.0"])
    toggle(aids, "Zoom automático de Windows", zoom_var)
    toggle(aids, "Sonido de las acciones", sound_var)
    toggle(aids, "Autoclick al comenzar", dwell_enabled_var)
    hint(aids, "F8 activa o desactiva el autoclick durante el uso.")
    def apply_profile(profile_name):
        p = normalize_profile(profiles.get(profile_name, DEFAULT_PROFILE))
        profile_name_var.set(profile_name)

        mouth_action_var.set(p.get("mouth", "Click izquierdo"))
        wink_left_action_var.set(p.get("wink_left", "Nada"))
        wink_right_action_var.set(p.get("wink_right", "Nada"))
        brow_raise_var.set(p.get("brow_raise", "Nada"))
        brow_frown_var.set(p.get("brow_frown", "Nada"))
        sens_x_var.set(p.get("sens_x", DEFAULT_PROFILE["sens_x"]))
        sens_y_var.set(p.get("sens_y", DEFAULT_PROFILE["sens_y"]))
        stabilize_var.set(bool(p.get("stabilize", True)))
        zoom_var.set(bool(p.get("zoom", False)))
        dwell_time_var.set(str(p.get("dwell_time", 2.0)))
        wink_diff_sens_var.set(p.get("wink_diff_sens", DEFAULT_PROFILE["wink_diff_sens"]))
        tracking_mode_var.set(p["face_point"])
        gain_x_var.set(p["gain_x"])
        gain_y_var.set(p["gain_y"])
        sound_var.set(p.get("sound_enabled", True))
        dwell_enabled_var.set(p.get("dwell_enabled", False))

        cam_idx = CAMERA_INDEX if master is not None else int(p.get("camera", 0))
        for name, idx in cam_map.items():
            if idx == cam_idx:
                cam_index_var.set(name)
                break

    def on_profile_selected(_event=None):
        apply_profile(selected_profile.get())

    def start():
        name = profile_name_var.get().strip() or "Default"

        p = {
            **normalize_profile(profiles.get(selected_profile.get(), DEFAULT_PROFILE)),
            "mouth": mouth_action_var.get(),
            "wink_left": wink_left_action_var.get(),
            "wink_right": wink_right_action_var.get(),
            "brow_raise": brow_raise_var.get(),
            "brow_frown": brow_frown_var.get(),
            "startup_default": True,
            "setup_complete": True,
            "camera": cam_map[cam_index_var.get()],
            "sens_x": sens_x_var.get(),
            "sens_y": sens_y_var.get(),
            "sensitivity": sens_x_var.get(),  # compatibilidad
            "stabilize": bool(stabilize_var.get()),
            "zoom": bool(zoom_var.get()),
            "dwell_time": float(dwell_time_var.get()),
            "wink_diff_sens": wink_diff_sens_var.get(),
            "tracking_mode": "Punto facial",
            "face_point": tracking_mode_var.get(),
            "gain_x": gain_x_var.get(),
            "gain_y": gain_y_var.get(),
            "sound_enabled": bool(sound_var.get()),
            "dwell_enabled": bool(dwell_enabled_var.get()),
        }

        try:
            p = validated(p)
            name = profile_save_name({k:normalize_profile(v) for k,v in profiles.items()}, name, p)
            updated = {key: {**value, "startup_default": False} for key,value in profiles.items()}
            updated[name] = p
            if persist_profiles is None:
                save_profiles(updated)
            else:
                persist_profiles(updated, p)
        except (ValueError, OSError) as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=window)
            return
        profiles[name] = p

        selected_config.update(p)
        selected_config["_profile_name"] = name
        selected_config["_show_guide"] = master is None
        if master is None:
            window.quit()
        window.destroy()
        if on_saved is not None:
            on_saved(selected_config)

    profile_combo.bind("<<ComboboxSelected>>", on_profile_selected)
    apply_profile(selected_profile.get())
    ui.finish(start, "F11: pausa / continuar · F12: salir · Esc / F10: liberar entradas\nF7: centrar · R: recuperar punto · K: recalibrar guiño\nF9: teclado · B: accesos rápidos · M: mostrar / ocultar cámara\nF1/F2: sensibilidad Y · F3/F4: sensibilidad X · F5/F6: sensibilidad del guiño", editing=master is not None)
    chrome = WindowChrome(window, window.destroy, "MouthClick · Elegir perfil")
    chrome.maximize()
    if master is not None:
        return window
    window.mainloop()

    if not selected_config:
        raise SystemExit(0)  # Closing setup must not start cursor control.

    return selected_config



def startup_config():
    profiles = load_profiles()
    if "--config" not in sys.argv:
        preferred = next((name for name,p in profiles.items() if p.get("startup_default")), None)
        preferred = preferred or next((name for name in profiles if name == "Por Defecto"), None)
        preferred = preferred or next((name for name in profiles if name.casefold() == "octavio"), None)
        if preferred is not None and profiles[preferred].get("setup_complete", False):
            return {**normalize_profile(profiles[preferred]), "_profile_name": preferred}
    return show_gui_menu()


CONFIG = startup_config()

GESTURE_ACTIONS = {
    "mouth": CONFIG["mouth"],
    "wink_left": CONFIG["wink_left"],
    "wink_right": CONFIG["wink_right"],
    "brow_raise": CONFIG.get("brow_raise", "Nada"),
    "brow_frown": CONFIG.get("brow_frown", "Nada"),
}

CAMERA_INDEX = int(CONFIG["camera"])
SENS_X = CONFIG.get("sens_x", CONFIG.get("sensitivity", "media"))
SENS_Y = CONFIG.get("sens_y", CONFIG.get("sensitivity", "media"))
STABILIZE = bool(CONFIG.get("stabilize", True))
AUTO_ZOOM_ENABLED = bool(CONFIG.get("zoom", False))
DWELL_CLICK_SEC = float(CONFIG.get("dwell_time", 2.0))
WINK_DIFF_SENS = CONFIG.get("wink_diff_sens", DEFAULT_PROFILE["wink_diff_sens"])

REL_GAIN_X = CONFIG["gain_x"]
REL_GAIN_Y = CONFIG["gain_y"]
WINK_DIFF_THR = WINK_DIFF_THR_BY_LEVEL.get(WINK_DIFF_SENS, WINK_DIFF_THR_BY_LEVEL[DEFAULT_PROFILE["wink_diff_sens"]])
WINK_CLOSED_RATIO_THR = WINK_CLOSED_RATIO_BY_LEVEL.get(WINK_DIFF_SENS, WINK_CLOSED_RATIO_BY_LEVEL[DEFAULT_PROFILE["wink_diff_sens"]])

CURRENT_SENS_X_INDEX = gain_index(REL_GAIN_X, list(GAIN_X_BY_LEVEL.values()))
CURRENT_SENS_Y_INDEX = gain_index(REL_GAIN_Y, list(GAIN_Y_BY_LEVEL.values()))
CUSTOM_SENS_X_STEPS = 0
CUSTOM_SENS_Y_STEPS = 0
CURRENT_WINK_DIFF_INDEX = WINK_DIFF_LEVELS.index(WINK_DIFF_SENS) if WINK_DIFF_SENS in WINK_DIFF_LEVELS else 2

print("Acciones:", GESTURE_ACTIONS)
print("Cam:", CAMERA_INDEX)
print("Sens X:", SENS_X, "->", REL_GAIN_X)
print("Sens Y:", SENS_Y, "->", REL_GAIN_Y)
print("Stabilize:", STABILIZE)
print("DwellTime:", DWELL_CLICK_SEC)
print("Wink diff:", WINK_DIFF_SENS, "->", WINK_DIFF_THR)
print("Wink closed ratio:", WINK_DIFF_SENS, "->", WINK_CLOSED_RATIO_THR)


# =========================================
# ========== CONFIG MOVIMIENTO ============
# =========================================

SCREEN_W, SCREEN_H = pyautogui.size()
SAFE_MARGIN = 8

RUNNING = True
PAUSED = False
DWELL_ENABLED = bool(CONFIG.get("dwell_enabled", False))

SHOW_OVERLAY = False
CAMERA_VISIBLE = False
FACE_POINT = CONFIG["face_point"]
SOUND_ENABLED = bool(CONFIG.get("sound_enabled", True))
ACTIVE_PROFILE = CONFIG["_profile_name"]
live_settings_window = None
ui_commands = queue.Queue(maxsize=64)


def queue_hotkey(key):
    if key not in tuple(getattr(keyboard.Key,f"f{i}") for i in range(1,13))+(keyboard.Key.esc,) and getattr(key,"char","") not in ("r","R","k","K"):
        return
    try:
        ui_commands.put_nowait(key)
    except queue.Full:
        try:
            ui_commands.get_nowait()
        except queue.Empty:
            pass
        try:
            ui_commands.put_nowait(key)
        except queue.Full:
            pass
action_audio = None
WINDOW_NAME = "Face Mouse"
WINDOW_FULLSCREEN = False
FLOATING_KEYBOARD_VISIBLE = False
floating_keyboard_root = None
floating_keyboard_buffer_var = None
floating_keyboard_shift = False
floating_keyboard_hwnd = None
floating_keyboard_target_hwnd = None
floating_keyboard_last_press = {}
floating_keyboard_move_mode = False
floating_keyboard_move_pending = False
floating_keyboard_move_started_at = 0.0
KEYBOARD_BUTTON_DEBOUNCE_SEC = 0.45
floating_actions_root = None
FLOATING_ACTIONS_VISIBLE = True
floating_actions_pos = None
floating_actions_collapse_after = 0.0
KEYBOARD_SIZE_LEVELS = ["compacto", "normal", "grande"]
keyboard_size_index = 0

# Optical Flow
SELECTING_POINT = True
tracking_point = None          # np.array [[[x,y]]]
prev_gray = None
current_gray_frame = None
last_good_point = None
smooth_x = None
smooth_y = None
selected_anchor_offset = None
last_face_anchor = None

# Movimiento
SMOOTHING = CONFIG["smoothing"]
POINT_SMOOTH_ALPHA = SMOOTHING if STABILIZE else 1.0  # alto = más responsivo
DEADZONE_PX_CAMERA = CONFIG["deadzone"]                         # zona muerta en pixels de cámara
MAX_MOUSE_STEP = 140                              # límite por frame en pantalla
PRECISION_CAM_PX = 1.8                            # movimientos chicos entran en modo precisión
PRECISION_MIN_SCALE = 0.35
FACE_ANCHOR_SMOOTH_ALPHA = 0.35
FACE_ANCHOR_CORRECTION_ALPHA = 0.35
FACE_ANCHOR_CORRECTION_START_PX = 2.5
FACE_ANCHOR_CORRECTION_MAX_STEP = 5.0
FREEZE_ON_GESTURE_SEC = 0.12
FREEZE_ON_LEFT_CLICK_SEC = 0.06
ACTION_DEBOUNCE_SEC = 0.65
suspend_move_until = 0.0
last_action_time_by_name = {}

cur_x, cur_y = pyautogui.position()
cursor_speed = 0.0
prev_cursor_pos = pyautogui.position()
prev_speed_time = time.time()

# Gestos boca / guiños
SLOW_START_RATIO = 0.035
CLICK_ARM_RATIO = CONFIG["mouth_threshold"]
CLICK_SHORT_SEC = 0.15
CLICK_COOLDOWN_SEC = 0.40
DBLCLICK_INTERVAL_SEC = 0.12

mouth_open_prev = False
mouth_open_start = None
mouth_click_armed = False
last_click_time = 0.0

LEFT_EYE_IDX = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]
last_wink_time = 0.0
WINK_COOLDOWN = 0.45

last_left_ear = 0.0
last_right_ear = 0.0
last_eye_diff = 0.0
smooth_left_ear = None
smooth_right_ear = None
smooth_eye_diff = 0.0
left_open_baseline = None
right_open_baseline = None
left_eye_open_norm = 1.0
right_eye_open_norm = 1.0
wink_calibration_samples = []
wink_calibrated = False
left_ear_vis = 0.0
right_ear_vis = 0.0
EAR_SMOOTH_ALPHA = 0.45
EAR_VIS_ALPHA = 0.25
WINK_CONFIRM_FRAMES = 3
FACE_PROCESS_EVERY_N = 1
WINK_CALIBRATION_FRAMES = 60
WINK_BASELINE_ADAPT_ALPHA = 0.01
WINK_OTHER_EYE_OPEN_MARGIN = 0.22
WINK_BASELINE_MAX_ASYMMETRY = 0.22
WINK_MIN_BASELINE_EAR = 0.16
WINK_BAD_READING_FRAMES_LIMIT = 15
wink_candidate = None
wink_candidate_frames = 0
wink_bad_reading_frames = 0
wink_warning_text = ""
wink_warning_until = 0.0
wink_label = ""
wink_label_until = 0.0

mouth_ratio_vis = 0.0
mouth_open_now = False

drag_active = False

# Dwell
DWELL_STILL_RADIUS_PX = CONFIG["dwell_radius"]
DWELL_POST_CLICK_DELAY = 1.0
last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()
dwell_progress = 0.0

# Zoom
zoom_active = False
last_zoom_toggle_time = 0.0
zoom_on_since = 0.0
ZOOM_TOGGLE_COOLDOWN = 0.8
ZOOM_MIN_ON_SEC = 1.5

VK_LWIN = 0x5B
VK_ESCAPE = 0x1B
VK_ADD_NUMPAD = 0x6B
KEYEVENTF_KEYUP = 0x0002


lk_params = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.03)
)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def clamp_with_margin(v, lo, hi, m=SAFE_MARGIN):
    return max(lo + m, min(hi - m, v))


def precision_scale_from_camera_delta(dx_cam, dy_cam):
    cam_dist = math.hypot(dx_cam, dy_cam)
    if cam_dist <= DEADZONE_PX_CAMERA:
        return 0.0
    scale = PRECISION_MIN_SCALE + (1.0 - PRECISION_MIN_SCALE) * clamp(cam_dist / PRECISION_CAM_PX, 0.0, 1.0)
    return scale


def face_anchor_px(lm, frame_w, frame_h):
    return point_pixels(lm, FACE_POINT, frame_w, frame_h)


def smooth_face_anchor(anchor):
    global last_face_anchor
    if last_face_anchor is None:
        last_face_anchor = anchor
    else:
        ax = (1 - FACE_ANCHOR_SMOOTH_ALPHA) * last_face_anchor[0] + FACE_ANCHOR_SMOOTH_ALPHA * anchor[0]
        ay = (1 - FACE_ANCHOR_SMOOTH_ALPHA) * last_face_anchor[1] + FACE_ANCHOR_SMOOTH_ALPHA * anchor[1]
        last_face_anchor = (ax, ay)
    return last_face_anchor


def apply_face_anchor_correction(anchor):
    global tracking_point, smooth_x, smooth_y, selected_anchor_offset, last_good_point
    if SELECTING_POINT or tracking_point is None or smooth_x is None or smooth_y is None:
        return

    if selected_anchor_offset is None:
        selected_anchor_offset = (smooth_x - anchor[0], smooth_y - anchor[1])
        return

    expected_x = anchor[0] + selected_anchor_offset[0]
    expected_y = anchor[1] + selected_anchor_offset[1]
    drift_x = expected_x - smooth_x
    drift_y = expected_y - smooth_y
    drift = math.hypot(drift_x, drift_y)

    if drift < FACE_ANCHOR_CORRECTION_START_PX:
        return

    step = min(FACE_ANCHOR_CORRECTION_MAX_STEP, drift * FACE_ANCHOR_CORRECTION_ALPHA)
    k = step / drift
    smooth_x += drift_x * k
    smooth_y += drift_y * k
    tracking_point = np.array([[[np.float32(smooth_x), np.float32(smooth_y)]]], dtype=np.float32)
    last_good_point = (smooth_x, smooth_y)


def draw_text_with_shadow(frame, text, org, scale, color, thickness=2):
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 3)
    cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def draw_control_cross(frame, x, y):
    x = int(x)
    y = int(y)
    cv2.circle(frame, (x, y), 6, (0, 255, 0), -1)


def draw_metric_bar(frame, label, value, max_value, x, y, w, h, color, threshold=None):
    value = clamp(value, 0.0, max_value)
    fill_w = int((value / max_value) * w) if max_value > 0 else 0
    cv2.rectangle(frame, (x, y), (x + w, y + h), (55, 55, 55), 2)
    cv2.rectangle(frame, (x, y), (x + fill_w, y + h), color, -1)
    if threshold is not None:
        tx = x + int((clamp(threshold, 0.0, max_value) / max_value) * w)
        cv2.line(frame, (tx, y - 5), (tx, y + h + 5), (0, 0, 255), 2)
    draw_text_with_shadow(frame, f"{label}: {value:.3f}", (x, y - 8), 0.5, (255, 255, 255), 1)


def draw_wink_debug(frame, left_norm, right_norm, eye_diff):
    h, w = frame.shape[:2]
    bar_w = min(260, max(160, w // 3))
    x = 16
    y = max(95, h - 135)
    open_thr = min(0.95, WINK_CLOSED_RATIO_THR + WINK_OTHER_EYE_OPEN_MARGIN)
    draw_metric_bar(frame, "Izq norm", left_norm, 1.2, x, y, bar_w, 18, (80, 210, 255), WINK_CLOSED_RATIO_THR)
    draw_metric_bar(frame, "Der norm", right_norm, 1.2, x, y + 42, bar_w, 18, (120, 255, 120), WINK_CLOSED_RATIO_THR)
    draw_metric_bar(frame, "eye_diff", eye_diff, 0.16, x, y + 84, bar_w, 18, (0, 190, 255), WINK_DIFF_THR)
    calib_text = "OK" if wink_calibrated else f"{len(wink_calibration_samples)}/{WINK_CALIBRATION_FRAMES}"
    draw_text_with_shadow(frame, f"cierra < {WINK_CLOSED_RATIO_THR:.2f} | otro > {open_thr:.2f}", (x + bar_w + 14, y + 100), 0.48, (255, 255, 255), 1)
    draw_text_with_shadow(frame, f"calib: {calib_text} confirm: {wink_candidate_frames}/{WINK_CONFIRM_FRAMES}", (x + bar_w + 14, y + 122), 0.48, (255, 255, 255), 1)


def setup_camera_window():
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)
    try:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        cam_w, cam_h = 960, 720
        screen_w, screen_h = pyautogui.size()
        cv2.resizeWindow(WINDOW_NAME, cam_w, cam_h)
        cv2.moveWindow(WINDOW_NAME, max(0, (screen_w - cam_w) // 2), max(0, (screen_h - cam_h) // 2 - 80))
    except Exception as e:
        print("[WARN] No se pudo ajustar tamaño de ventana:", e)


def toggle_camera_window():
    global CAMERA_VISIBLE
    CAMERA_VISIBLE = not CAMERA_VISIBLE
    if CAMERA_VISIBLE:
        setup_camera_window()
    else:
        cv2.destroyWindow(WINDOW_NAME)


def hotkey_zoom_open():
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_ADD_NUMPAD, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_ADD_NUMPAD, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)


def hotkey_zoom_close():
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)


def zoom_in_windows():
    global zoom_active, last_zoom_toggle_time, zoom_on_since
    now = time.time()
    if zoom_active or (now - last_zoom_toggle_time < ZOOM_TOGGLE_COOLDOWN):
        return
    try:
        hotkey_zoom_open()
        zoom_active = True
        zoom_on_since = now
        last_zoom_toggle_time = now
        print("[ZOOM] ON")
    except Exception as e:
        print("[ZOOM] No se pudo activar:", e)


def zoom_out_windows():
    global zoom_active, last_zoom_toggle_time
    now = time.time()
    if not zoom_active or (now - last_zoom_toggle_time < ZOOM_TOGGLE_COOLDOWN):
        return
    if (now - zoom_on_since) < ZOOM_MIN_ON_SEC:
        return
    try:
        hotkey_zoom_close()
        zoom_active = False
        last_zoom_toggle_time = now
        print("[ZOOM] OFF")
    except Exception as e:
        print("[ZOOM] No se pudo desactivar:", e)


def do_click():
    global suspend_move_until, floating_keyboard_move_mode
    if floating_keyboard_move_mode:
        floating_keyboard_move_mode = False
        print("[KEYBOARD MOVE] Posición fijada")
        return
    x, y = pyautogui.position()
    suspend_move_until = time.time() + FREEZE_ON_LEFT_CLICK_SEC
    pyautogui.click(x=x, y=y, button="left")
    play_action_sound("Click izquierdo")


def do_right_click():
    global suspend_move_until
    if PAUSED:
        return
    x, y = pyautogui.position()
    suspend_move_until = time.time() + FREEZE_ON_GESTURE_SEC
    pyautogui.click(x=x, y=y, button="right")
    play_action_sound("Click derecho")


def do_double_click():
    global suspend_move_until
    x, y = pyautogui.position()
    suspend_move_until = time.time() + FREEZE_ON_GESTURE_SEC
    pyautogui.click(x=x, y=y)
    time.sleep(DBLCLICK_INTERVAL_SEC)
    pyautogui.click(x=x, y=y)
    play_action_sound("Doble click")


def start_drag():
    global drag_active, suspend_move_until
    if not drag_active:
        suspend_move_until = 0.0
        pyautogui.mouseDown(button="left")
        drag_active = True
        play_action_sound("Drag toggle")
        print("[DRAG] START")


def stop_drag():
    global drag_active, suspend_move_until
    if drag_active:
        pyautogui.mouseUp(button="left")
        drag_active = False
        play_action_sound("Drag toggle")
        suspend_move_until = 0.0
        print("[DRAG] STOP")


def release_all_inputs(close_context_menu=True):
    global drag_active, suspend_move_until
    try:
        pyautogui.mouseUp(button="left")
        # A synthetic right-button release can itself open a Windows context menu.
        if ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000:
            pyautogui.mouseUp(button="right")
    except Exception:
        pass
    drag_active = False
    suspend_move_until = 0.0
    if close_context_menu:
        try:
            pyautogui.press("esc")
        except Exception:
            pass
    print("[RESCUE] Inputs liberados")


def action_debounced(action_name):
    now = time.time()
    last = last_action_time_by_name.get(action_name, 0.0)
    if now - last < ACTION_DEBOUNCE_SEC:
        print(f"[ACTION] Ignorada repetida: {action_name}")
        return True
    last_action_time_by_name[action_name] = now
    return False


ACTION_SOUNDS = {
    "Click izquierdo": [(880, 90)],
    "Doble click": [(880, 70), (1040, 70)],
    "Click derecho": [(520, 120)],
    "Drag toggle": [(700, 80), (420, 90)],
}


def play_action_sound(action_name):
    if SOUND_ENABLED and action_audio is not None:
        action_audio.play(action_name)


drag_mode = False
office_mode = False


def pointer_over_controls():
    x, y = pyautogui.position()
    for window in (floating_actions_root, floating_keyboard_root, live_settings_window, confirmation_window, main_menu_window, alignment_window):
        if window is not None and window.winfo_exists() and window.winfo_viewable():
            if window.winfo_rootx() <= x < window.winfo_rootx()+window.winfo_width() and window.winfo_rooty() <= y < window.winfo_rooty()+window.winfo_height():
                return True
    return False


def update_mode_buttons():
    if floating_actions_root is not None:
        floating_actions_root.set_modes(drag_mode, office_mode)


def toggle_drag_mode():
    global drag_mode, office_mode
    stop_drag()
    drag_mode = not drag_mode
    office_mode = False
    update_mode_buttons()


def toggle_office_mode():
    global drag_mode, office_mode
    stop_drag()
    office_mode = not office_mode
    drag_mode = False
    update_mode_buttons()


def execute_gesture(gesture):
    if PAUSED or not RUNNING:
        return
    action = GESTURE_ACTIONS.get(gesture, "Nada")
    if floating_actions_root is not None and floating_actions_root.moving and (action != "Nada" or office_mode):
        floating_actions_root.stop_moving()
        return
    if pointer_over_controls() and (action != "Nada" or office_mode):
        execute_action("Click izquierdo")
    elif office_mode:
        if action_debounced("office:"+gesture):
            return
        if gesture in ("wink_left", "wink_right"):
            stop_drag()
            pyautogui.hotkey("ctrl", "c" if gesture == "wink_left" else "v")
            play_action_sound("Click izquierdo")
        elif gesture == "mouth":
            do_click()
    else:
        execute_action(action)


def execute_action(action_name):
    if action_name == "Nada":
        return
    if action_debounced(action_name):
        return
    if pointer_over_controls():
        stop_drag()
        do_click()
        return
    if action_name == "Click izquierdo":
        if drag_mode:
            stop_drag() if drag_active else start_drag()
        else:
            do_click()
    elif action_name == "Doble click":
        do_double_click()
    elif action_name == "Click derecho":
        do_right_click()
    elif action_name == "Drag toggle":
        if drag_active:
            stop_drag()
        else:
            start_drag()


def centered_geometry(width, height, y_bias=0):
    screen_w, screen_h = pyautogui.size()
    x = max(0, int((screen_w - width) / 2))
    y = max(0, int((screen_h - height) / 2 + y_bias))
    return f"{width}x{height}+{x}+{y}"


def geometry_at_pos(width, height, pos=None, y_bias=0):
    if pos is None:
        return centered_geometry(width, height, y_bias=y_bias)
    return f"{width}x{height}+{int(pos[0])}+{int(pos[1])}"


def make_window_no_activate(root, remember_as_keyboard=True):
    global floating_keyboard_hwnd
    try:
        root.update_idletasks()
        hwnd = int(root.winfo_id())
        if remember_as_keyboard:
            floating_keyboard_hwnd = hwnd
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOPMOST = 0x00000008
        WS_EX_TOOLWINDOW = 0x00000080
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
        root.attributes("-topmost", True)
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo hacer no-activate:", e)


def window_title(hwnd):
    try:
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def is_own_or_helper_window(hwnd):
    if not hwnd:
        return True
    if floating_keyboard_hwnd and hwnd == floating_keyboard_hwnd:
        return True
    title = window_title(hwnd).lower()
    return (
        "mouthclick teclado" in title
        or "mouthclick keyboard" in title
        or "mouthclick acciones" in title
        or "mouthclick ajustes" in title
        or WINDOW_NAME.lower() in title
    )


def remember_keyboard_target():
    global floating_keyboard_target_hwnd
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd and not is_own_or_helper_window(hwnd):
            floating_keyboard_target_hwnd = hwnd
    except Exception:
        pass


def focus_keyboard_target():
    if not floating_keyboard_target_hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        target_thread = user32.GetWindowThreadProcessId(floating_keyboard_target_hwnd, None)
        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = False
        if target_thread and target_thread != current_thread:
            attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))

        user32.ShowWindow(floating_keyboard_target_hwnd, 5)  # SW_SHOW
        user32.BringWindowToTop(floating_keyboard_target_hwnd)
        user32.SetForegroundWindow(floating_keyboard_target_hwnd)
        user32.SetFocus(floating_keyboard_target_hwnd)

        if attached:
            user32.AttachThreadInput(current_thread, target_thread, False)
        time.sleep(0.06)
        return True
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo enfocar destino:", e)
        return False


def keyboard_debounced(action_id):
    now = time.time()
    last = floating_keyboard_last_press.get(action_id, 0.0)
    if now - last < KEYBOARD_BUTTON_DEBOUNCE_SEC:
        print(f"[KEYBOARD] Ignorado repetido: {action_id}")
        return True
    floating_keyboard_last_press[action_id] = now
    return False


def keyboard_buffer_append(text):
    if floating_keyboard_buffer_var is None:
        return
    current = floating_keyboard_buffer_var.get()
    if text == "\b":
        floating_keyboard_buffer_var.set(current[:-1])
    elif text == "\n":
        floating_keyboard_buffer_var.set("")
    else:
        floating_keyboard_buffer_var.set((current + text)[-80:])


def keyboard_send_text(text):
    if not text:
        return
    try:
        focus_keyboard_target()
        if len(text) == 1 and ord(text) < 128:
            pyautogui.write(text, interval=0)
        elif floating_keyboard_root is not None:
            floating_keyboard_root.clipboard_clear()
            floating_keyboard_root.clipboard_append(text)
            floating_keyboard_root.update_idletasks()
            pyautogui.hotkey("ctrl", "v")
        else:
            pyautogui.write(text, interval=0)
        keyboard_buffer_append(text)
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo escribir texto:", e)


def keyboard_send_key(key_name):
    try:
        global floating_keyboard_move_mode
        if floating_keyboard_move_mode and key_name in ("enter", "esc", "space"):
            floating_keyboard_move_mode = False
            print("[KEYBOARD MOVE] Posición fijada")
            return
        if key_name == "esc":
            release_all_inputs(close_context_menu=False)
        focus_keyboard_target()
        pyautogui.press(key_name)
        if key_name == "backspace":
            keyboard_buffer_append("\b")
        elif key_name == "enter":
            keyboard_buffer_append("\n")
        elif key_name == "space":
            keyboard_buffer_append(" ")
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo enviar tecla:", e)


def keyboard_hotkey(*keys):
    try:
        focus_keyboard_target()
        pyautogui.hotkey(*keys)
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo enviar atajo:", e)


def keyboard_button_press(value):
    global floating_keyboard_shift
    if keyboard_debounced(f"key:{value}"):
        return
    if value == "Shift":
        floating_keyboard_shift = not floating_keyboard_shift
        return
    if value == "Space":
        keyboard_send_key("space")
        return
    if value == "Back":
        keyboard_send_key("backspace")
        return
    if value == "Enter":
        keyboard_send_key("enter")
        return
    if value == "Tab":
        keyboard_send_key("tab")
        return
    if value == "Esc":
        keyboard_send_key("esc")
        return

    text = value.upper() if floating_keyboard_shift else value.lower()
    keyboard_send_text(text)
    if floating_keyboard_shift:
        floating_keyboard_shift = False


def keyboard_quick_phrase(text):
    if keyboard_debounced(f"phrase:{text}"):
        return
    keyboard_send_text(text)


def keyboard_style():
    level = KEYBOARD_SIZE_LEVELS[keyboard_size_index]
    if level == "grande":
        return {"w": 1060, "h": 340, "font": 11, "title_font": 10, "preview": 11, "btn_h": 1, "row_pady": 2, "pad": 5}
    if level == "normal":
        return {"w": 1000, "h": 305, "font": 10, "title_font": 9, "preview": 10, "btn_h": 1, "row_pady": 1, "pad": 4}
    return {"w": 940, "h": 285, "font": 10, "title_font": 9, "preview": 10, "btn_h": 1, "row_pady": 1, "pad": 3}


def resize_floating_keyboard(delta):
    global keyboard_size_index, floating_keyboard_root, floating_actions_root, live_settings_window
    keyboard_size_index = clamp(keyboard_size_index + delta, 0, len(KEYBOARD_SIZE_LEVELS) - 1)
    if floating_keyboard_root is None:
        return
    try:
        was_visible = FLOATING_KEYBOARD_VISIBLE
        actions_was_visible = FLOATING_ACTIONS_VISIBLE
        if live_settings_window is not None and live_settings_window.winfo_exists():
            live_settings_window.discard()
        live_settings_window = None
        floating_keyboard_root.destroy()
        floating_keyboard_root = None
        floating_actions_root = None
        create_floating_keyboard()
        create_quick_actions_bubble()
        if not was_visible and floating_keyboard_root is not None:
            floating_keyboard_root.withdraw()
        if not actions_was_visible and floating_actions_root is not None:
            floating_actions_root.withdraw()
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo cambiar tamaño:", e)


def toggle_keyboard_move_mode():
    global floating_keyboard_move_mode, floating_keyboard_move_pending, floating_keyboard_move_started_at
    floating_keyboard_move_mode = not floating_keyboard_move_mode
    floating_keyboard_move_pending = False
    floating_keyboard_move_started_at = time.time()
    print(f"[KEYBOARD MOVE] {'ON' if floating_keyboard_move_mode else 'OFF'}")


def update_keyboard_move_mode():
    global floating_keyboard_move_mode
    if not floating_keyboard_move_mode or floating_keyboard_root is None:
        return
    try:
        x, y = pyautogui.position()
        floating_keyboard_root.geometry(f"+{max(0, x - 80)}+{max(0, y - 24)}")
        if time.time() - floating_keyboard_move_started_at > 0.35:
            left_down = ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000
            right_down = ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000
            if left_down or right_down:
                floating_keyboard_move_mode = False
                release_all_inputs(close_context_menu=False)
                print("[KEYBOARD MOVE] Posición fijada")
    except Exception:
        pass


def toggle_floating_keyboard():
    global FLOATING_KEYBOARD_VISIBLE
    FLOATING_KEYBOARD_VISIBLE = not FLOATING_KEYBOARD_VISIBLE
    if floating_keyboard_root is None:
        return
    if FLOATING_KEYBOARD_VISIBLE:
        floating_keyboard_root.deiconify()
    else:
        floating_keyboard_root.withdraw()
    print(f"[KEYBOARD] {'ON' if FLOATING_KEYBOARD_VISIBLE else 'OFF'}")


def toggle_floating_actions():
    global FLOATING_ACTIONS_VISIBLE
    FLOATING_ACTIONS_VISIBLE = True
    if floating_actions_root is None:
        return
    floating_actions_root.deiconify()
    floating_actions_root.attributes("-topmost", True)
    floating_actions_root.lift()
    floating_actions_root.expand()



def create_quick_actions_bubble():
    global floating_actions_root, floating_actions_pos, floating_actions_collapse_after
    if floating_keyboard_root is None:
        return None
    try:
        items = [
            ("Drag", lambda: None if keyboard_debounced("bubble:drag") else toggle_drag_mode()),
            ("Oficina", toggle_office_mode),
            ("Teclado", toggle_floating_keyboard),
            ("Sensibilidades", open_live_settings),
            ("Menú principal", open_main_menu),
            ("Posición cámara", open_alignment_guide),
            ("Calib", reset_wink_calibration),
            ("Centro", center_mouse),
            ("Pausa", lambda: confirm_control("pause")),
            ("Salir", lambda: confirm_control("exit")),
        ]
        def remember_pos(x, y):
            global floating_actions_pos
            floating_actions_pos = (x, y)

        def schedule_collapse():
            global floating_actions_collapse_after
            floating_actions_collapse_after = time.time() + 0.9

        def cancel_collapse():
            global floating_actions_collapse_after
            floating_actions_collapse_after = 0.0

        root = ActionsBubble(floating_keyboard_root, items, floating_actions_pos,
                             remember_pos, schedule_collapse, cancel_collapse)
        root.set_paused(PAUSED)
        root.set_modes(drag_mode, office_mode)
        root.protocol("WM_DELETE_WINDOW", toggle_floating_actions)
        make_window_no_activate(root, remember_as_keyboard=False)
        floating_actions_root = root
        if not FLOATING_ACTIONS_VISIBLE:
            root.withdraw()
        return root
    except Exception as e:
        print("[ACTIONS WARN] No se pudo crear burbuja:", e)
        return None



def create_floating_keyboard():
    global floating_keyboard_root, floating_keyboard_buffer_var
    try:
        style = keyboard_style()
        root = tk.Tk()
        if not FLOATING_KEYBOARD_VISIBLE:
            root.withdraw()
        root.title("MouthClick Teclado")
        root.geometry(centered_geometry(style["w"], style["h"], y_bias=220))
        root.resizable(True, True)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#111827")
        root.protocol("WM_DELETE_WINDOW", toggle_floating_keyboard)

        floating_keyboard_buffer_var = tk.StringVar(value="")

        topbar = tk.Frame(root, bg="#0f172a")
        topbar.pack(fill="x")
        tk.Label(
            topbar,
            text="Teclado",
            fg="#e5e7eb",
            bg="#0f172a",
            font=("Arial", style["title_font"], "bold")
        ).pack(side="left", padx=8, pady=2)
        tk.Button(topbar, text="Acciones", command=toggle_floating_actions, width=8).pack(side="right", padx=3, pady=1)
        tk.Button(topbar, text="Mover", command=toggle_keyboard_move_mode, width=7).pack(side="right", padx=3, pady=1)
        tk.Button(topbar, text="+", command=lambda: resize_floating_keyboard(1), width=3).pack(side="right", padx=3, pady=2)
        tk.Button(topbar, text="-", command=lambda: resize_floating_keyboard(-1), width=3).pack(side="right", padx=3, pady=2)
        tk.Button(topbar, text="Ocultar", command=toggle_floating_keyboard, width=8).pack(side="right", padx=4, pady=2)

        preview = tk.Entry(
            root,
            textvariable=floating_keyboard_buffer_var,
            font=("Arial", style["preview"]),
            bg="#020617",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat"
        )
        preview.pack(fill="x", padx=style["pad"], pady=(style["pad"], 2), ipady=2)

        quick = tk.Frame(root, bg="#111827")
        quick.pack(fill="x", padx=style["pad"], pady=style["row_pady"])
        quick_items = [
            ("Si", "Sí"),
            ("No", "No"),
            ("Hola", "Hola "),
            ("Gracias", "Gracias "),
            ("Ayuda", "Necesito ayuda "),
            ("Borrar", None),
            ("Enter", "enter"),
        ]
        for label, text in quick_items:
            if label == "Borrar":
                cmd = lambda: None if keyboard_debounced("quick:backspace") else keyboard_send_key("backspace")
            elif text == "enter":
                cmd = lambda: None if keyboard_debounced("quick:enter") else keyboard_send_key("enter")
            else:
                cmd = lambda t=text: keyboard_quick_phrase(t)
            tk.Button(quick, text=label, command=cmd, height=style["btn_h"]).pack(side="left", padx=2, fill="x", expand=True)

        rows = [
            list("1234567890"),
            list("QWERTYUIOP"),
            list("ASDFGHJKLÑ"),
            list("ZXCVBNM"),
        ]

        for row in rows:
            row_frame = tk.Frame(root, bg="#111827")
            row_frame.pack(fill="x", padx=style["pad"], pady=style["row_pady"])
            for key_label in row:
                tk.Button(
                    row_frame,
                    text=key_label,
                    command=lambda v=key_label: keyboard_button_press(v),
                    font=("Arial", style["font"], "bold"),
                    height=style["btn_h"],
                    width=4
                ).pack(side="left", padx=2, fill="x", expand=True)

        bottom = tk.Frame(root, bg="#111827")
        bottom.pack(fill="x", padx=style["pad"], pady=style["row_pady"])
        bottom_keys = [
            ("Shift", "Shift"),
            ("Tab", "Tab"),
            ("Espacio", "Space"),
            ("Back", "Back"),
            ("Enter", "Enter"),
            ("Esc", "Esc"),
        ]
        for label, value in bottom_keys:
            width = 16 if value == "Space" else 7
            tk.Button(
                bottom,
                text=label,
                command=lambda v=value: keyboard_button_press(v),
                height=style["btn_h"],
                width=width
            ).pack(side="left", padx=2, fill="x", expand=(value == "Space"))

        actions = tk.Frame(root, bg="#111827")
        actions.pack_forget()
        action_buttons = [
            ("Ctrl+C", lambda: None if keyboard_debounced("act:copy") else keyboard_hotkey("ctrl", "c")),
            ("Ctrl+V", lambda: None if keyboard_debounced("act:paste") else keyboard_hotkey("ctrl", "v")),
            ("Ctrl+A", lambda: None if keyboard_debounced("act:all") else keyboard_hotkey("ctrl", "a")),
            ("Esc", lambda: None if keyboard_debounced("act:esc") else release_all_inputs(close_context_menu=True)),
            ("Click", lambda: None if keyboard_debounced("act:click") else do_click()),
            ("Doble", lambda: None if keyboard_debounced("act:double") else do_double_click()),
            ("Derecho", lambda: None if keyboard_debounced("act:right") else do_right_click()),
            ("Drag", lambda: None if keyboard_debounced("act:drag") else (stop_drag() if drag_active else start_drag())),
            ("Centro", lambda: None if keyboard_debounced("act:center") else center_mouse()),
        ]
        for label, cmd in action_buttons:
            tk.Button(actions, text=label, command=cmd, height=style["btn_h"]).pack(side="left", padx=2, fill="x", expand=True)

        style_floating(root)
        root.update_idletasks()
        root.geometry(centered_geometry(min(root.winfo_screenwidth()-20, max(style["w"], root.winfo_reqwidth())),
                                        min(root.winfo_screenheight()-60, max(style["h"], root.winfo_reqheight())), y_bias=100))
        make_window_no_activate(root)
        floating_keyboard_root = root
        if not FLOATING_KEYBOARD_VISIBLE:
            root.withdraw()
        return root
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo crear teclado flotante:", e)
        return None


last_bubble_check = 0.0


def update_floating_keyboard():
    try:
        global floating_actions_collapse_after, last_bubble_check
        remember_keyboard_target()
        if floating_keyboard_root is not None:
            update_keyboard_move_mode()
            floating_keyboard_root.update()
        if floating_actions_root is not None:
            if time.monotonic()-last_bubble_check >= 0.5:
                last_bubble_check = time.monotonic()
                if floating_actions_root.state() != "normal":
                    floating_actions_root.deiconify()
                floating_actions_root.attributes("-topmost", True)
                floating_actions_root.lift()
            if floating_actions_collapse_after and time.time() >= floating_actions_collapse_after:
                try:
                    floating_actions_root.collapse_now()
                except Exception:
                    pass
                floating_actions_collapse_after = 0.0
    except tk.TclError:
        pass


def center_mouse():
    global cur_x, cur_y, last_cursor_pos, last_move_time
    cur_x = SCREEN_W // 2
    cur_y = SCREEN_H // 2
    pyautogui.moveTo(cur_x, cur_y)
    last_cursor_pos = pyautogui.position()
    last_move_time = time.time()
    print("[HOTKEY] Mouse centrado")


def reset_tracking():
    global SELECTING_POINT, tracking_point, prev_gray, last_good_point, smooth_x, smooth_y
    global selected_anchor_offset, last_face_anchor
    global mouth_open_prev, mouth_open_start, mouth_click_armed, wink_candidate, wink_candidate_frames
    global last_move_time, dwell_progress
    mouth_open_prev, mouth_open_start, mouth_click_armed = False, None, False
    wink_candidate, wink_candidate_frames = None, 0
    last_move_time, dwell_progress = time.time(), 0.0
    SELECTING_POINT = True
    tracking_point = None
    prev_gray = None
    last_good_point = None
    smooth_x = None
    smooth_y = None
    selected_anchor_offset = None
    last_face_anchor = None
    print("[TRACK] Buscando punto facial:", FACE_POINT)


def reset_wink_calibration():
    global brow_detector
    brow_detector = None
    global left_open_baseline, right_open_baseline, wink_calibrated, wink_calibration_samples
    global smooth_left_ear, smooth_right_ear, smooth_eye_diff
    global left_eye_open_norm, right_eye_open_norm, wink_candidate, wink_candidate_frames
    global wink_bad_reading_frames, wink_warning_text, wink_warning_until
    left_open_baseline = None
    right_open_baseline = None
    wink_calibrated = False
    wink_calibration_samples = []
    smooth_left_ear = None
    smooth_right_ear = None
    smooth_eye_diff = 0.0
    left_eye_open_norm = 1.0
    right_eye_open_norm = 1.0
    wink_candidate = None
    wink_candidate_frames = 0
    wink_bad_reading_frames = 0
    wink_warning_text = "RECALIBRANDO OJOS: MANTENELOS ABIERTOS"
    wink_warning_until = time.time() + 2.5
    print("[WINK CAL] Recalibrando: mantené ambos ojos abiertos")


def mouth_open_ratio(lm):
    p_up = lm[13]
    p_dn = lm[14]
    p_top = lm[10]
    p_bot = lm[152]
    dy_mouth = np.hypot(p_up.x - p_dn.x, p_up.y - p_dn.y)
    dy_face = np.hypot(p_top.x - p_bot.x, p_top.y - p_bot.y)
    return dy_mouth / dy_face if dy_face > 1e-6 else 0.0


def eye_aspect_ratio(lm, idxs):
    p = [lm[i] for i in idxs]
    v1 = np.hypot(p[1].x - p[5].x, p[1].y - p[5].y)
    v2 = np.hypot(p[2].x - p[4].x, p[2].y - p[4].y)
    h = np.hypot(p[0].x - p[3].x, p[0].y - p[3].y)
    return (v1 + v2) / (2 * h) if h > 1e-6 else 0.0


def update_wink_baseline(left, right):
    global left_open_baseline, right_open_baseline, wink_calibrated, wink_calibration_samples
    global wink_warning_text, wink_warning_until

    if left <= 0.01 or right <= 0.01:
        return False

    if not wink_calibrated:
        wink_calibration_samples.append((left, right))
        if len(wink_calibration_samples) >= WINK_CALIBRATION_FRAMES:
            arr = np.array(wink_calibration_samples, dtype=np.float32)
            left_base = float(np.percentile(arr[:, 0], 75))
            right_base = float(np.percentile(arr[:, 1], 75))
            avg_base = (left_base + right_base) * 0.5
            asym = abs(left_base - right_base) / max(avg_base, 1e-6)

            if avg_base < WINK_MIN_BASELINE_EAR or asym > WINK_BASELINE_MAX_ASYMMETRY:
                wink_calibration_samples = []
                wink_warning_text = "NO PUDE CALIBRAR OJOS: MAS LUZ / MIRAR DE FRENTE"
                wink_warning_until = time.time() + 3.0
                print(f"[WINK CAL WARN] mala calibracion L={left_base:.3f} R={right_base:.3f} asym={asym:.2f}")
                return False

            left_open_baseline = left_base
            right_open_baseline = right_base
            wink_calibrated = True
            wink_calibration_samples = []
            wink_warning_text = ""
            wink_warning_until = 0.0
            print(f"[WINK CAL] baseline L={left_open_baseline:.3f} R={right_open_baseline:.3f}")
        return wink_calibrated

    return True


def adapt_open_eye_baseline(left, right, left_norm, right_norm):
    global left_open_baseline, right_open_baseline
    if left_open_baseline is None or right_open_baseline is None:
        return
    if left_norm > 0.88 and right_norm > 0.88:
        left_open_baseline = (1 - WINK_BASELINE_ADAPT_ALPHA) * left_open_baseline + WINK_BASELINE_ADAPT_ALPHA * left
        right_open_baseline = (1 - WINK_BASELINE_ADAPT_ALPHA) * right_open_baseline + WINK_BASELINE_ADAPT_ALPHA * right


brow_detector = None


def detect_gesture(lm, ratio_raw, now):
    global brow_detector
    primary = detect_primary_gesture(lm, ratio_raw, now)
    if all(GESTURE_ACTIONS.get(key, "Nada") == "Nada" for key in ("brow_raise", "brow_frown")):
        return primary
    if brow_detector is None:
        brow_detector = BrowGestures()
    def distance(a,b):
        return math.hypot(lm[a].x-lm[b].x,lm[a].y-lm[b].y)
    width = max(distance(33,263), 1e-6)
    height = (distance(105,159)+distance(334,386))/(2*width)
    gap = distance(107,336)/width
    brow = brow_detector.update(height,gap,now, primary is None and ratio_raw < SLOW_START_RATIO and left_eye_open_norm > .85 and right_eye_open_norm > .85)
    return primary or brow


def detect_primary_gesture(lm, ratio_raw, now):
    global mouth_open_prev, mouth_open_start, mouth_click_armed
    global last_click_time, last_wink_time
    global last_left_ear, last_right_ear, last_eye_diff
    global smooth_left_ear, smooth_right_ear, smooth_eye_diff
    global left_eye_open_norm, right_eye_open_norm
    global wink_candidate, wink_candidate_frames
    global wink_bad_reading_frames, wink_warning_text, wink_warning_until

    # Boca: arma al abrir bastante y dispara al cerrar
    opened = ratio_raw >= SLOW_START_RATIO

    if opened and not mouth_open_prev:
        mouth_open_start = now

    if (not opened) and mouth_open_prev and (mouth_open_start is not None):
        dur = now - mouth_open_start

        if mouth_click_armed and (now - last_click_time >= CLICK_COOLDOWN_SEC):
            if dur >= CLICK_SHORT_SEC:
                last_click_time = now
                mouth_open_start = None
                mouth_click_armed = False
                mouth_open_prev = opened
                return "mouth"

        mouth_open_start = None
        mouth_click_armed = False

    if ratio_raw >= CLICK_ARM_RATIO:
        mouth_click_armed = True

    mouth_open_prev = opened

    # Guiño por diferencia entre ojos
    left = eye_aspect_ratio(lm, LEFT_EYE_IDX)
    right = eye_aspect_ratio(lm, RIGHT_EYE_IDX)

    if smooth_left_ear is None or smooth_right_ear is None:
        smooth_left_ear = left
        smooth_right_ear = right
    else:
        smooth_left_ear = (1 - EAR_SMOOTH_ALPHA) * smooth_left_ear + EAR_SMOOTH_ALPHA * left
        smooth_right_ear = (1 - EAR_SMOOTH_ALPHA) * smooth_right_ear + EAR_SMOOTH_ALPHA * right

    last_left_ear = smooth_left_ear
    last_right_ear = smooth_right_ear

    raw_eye_diff = abs(left - right)
    eye_diff = abs(smooth_left_ear - smooth_right_ear)
    smooth_eye_diff = (1 - EAR_SMOOTH_ALPHA) * smooth_eye_diff + EAR_SMOOTH_ALPHA * eye_diff
    last_eye_diff = smooth_eye_diff

    if not update_wink_baseline(smooth_left_ear, smooth_right_ear):
        wink_candidate = None
        wink_candidate_frames = 0
        return None

    if left_open_baseline is None or right_open_baseline is None:
        return None

    left_eye_open_norm = clamp(smooth_left_ear / max(left_open_baseline, 1e-6), 0.0, 1.2)
    right_eye_open_norm = clamp(smooth_right_ear / max(right_open_baseline, 1e-6), 0.0, 1.2)
    adapt_open_eye_baseline(smooth_left_ear, smooth_right_ear, left_eye_open_norm, right_eye_open_norm)

    other_eye_open_thr = min(0.95, WINK_CLOSED_RATIO_THR + WINK_OTHER_EYE_OPEN_MARGIN)
    one_eye_looks_closed = (
        left_eye_open_norm < WINK_CLOSED_RATIO_THR
        or right_eye_open_norm < WINK_CLOSED_RATIO_THR
    )

    if one_eye_looks_closed and not (mouth_open_now or wink_candidate_frames > 0):
        wink_bad_reading_frames += 1
    else:
        wink_bad_reading_frames = max(0, wink_bad_reading_frames - 1)

    if wink_bad_reading_frames >= WINK_BAD_READING_FRAMES_LIMIT:
        wink_warning_text = "LECTURA DE OJOS INESTABLE: PRESIONA K / MAS LUZ"
        wink_warning_until = now + 3.0
        wink_candidate = None
        wink_candidate_frames = 0
        return None

    current_candidate = None
    if left_eye_open_norm < WINK_CLOSED_RATIO_THR and right_eye_open_norm > other_eye_open_thr:
        current_candidate = "wink_left"
    elif right_eye_open_norm < WINK_CLOSED_RATIO_THR and left_eye_open_norm > other_eye_open_thr:
        current_candidate = "wink_right"

    if current_candidate is None:
        wink_candidate = None
        wink_candidate_frames = 0
        return None

    if current_candidate == wink_candidate:
        wink_candidate_frames += 1
    else:
        wink_candidate = current_candidate
        wink_candidate_frames = 1

    if wink_candidate_frames >= WINK_CONFIRM_FRAMES:
        if (now - last_wink_time) > WINK_COOLDOWN:
            last_wink_time = now
            wink_candidate_frames = 0
            print(
                f"[WINK] L={smooth_left_ear:.3f}/{left_eye_open_norm:.2f} "
                f"R={smooth_right_ear:.3f}/{right_eye_open_norm:.2f} "
                f"diff={smooth_eye_diff:.3f} raw_diff={raw_eye_diff:.3f}"
            )
            return wink_candidate

    return None


def open_camera(index):
    # DSHOW suele dar menor latencia y no se cuelga tanto en Windows
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[WARN] DSHOW falló, probando DEFAULT")
        cap.release()
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir cámara {index}")
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print(f"[INFO] Cámara abierta en índice {index}")
    return cap


def on_mouse(event, x, y, flags, param):
    global SELECTING_POINT, tracking_point, prev_gray, last_good_point, smooth_x, smooth_y
    global selected_anchor_offset, cur_x, cur_y, prev_cursor_pos, prev_speed_time, last_move_time
    if event == cv2.EVENT_LBUTTONDOWN:
        if not SELECTING_POINT:
            return
        tracking_point = np.array([[[np.float32(x), np.float32(y)]]], dtype=np.float32)
        last_good_point = (float(x), float(y))
        smooth_x = float(x)
        smooth_y = float(y)
        if last_face_anchor is not None:
            selected_anchor_offset = (smooth_x - last_face_anchor[0], smooth_y - last_face_anchor[1])
        else:
            selected_anchor_offset = None
        if current_gray_frame is not None:
            prev_gray = current_gray_frame.copy()
        cur_x, cur_y = pyautogui.position()
        prev_cursor_pos = (cur_x, cur_y)
        prev_speed_time = time.time()
        last_move_time = prev_speed_time
        SELECTING_POINT = False
        print(f"[TRACK] Punto seleccionado: x={x}, y={y}")


confirmation_window = None


def confirm_control(action):
    global confirmation_window
    if confirmation_window is not None and confirmation_window.winfo_exists():
        confirmation_window.lift()
        return
    if action == "pause" and PAUSED:
        toggle_pause()
        return
    title = "¿Pausar el control facial?" if action == "pause" else "¿Cerrar MouthClick?"
    explanation = ("Para continuar necesitarás F11 o un dispositivo físico para pulsar Continuar."
                   if action == "pause" else
                   "Para volver a usar el control facial necesitarás abrir la app con ayuda o un dispositivo físico. Guardá tus ajustes antes de salir.")
    confirmation_window = ConfirmAction(floating_keyboard_root, title, explanation,
                                        toggle_pause if action == "pause" else request_exit)


def toggle_pause():
    global PAUSED
    release_all_inputs(close_context_menu=False)
    if floating_actions_root is not None:
        floating_actions_root.stop_moving()
    PAUSED = not PAUSED
    if PAUSED:
        dismiss_paused_menu()
        if floating_keyboard_root is not None:
            floating_keyboard_root.after(200, dismiss_paused_menu)
    reset_tracking()
    if floating_actions_root is not None:
        floating_actions_root.set_paused(PAUSED)


def dismiss_paused_menu():
    if not PAUSED:
        return
    release_all_inputs(close_context_menu=False)
    try:
        user32 = ctypes.windll.user32
        user32.PostMessageW(user32.GetForegroundWindow(), 0x001F, 0, 0)  # WM_CANCELMODE
    except Exception:
        pass
    pyautogui.press("esc")


def request_exit():
    global RUNNING
    release_all_inputs(close_context_menu=False)
    RUNNING = False


def process_hotkeys(limit=64):
    # A large input queue must not starve Tk updates or camera processing.
    for _ in range(limit):
        try:
            key = ui_commands.get_nowait()
        except queue.Empty:
            break
        on_press(key)
        if not RUNNING:
            break


def on_press(key):
    global RUNNING, PAUSED, DWELL_ENABLED
    global CURRENT_SENS_X_INDEX, CURRENT_SENS_Y_INDEX, REL_GAIN_X, REL_GAIN_Y
    global CUSTOM_SENS_X_STEPS, CUSTOM_SENS_Y_STEPS
    global CURRENT_WINK_DIFF_INDEX, WINK_DIFF_THR, WINK_CLOSED_RATIO_THR
    global dwell_progress

    try:
        if key == keyboard.Key.f12:
            print("[HOTKEY] F12 -> salir")
            confirm_control("exit")

        elif key == keyboard.Key.f11:
            confirm_control("pause")

        elif key == keyboard.Key.f8:
            release_all_inputs(close_context_menu=True)
            DWELL_ENABLED = not DWELL_ENABLED
            dwell_progress = 0.0
            print(f"[HOTKEY] F8 -> autoclick {'ON' if DWELL_ENABLED else 'OFF'}")

        elif key == keyboard.Key.f9:
            toggle_floating_keyboard()

        elif key == keyboard.Key.f7:
            center_mouse()

        elif key == keyboard.Key.f10:
            release_all_inputs(close_context_menu=True)

        elif key == keyboard.Key.esc:
            # Escape has already reached the target application. Never emit it again.
            release_all_inputs(close_context_menu=False)

        elif key in (keyboard.Key.f3, keyboard.Key.f4):
            direction = 1 if key == keyboard.Key.f4 else -1
            REL_GAIN_X = step_gain(REL_GAIN_X, list(GAIN_X_BY_LEVEL.values()), direction, 8.0)
            CURRENT_SENS_X_INDEX = gain_index(REL_GAIN_X, list(GAIN_X_BY_LEVEL.values()))
            CUSTOM_SENS_X_STEPS = max(0, (REL_GAIN_X-GAIN_X_BY_LEVEL[SENS_LEVELS[-1]])/8.0)

        elif key in (keyboard.Key.f1, keyboard.Key.f2):
            direction = 1 if key == keyboard.Key.f2 else -1
            REL_GAIN_Y = step_gain(REL_GAIN_Y, list(GAIN_Y_BY_LEVEL.values()), direction, 7.0)
            CURRENT_SENS_Y_INDEX = gain_index(REL_GAIN_Y, list(GAIN_Y_BY_LEVEL.values()))
            CUSTOM_SENS_Y_STEPS = max(0, (REL_GAIN_Y-GAIN_Y_BY_LEVEL[SENS_LEVELS[-1]])/7.0)

        elif key == keyboard.Key.f5:
            CURRENT_WINK_DIFF_INDEX = max(0, CURRENT_WINK_DIFF_INDEX - 1)
            level = WINK_DIFF_LEVELS[CURRENT_WINK_DIFF_INDEX]
            WINK_DIFF_THR = WINK_DIFF_THR_BY_LEVEL[level]
            WINK_CLOSED_RATIO_THR = WINK_CLOSED_RATIO_BY_LEVEL[level]
            print(f"[WINK SENS] {level} -> cerrado<{WINK_CLOSED_RATIO_THR:.2f}")

        elif key == keyboard.Key.f6:
            CURRENT_WINK_DIFF_INDEX = min(len(WINK_DIFF_LEVELS) - 1, CURRENT_WINK_DIFF_INDEX + 1)
            level = WINK_DIFF_LEVELS[CURRENT_WINK_DIFF_INDEX]
            WINK_DIFF_THR = WINK_DIFF_THR_BY_LEVEL[level]
            WINK_CLOSED_RATIO_THR = WINK_CLOSED_RATIO_BY_LEVEL[level]
            print(f"[WINK SENS] {level} -> cerrado<{WINK_CLOSED_RATIO_THR:.2f}")

        else:
            try:
                if key.char and key.char.lower() == "r":
                    reset_tracking()
                elif key.char and key.char.lower() == "k":
                    reset_wink_calibration()
            except Exception:
                pass

        if live_settings_window is not None and live_settings_window.winfo_exists():
            live_settings_window.sync(runtime_snapshot())
    except Exception as e:
        print("[HOTKEY WARN]", e)


def update_optical_tracking(gray, now):
    global smooth_x, smooth_y, cur_x, cur_y, prev_cursor_pos, prev_speed_time
    global cursor_speed, tracking_point, last_good_point, SELECTING_POINT, prev_gray
    if tracking_point is not None and prev_gray is not None:
        next_point, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, gray, tracking_point, None, **lk_params)
        if next_point is not None and status is not None and (status[0][0] == 1):
            old_x, old_y = tracking_point[0][0]
            new_x, new_y = next_point[0][0]
            if smooth_x is None:
                smooth_x, smooth_y = (float(new_x), float(new_y))
            else:
                smooth_x = (1 - POINT_SMOOTH_ALPHA) * smooth_x + POINT_SMOOTH_ALPHA * float(new_x)
                smooth_y = (1 - POINT_SMOOTH_ALPHA) * smooth_y + POINT_SMOOTH_ALPHA * float(new_y)
            dx_cam = smooth_x - float(old_x)
            dy_cam = smooth_y - float(old_y)
            precision_scale = precision_scale_from_camera_delta(dx_cam, dy_cam)
            # Subtract the noise floor smoothly instead of jumping at its edge.
            magnitude = math.hypot(dx_cam,dy_cam)
            noise_scale = max(0.0,1.0-DEADZONE_PX_CAMERA/magnitude) if magnitude else 0.0
            dx_cam *= noise_scale
            dy_cam *= noise_scale
            dx_mouse = dx_cam * REL_GAIN_X * precision_scale
            dy_mouse = dy_cam * REL_GAIN_Y * precision_scale
            dist = math.hypot(dx_mouse, dy_mouse)
            if dist > MAX_MOUSE_STEP:
                k = MAX_MOUSE_STEP / dist
                dx_mouse *= k
                dy_mouse *= k
            if now >= suspend_move_until:
                if dx_mouse != 0.0 or dy_mouse != 0.0:
                    cur_x, cur_y = pyautogui.position()
                    tx = round(clamp_with_margin(cur_x + dx_mouse, 0, SCREEN_W - 1))
                    ty = round(clamp_with_margin(cur_y + dy_mouse, 0, SCREEN_H - 1))
                    if (tx,ty) != (cur_x,cur_y):
                        pyautogui.moveTo(tx, ty)
                    now_pos = pyautogui.position()
                    dt = max(1e-06, time.time() - prev_speed_time)
                    cursor_speed = math.hypot(now_pos[0] - prev_cursor_pos[0], now_pos[1] - prev_cursor_pos[1]) / dt
                    prev_cursor_pos = now_pos
                    prev_speed_time = time.time()
            tracking_point = np.array([[[np.float32(smooth_x), np.float32(smooth_y)]]], dtype=np.float32)
            last_good_point = (smooth_x, smooth_y)
        elif last_face_anchor is not None and selected_anchor_offset is not None:
            recover_x = clamp(last_face_anchor[0] + selected_anchor_offset[0], 0, gray.shape[1] - 1)
            recover_y = clamp(last_face_anchor[1] + selected_anchor_offset[1], 0, gray.shape[0] - 1)
            smooth_x = float(recover_x)
            smooth_y = float(recover_y)
            tracking_point = np.array([[[np.float32(smooth_x), np.float32(smooth_y)]]], dtype=np.float32)
            last_good_point = (smooth_x, smooth_y)
        else:
            SELECTING_POINT = True
            tracking_point = None
        prev_gray = gray


def runtime_snapshot():
    return {
        "face_point": FACE_POINT, "gain_x": REL_GAIN_X, "gain_y": REL_GAIN_Y,
        "sens_x": SENS_LEVELS[CURRENT_SENS_X_INDEX], "sens_y": SENS_LEVELS[CURRENT_SENS_Y_INDEX],
        "wink_diff_sens": WINK_DIFF_LEVELS[CURRENT_WINK_DIFF_INDEX],
        "mouth_threshold": CLICK_ARM_RATIO, "dwell_time": DWELL_CLICK_SEC,
        "dwell_radius": DWELL_STILL_RADIUS_PX, "dwell_enabled": DWELL_ENABLED,
        "deadzone": DEADZONE_PX_CAMERA, "stabilize": STABILIZE, "smoothing": SMOOTHING,
        "zoom": AUTO_ZOOM_ENABLED, "sound_enabled": SOUND_ENABLED,
        "_custom_x": CUSTOM_SENS_X_STEPS, "_custom_y": CUSTOM_SENS_Y_STEPS,
    }


def apply_runtime_settings(values):
    global FACE_POINT, REL_GAIN_X, REL_GAIN_Y, STABILIZE, SMOOTHING, POINT_SMOOTH_ALPHA
    global DEADZONE_PX_CAMERA, DWELL_CLICK_SEC, DWELL_STILL_RADIUS_PX, DWELL_ENABLED
    global CURRENT_SENS_X_INDEX, CURRENT_SENS_Y_INDEX, CUSTOM_SENS_X_STEPS, CUSTOM_SENS_Y_STEPS
    global CURRENT_WINK_DIFF_INDEX, WINK_CLOSED_RATIO_THR, WINK_DIFF_THR, CLICK_ARM_RATIO
    global AUTO_ZOOM_ENABLED, SOUND_ENABLED, last_move_time, dwell_progress
    global wink_candidate, wink_candidate_frames, mouth_open_prev, mouth_open_start, mouth_click_armed
    values = validated(values)
    if values["wink_diff_sens"] != WINK_DIFF_LEVELS[CURRENT_WINK_DIFF_INDEX]:
        wink_candidate, wink_candidate_frames = None, 0
    if values["mouth_threshold"] != CLICK_ARM_RATIO:
        mouth_open_prev, mouth_open_start, mouth_click_armed = False, None, False
    point_changed = values["face_point"] != FACE_POINT
    dwell_changed = any(values[k] != runtime_snapshot()[k] for k in ("dwell_enabled", "dwell_time", "dwell_radius"))
    FACE_POINT = values["face_point"]
    REL_GAIN_X, REL_GAIN_Y = values["gain_x"], values["gain_y"]
    CURRENT_SENS_X_INDEX = gain_index(REL_GAIN_X, list(GAIN_X_BY_LEVEL.values()))
    CURRENT_SENS_Y_INDEX = gain_index(REL_GAIN_Y, list(GAIN_Y_BY_LEVEL.values()))
    CUSTOM_SENS_X_STEPS = values.get("_custom_x", 0)
    CUSTOM_SENS_Y_STEPS = values.get("_custom_y", 0)
    STABILIZE, SMOOTHING = bool(values["stabilize"]), values["smoothing"]
    POINT_SMOOTH_ALPHA = SMOOTHING if STABILIZE else 1.0
    DEADZONE_PX_CAMERA = values["deadzone"]
    DWELL_CLICK_SEC, DWELL_STILL_RADIUS_PX = values["dwell_time"], values["dwell_radius"]
    DWELL_ENABLED = bool(values["dwell_enabled"])
    CURRENT_WINK_DIFF_INDEX = WINK_DIFF_LEVELS.index(values["wink_diff_sens"])
    WINK_CLOSED_RATIO_THR = WINK_CLOSED_RATIO_BY_LEVEL[values["wink_diff_sens"]]
    WINK_DIFF_THR = WINK_DIFF_THR_BY_LEVEL[values["wink_diff_sens"]]
    CLICK_ARM_RATIO = values["mouth_threshold"]
    AUTO_ZOOM_ENABLED, SOUND_ENABLED = bool(values["zoom"]), bool(values["sound_enabled"])
    if not AUTO_ZOOM_ENABLED and zoom_active:
        zoom_out_windows()
    if dwell_changed:
        last_move_time, dwell_progress = time.time(), 0.0
    if point_changed:
        stop_drag()
        reset_tracking()


def save_runtime_settings(values):
    global ACTIVE_PROFILE
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, encoding="utf-8") as f:
            profiles = json.load(f)
        if not isinstance(profiles, dict):
            raise ValueError("El archivo de perfiles no es válido.")
    else:
        profiles = {}
    settings = {k: v for k, v in validated(values).items() if not k.startswith("_")}
    profile = {**CONFIG, **profiles.get(ACTIVE_PROFILE, {}), **settings}
    profile = {k:v for k,v in profile.items() if not k.startswith("_")}
    profile["sens_x"] = SENS_LEVELS[CURRENT_SENS_X_INDEX]
    profile["sens_y"] = SENS_LEVELS[CURRENT_SENS_Y_INDEX]
    profile["sensitivity"] = profile["sens_x"]
    profile["tracking_mode"] = "Punto facial"
    new_name = profile_save_name({k:normalize_profile(v) for k,v in profiles.items()}, ACTIVE_PROFILE, profile)
    if new_name != ACTIVE_PROFILE:
        profiles = {k:{**v,"startup_default":False} for k,v in profiles.items()}
        profile["startup_default"] = True
    profiles[new_name] = profile
    save_profiles(profiles)
    ACTIVE_PROFILE = new_name
    CONFIG.update(profile)
    CONFIG["_profile_name"] = new_name


main_menu_window = None
alignment_window = None


def open_alignment_guide():
    global alignment_window
    if alignment_window is not None and alignment_window.winfo_exists():
        alignment_window.deiconify()
        alignment_window.lift()
    else:
        alignment_window = AlignmentGuide(floating_keyboard_root, reset_wink_calibration)


def update_alignment_guide(frame, landmarks):
    if alignment_window is not None and alignment_window.winfo_exists():
        alignment_window.update_frame(frame,landmarks)


def save_menu_profiles(profiles, config):
    """Validate the new device before persisting or releasing the working camera."""
    global cap, CAMERA_INDEX, last_preview_frame, current_gray_frame
    index = int(config["camera"])
    candidate = None
    try:
        if index != CAMERA_INDEX:
            raw = open_camera(index)
            if raw is None:
                raise ValueError("No se pudo abrir esa cámara. La cámara anterior sigue activa.")
            candidate = LatestFrameCapture(raw)
            deadline = time.monotonic() + 4.0
            ready = False
            while time.monotonic() < deadline:
                ok, frame = candidate.read()
                if ok and frame is not None and frame.size:
                    ready = True
                    break
            if not ready:
                raise ValueError("Esa cámara no entrega imagen. La cámara anterior sigue activa.")
        save_profiles(profiles)
    except Exception:
        if candidate is not None:
            candidate.release()
        raise
    if candidate is not None:
        stop_drag()
        previous = cap
        cap = candidate
        CAMERA_INDEX = index
        last_preview_frame = current_gray_frame = None
        reset_tracking()
        reset_wink_calibration()
        previous.release()


def apply_menu_profile(config):
    global ACTIVE_PROFILE, CONFIG, drag_mode, office_mode
    stop_drag()
    drag_mode = office_mode = False
    update_mode_buttons()
    CONFIG = dict(config)
    ACTIVE_PROFILE = config["_profile_name"]
    GESTURE_ACTIONS.update({key:config.get(key,"Nada") for key in GESTURE_ACTIONS})
    apply_runtime_settings(config)
    reset_wink_calibration()


def open_main_menu():
    global main_menu_window
    if main_menu_window is not None and main_menu_window.winfo_exists():
        main_menu_window.deiconify()
        main_menu_window.lift()
        return
    if live_settings_window is not None and live_settings_window.winfo_exists():
        live_settings_window.lift()
        live_settings_window.message.configure(text="Guardá o cerrá estos ajustes antes de abrir Menú principal.")
        return
    main_menu_window = show_gui_menu(floating_keyboard_root, apply_menu_profile, save_menu_profiles)


def open_live_settings():
    global live_settings_window
    if main_menu_window is not None and main_menu_window.winfo_exists():
        main_menu_window.deiconify()
        main_menu_window.lift()
        return
    if live_settings_window is not None and live_settings_window.winfo_exists():
        live_settings_window.lift()
        return
    live_settings_window = LiveSettings(
        floating_keyboard_root, ACTIVE_PROFILE, runtime_snapshot(), apply_runtime_settings,
        save_runtime_settings, lambda: action_audio.play("Click izquierdo"), lambda: action_audio.error)


# =========================================
# ========== INICIALIZACIÓN ===============
# =========================================

cap = open_camera(CAMERA_INDEX)
if cap is None:
    raise SystemExit("No se pudo iniciar la cámara.")
cap = LatestFrameCapture(cap)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.4,
    min_tracking_confidence=0.4
)

action_audio = ActionAudio()
create_floating_keyboard()
create_quick_actions_bubble()
if CONFIG.get("_show_guide"):
    open_alignment_guide()

hotkey_listener = keyboard.Listener(on_press=queue_hotkey)
hotkey_listener.start()

print("[TRACK] Selección automática:", FACE_POINT)

frame_count = 0
last_debug_print = 0.0

def report_status(text):
    if floating_actions_root is not None:
        floating_actions_root.set_status(text)
    if live_settings_window is not None and live_settings_window.winfo_exists() and action_audio.error:
        live_settings_window.message.configure(text=action_audio.error, fg="#FFD078")


def present_camera(frame, status):
    global CAMERA_VISIBLE
    if not CAMERA_VISIBLE:
        return
    try:
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            CAMERA_VISIBLE = False
            return
        preview = frame.copy()
        if smooth_x is not None and smooth_y is not None:
            draw_control_cross(preview, smooth_x, smooth_y)
        draw_status(preview, status, "warning" if SELECTING_POINT or PAUSED else "success")
        cv2.imshow(WINDOW_NAME, preview)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            toggle_camera_window()
    except cv2.error:
        CAMERA_VISIBLE = False


try:
    while RUNNING:
        process_hotkeys()
        update_floating_keyboard()
        if not RUNNING:
            break
        if PAUSED:
            report_status("PAUSADO · F11 para continuar")
            if last_preview_frame is not None:
                present_camera(last_preview_frame, "PAUSADO - F11 para continuar")
            time.sleep(0.02)
            continue

        ok, frame = cap.read()
        if not ok:
            if alignment_window is not None and alignment_window.winfo_exists():
                alignment_window.unavailable()
            if not SELECTING_POINT:
                stop_drag()
                reset_tracking()
            report_status("SIN IMAGEN DE CÁMARA")
            time.sleep(0.03)  # Avoid a busy loop when the device disconnects.
            continue

        frame = cv2.flip(frame, 1)
        last_preview_frame = frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_gray_frame = gray
        now = time.time()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = face_mesh.process(rgb)  # Raw camera data, never overlays or text.
        if not res.multi_face_landmarks:
            update_alignment_guide(frame,None)
            brow_detector = None
            if not SELECTING_POINT:
                stop_drag()
                reset_tracking()
            last_move_time, dwell_progress = now, 0.0
            mouth_open_prev, mouth_open_start, mouth_click_armed = False, None, False
            wink_candidate, wink_candidate_frames = None, 0
            report_status("BUSCANDO CARA · " + FACE_POINT)
            present_camera(frame, "BUSCANDO CARA")
            continue

        lm = res.multi_face_landmarks[0].landmark
        update_alignment_guide(frame,lm)
        face_anchor = smooth_face_anchor(face_anchor_px(lm, frame.shape[1], frame.shape[0]))
        selecting = SELECTING_POINT
        if selecting:
            # Seed the optical tracker on today's face position, not saved screen coordinates.
            on_mouse(cv2.EVENT_LBUTTONDOWN, face_anchor[0], face_anchor[1], None, None)
            last_move_time, dwell_progress = now, 0.0
        else:
            update_optical_tracking(gray, now)
            apply_face_anchor_correction(face_anchor)

        ratio_raw = mouth_open_ratio(lm)
        gesture = detect_gesture(lm, ratio_raw, now)
        if gesture is not None and not selecting and not SELECTING_POINT:
            execute_gesture(gesture)

        if DWELL_ENABLED and not SELECTING_POINT and (not drag_mode or pointer_over_controls()) and not (floating_actions_root is not None and floating_actions_root.moving):
            current_cursor_pos = pyautogui.position()
            moved_px = math.hypot(current_cursor_pos[0]-last_cursor_pos[0],
                                  current_cursor_pos[1]-last_cursor_pos[1])
            if moved_px > DWELL_STILL_RADIUS_PX:
                last_move_time = now
                last_cursor_pos = current_cursor_pos
                dwell_progress = 0.0
            else:
                elapsed = now-last_move_time
                dwell_progress = clamp(elapsed/DWELL_CLICK_SEC, 0.0, 1.0)
                if elapsed >= DWELL_CLICK_SEC and now-last_dwell_click_time >= DWELL_POST_CLICK_DELAY:
                    do_click()
                    last_dwell_click_time = last_move_time = now
                    last_cursor_pos = pyautogui.position()
                    dwell_progress = 0.0
        else:
            dwell_progress = 0.0

        if AUTO_ZOOM_ENABLED:
            if cursor_speed < 30 and not zoom_active:
                zoom_in_windows()
            elif cursor_speed > 80 and zoom_active:
                zoom_out_windows()

        state = "ACTIVO · " + FACE_POINT if wink_calibrated else "CALIBRANDO · mantené los ojos abiertos"
        report_status(state)
        present_camera(frame, state)

finally:
    if action_audio is not None:
        action_audio.close()
    release_all_inputs(close_context_menu=False)
    try:
        if zoom_active:
            zoom_out_windows()
    except Exception:
        pass

    try:
        hotkey_listener.stop()
    except Exception:
        pass

    try:
        face_mesh.close()
    except Exception:
        pass

    try:
        cap.release()
    except Exception:
        pass

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    try:
        if floating_actions_root is not None:
            floating_actions_root.destroy()
    except Exception:
        pass

    try:
        if floating_keyboard_root is not None:
            floating_keyboard_root.destroy()
    except Exception:
        pass

    # Close any remaining context menu after our windows have been removed.
    try:
        pyautogui.press("esc")
    except Exception:
        pass
