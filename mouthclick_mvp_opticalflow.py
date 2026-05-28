import os
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
from pynput import keyboard
import winsound

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

PROFILES_FILE = "profiles.json"

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

WINK_DIFF_LEVELS = ["muy sensible", "sensible", "normal", "estricto", "muy estricto"]
WINK_DIFF_THR_BY_LEVEL = {
    "muy sensible": 0.030,
    "sensible": 0.045,
    "normal": 0.060,
    "estricto": 0.080,
    "muy estricto": 0.105,
}
WINK_CLOSED_RATIO_BY_LEVEL = {
    "muy sensible": 0.78,
    "sensible": 0.72,
    "normal": 0.66,
    "estricto": 0.60,
    "muy estricto": 0.54,
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
    "camera": 0,
    "sens_x": "media",
    "sens_y": "media",
    "sensitivity": "media",  # compatibilidad con profiles viejos
    "stabilize": True,
    "zoom": False,
    "dwell_time": 2.0,
    "wink_diff_sens": "normal",
    "tracking_mode": "Punto manual",
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
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)


def normalize_profile(p):
    """Soporta profiles viejos con 'sensitivity' única."""
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


def show_gui_menu():
    profiles = load_profiles()
    if not profiles:
        profiles = {"Default": DEFAULT_PROFILE.copy()}

    window = tk.Tk()
    window.title("MouthClick MVP - Optical Flow")
    window.resizable(False, False)

    # Ventana con scroll para pantallas chicas
    outer = ttk.Frame(window)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, width=420, height=680, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    parent = ttk.Frame(canvas)

    parent.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=parent, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    tk.Label(parent, text="MOUTHCLICK MVP", font=("Arial", 16, "bold")).pack(pady=10)

    selected_profile = tk.StringVar(value=list(profiles.keys())[0])
    profile_name_var = tk.StringVar(value=selected_profile.get())

    # Variables
    mouth_action_var = tk.StringVar(value="Click izquierdo")
    wink_left_action_var = tk.StringVar(value="Nada")
    wink_right_action_var = tk.StringVar(value="Nada")
    sens_x_var = tk.StringVar(value=DEFAULT_PROFILE["sens_x"])
    sens_y_var = tk.StringVar(value=DEFAULT_PROFILE["sens_y"])
    stabilize_var = tk.BooleanVar(value=True)
    zoom_var = tk.BooleanVar(value=False)
    dwell_time_var = tk.StringVar(value="2.0")
    wink_diff_sens_var = tk.StringVar(value=DEFAULT_PROFILE["wink_diff_sens"])
    tracking_mode_var = tk.StringVar(value="Punto manual")

    cam_names, cam_map = get_camera_options()
    cam_index_var = tk.StringVar(value=cam_names[0] if cam_names else "Cam 0")

    frame_profile = tk.LabelFrame(parent, text="Perfil")
    frame_profile.pack(fill="x", padx=20, pady=8)

    profile_combo = ttk.Combobox(
        frame_profile,
        textvariable=selected_profile,
        values=list(profiles.keys()),
        state="readonly"
    )
    profile_combo.pack(fill="x", padx=10, pady=4)

    tk.Label(frame_profile, text="Nombre para guardar / nuevo perfil").pack(anchor="w", padx=10)
    tk.Entry(frame_profile, textvariable=profile_name_var).pack(fill="x", padx=10, pady=4)

    frame_click = tk.LabelFrame(parent, text="Acciones por gesto")
    frame_click.pack(fill="x", padx=20, pady=8)

    def combo_row(label, var):
        tk.Label(frame_click, text=label).pack(anchor="w", padx=10)
        ttk.Combobox(
            frame_click,
            textvariable=var,
            values=AVAILABLE_ACTIONS,
            state="readonly"
        ).pack(fill="x", padx=10, pady=4)

    combo_row("Boca", mouth_action_var)
    combo_row("Guiño izquierdo", wink_left_action_var)
    combo_row("Guiño derecho", wink_right_action_var)

    frame_wink = tk.LabelFrame(parent, text="Sensibilidad de guiño")
    frame_wink.pack(fill="x", padx=20, pady=8)

    ttk.Combobox(
        frame_wink,
        textvariable=wink_diff_sens_var,
        values=WINK_DIFF_LEVELS,
        state="readonly"
    ).pack(fill="x", padx=10, pady=5)

    tk.Label(
        frame_wink,
        text="Más sensible detecta un cierre menor del párpado. Más estricto exige cerrar más el ojo y reduce falsos positivos.",
        font=("Arial", 9),
        justify="left",
        wraplength=360
    ).pack(anchor="w", padx=10, pady=5)

    frame_cam = tk.LabelFrame(parent, text="Cámara")
    frame_cam.pack(fill="x", padx=20, pady=8)

    ttk.Combobox(
        frame_cam,
        textvariable=cam_index_var,
        values=cam_names,
        state="readonly"
    ).pack(fill="x", padx=10, pady=5)

    frame_tracking = tk.LabelFrame(parent, text="Tracking de cursor")
    frame_tracking.pack(fill="x", padx=20, pady=8)

    ttk.Combobox(
        frame_tracking,
        textvariable=tracking_mode_var,
        values=["Punto manual"],
        state="readonly"
    ).pack(fill="x", padx=10, pady=5)

    tk.Label(
        frame_tracking,
        text="Al iniciar, hacé click sobre el punto de la cara a seguir.\nRecomendado: entrecejo, nariz, ceja o pómulo.",
        font=("Arial", 9),
        justify="left"
    ).pack(anchor="w", padx=10, pady=5)

    frame_sens = tk.LabelFrame(parent, text="Sensibilidad")
    frame_sens.pack(fill="x", padx=20, pady=8)

    tk.Label(frame_sens, text="Eje X").pack(anchor="w", padx=10)
    ttk.Combobox(
        frame_sens,
        textvariable=sens_x_var,
        values=SENS_LEVELS,
        state="readonly"
    ).pack(fill="x", padx=10, pady=4)

    tk.Label(frame_sens, text="Eje Y").pack(anchor="w", padx=10)
    ttk.Combobox(
        frame_sens,
        textvariable=sens_y_var,
        values=SENS_LEVELS,
        state="readonly"
    ).pack(fill="x", padx=10, pady=4)

    frame_stab = tk.LabelFrame(parent, text="Estabilización")
    frame_stab.pack(fill="x", padx=20, pady=8)

    tk.Checkbutton(
        frame_stab,
        text="Suavizado liviano del punto óptico",
        variable=stabilize_var
    ).pack(anchor="w", padx=10, pady=4)

    tk.Checkbutton(
        frame_stab,
        text="Zoom automático Windows",
        variable=zoom_var
    ).pack(anchor="w", padx=10, pady=4)

    frame_dwell = tk.LabelFrame(parent, text="Autoclick por permanencia")
    frame_dwell.pack(fill="x", padx=20, pady=8)

    ttk.Combobox(
        frame_dwell,
        textvariable=dwell_time_var,
        values=["0.5", "1.0", "1.5", "2.0", "2.5", "3.0"],
        state="readonly"
    ).pack(fill="x", padx=10, pady=5)

    tk.Label(
        parent,
        text="Hotkeys: F12 salir | F11 pausa | F7 centrar | R re-seleccionar punto | K recalibrar guiño | M ventana | F9 teclado | B burbuja | F5/F6 sens guiño | F8 autoclick",
        font=("Arial", 9),
        wraplength=360,
        justify="center"
    ).pack(pady=8)

    selected_config = {}

    def apply_profile(profile_name):
        p = normalize_profile(profiles.get(profile_name, DEFAULT_PROFILE))
        profile_name_var.set(profile_name)

        mouth_action_var.set(p.get("mouth", "Click izquierdo"))
        wink_left_action_var.set(p.get("wink_left", "Nada"))
        wink_right_action_var.set(p.get("wink_right", "Nada"))
        sens_x_var.set(p.get("sens_x", DEFAULT_PROFILE["sens_x"]))
        sens_y_var.set(p.get("sens_y", DEFAULT_PROFILE["sens_y"]))
        stabilize_var.set(bool(p.get("stabilize", True)))
        zoom_var.set(bool(p.get("zoom", False)))
        dwell_time_var.set(str(p.get("dwell_time", 2.0)))
        wink_diff_sens_var.set(p.get("wink_diff_sens", DEFAULT_PROFILE["wink_diff_sens"]))
        tracking_mode_var.set(p.get("tracking_mode", "Punto manual"))

        cam_idx = int(p.get("camera", 0))
        for name, idx in cam_map.items():
            if idx == cam_idx:
                cam_index_var.set(name)
                break

    def on_profile_selected(_event=None):
        apply_profile(selected_profile.get())

    profile_combo.bind("<<ComboboxSelected>>", on_profile_selected)
    apply_profile(selected_profile.get())

    def start():
        name = profile_name_var.get().strip() or "Default"

        p = {
            "mouth": mouth_action_var.get(),
            "wink_left": wink_left_action_var.get(),
            "wink_right": wink_right_action_var.get(),
            "camera": cam_map.get(cam_index_var.get(), 0),
            "sens_x": sens_x_var.get(),
            "sens_y": sens_y_var.get(),
            "sensitivity": sens_x_var.get(),  # compatibilidad
            "stabilize": bool(stabilize_var.get()),
            "zoom": bool(zoom_var.get()),
            "dwell_time": float(dwell_time_var.get()),
            "wink_diff_sens": wink_diff_sens_var.get(),
            "tracking_mode": tracking_mode_var.get(),
        }

        profiles[name] = p
        save_profiles(profiles)

        selected_config.update(p)
        window.quit()
        window.destroy()

    tk.Button(
        parent,
        text="COMENZAR",
        font=("Arial", 14, "bold"),
        command=start,
        bg="#4CAF50",
        fg="white"
    ).pack(pady=18)

    window.mainloop()

    if not selected_config:
        selected_config.update(normalize_profile(profiles.get(selected_profile.get(), DEFAULT_PROFILE)))

    return selected_config


CONFIG = show_gui_menu()

GESTURE_ACTIONS = {
    "mouth": CONFIG["mouth"],
    "wink_left": CONFIG["wink_left"],
    "wink_right": CONFIG["wink_right"],
}

CAMERA_INDEX = int(CONFIG["camera"])
SENS_X = CONFIG.get("sens_x", CONFIG.get("sensitivity", "media"))
SENS_Y = CONFIG.get("sens_y", CONFIG.get("sensitivity", "media"))
STABILIZE = bool(CONFIG.get("stabilize", True))
AUTO_ZOOM_ENABLED = bool(CONFIG.get("zoom", False))
DWELL_CLICK_SEC = float(CONFIG.get("dwell_time", 2.0))
WINK_DIFF_SENS = CONFIG.get("wink_diff_sens", DEFAULT_PROFILE["wink_diff_sens"])

REL_GAIN_X = GAIN_X_BY_LEVEL.get(SENS_X, GAIN_X_BY_LEVEL["media"])
REL_GAIN_Y = GAIN_Y_BY_LEVEL.get(SENS_Y, GAIN_Y_BY_LEVEL["media"])
WINK_DIFF_THR = WINK_DIFF_THR_BY_LEVEL.get(WINK_DIFF_SENS, WINK_DIFF_THR_BY_LEVEL[DEFAULT_PROFILE["wink_diff_sens"]])
WINK_CLOSED_RATIO_THR = WINK_CLOSED_RATIO_BY_LEVEL.get(WINK_DIFF_SENS, WINK_CLOSED_RATIO_BY_LEVEL[DEFAULT_PROFILE["wink_diff_sens"]])

CURRENT_SENS_X_INDEX = SENS_LEVELS.index(SENS_X) if SENS_X in SENS_LEVELS else 2
CURRENT_SENS_Y_INDEX = SENS_LEVELS.index(SENS_Y) if SENS_Y in SENS_LEVELS else 2
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
DWELL_ENABLED = False

SHOW_OVERLAY = True
WINDOW_NAME = "Face Mouse"
WINDOW_FULLSCREEN = False
FLOATING_KEYBOARD_VISIBLE = True
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
POINT_SMOOTH_ALPHA = 0.65 if STABILIZE else 1.0  # alto = más responsivo
DEADZONE_PX_CAMERA = 0.15                         # zona muerta en pixels de cámara
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
CLICK_ARM_RATIO = 0.055
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
DWELL_STILL_RADIUS_PX = 20
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
    # Promedio de landmarks rígidos alrededor de nariz/entrecejo para reducir jitter de un punto único.
    stable_idxs = [168, 6, 197, 195, 5, 4]
    pts = []
    for idx in stable_idxs:
        if len(lm) > idx:
            p = lm[idx]
            pts.append((float(p.x * frame_w), float(p.y * frame_h)))

    if pts:
        return (
            sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts),
        )

    left = lm[33]
    right = lm[263]
    return (
        float(((left.x + right.x) * 0.5) * frame_w),
        float(((left.y + right.y) * 0.5) * frame_h),
    )


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
    global WINDOW_FULLSCREEN
    WINDOW_FULLSCREEN = not WINDOW_FULLSCREEN
    try:
        if WINDOW_FULLSCREEN:
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 960, 720)
        print(f"[WINDOW] {'Fullscreen' if WINDOW_FULLSCREEN else 'Normal'}")
    except Exception as e:
        print("[WINDOW WARN]", e)


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


def do_right_click():
    global suspend_move_until
    x, y = pyautogui.position()
    suspend_move_until = time.time() + FREEZE_ON_GESTURE_SEC
    pyautogui.click(x=x, y=y, button="right")


def do_double_click():
    global suspend_move_until
    x, y = pyautogui.position()
    suspend_move_until = time.time() + FREEZE_ON_GESTURE_SEC
    pyautogui.click(x=x, y=y)
    time.sleep(DBLCLICK_INTERVAL_SEC)
    pyautogui.click(x=x, y=y)


def start_drag():
    global drag_active, suspend_move_until
    if not drag_active:
        suspend_move_until = 0.0
        pyautogui.mouseDown(button="left")
        drag_active = True
        print("[DRAG] START")


def stop_drag():
    global drag_active, suspend_move_until
    if drag_active:
        pyautogui.mouseUp(button="left")
        drag_active = False
        suspend_move_until = 0.0
        print("[DRAG] STOP")


def release_all_inputs(close_context_menu=True):
    global drag_active, suspend_move_until
    try:
        pyautogui.mouseUp(button="left")
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
    pattern = ACTION_SOUNDS.get(action_name)
    if not pattern:
        return
    try:
        for freq, dur in pattern:
            winsound.Beep(freq, dur)
    except Exception:
        pass


def execute_action(action_name):
    if action_name == "Nada":
        return
    if action_debounced(action_name):
        return
    play_action_sound(action_name)
    if action_name == "Click izquierdo":
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
    global keyboard_size_index, floating_keyboard_root, floating_actions_root
    keyboard_size_index = clamp(keyboard_size_index + delta, 0, len(KEYBOARD_SIZE_LEVELS) - 1)
    if floating_keyboard_root is None:
        return
    try:
        was_visible = FLOATING_KEYBOARD_VISIBLE
        actions_was_visible = FLOATING_ACTIONS_VISIBLE
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
    FLOATING_ACTIONS_VISIBLE = not FLOATING_ACTIONS_VISIBLE
    if floating_actions_root is None:
        return
    if FLOATING_ACTIONS_VISIBLE:
        floating_actions_root.deiconify()
    else:
        floating_actions_root.withdraw()
    print(f"[ACTIONS] {'ON' if FLOATING_ACTIONS_VISIBLE else 'OFF'}")


def create_quick_actions_bubble():
    global floating_actions_root, floating_actions_pos, floating_actions_collapse_after
    if floating_keyboard_root is None:
        return None
    try:
        root = tk.Toplevel(floating_keyboard_root)
        root.title("MouthClick Acciones")
        root.geometry(geometry_at_pos(58, 58, floating_actions_pos, y_bias=-330))
        root.resizable(False, False)
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#111827")
        root.protocol("WM_DELETE_WINDOW", toggle_floating_actions)
        drag_state = {"x": 0, "y": 0}

        items = [
            ("Esc", lambda: None if keyboard_debounced("bubble:esc") else release_all_inputs(close_context_menu=True)),
            ("Click", lambda: None if keyboard_debounced("bubble:click") else do_click()),
            ("Derecho", lambda: None if keyboard_debounced("bubble:right") else do_right_click()),
            ("Drag", lambda: None if keyboard_debounced("bubble:drag") else (stop_drag() if drag_active else start_drag())),
            ("Teclado", toggle_floating_keyboard),
            ("Calib", reset_wink_calibration),
            ("Centro", center_mouse),
        ]

        collapsed = {"value": True}
        buttons = []

        def remember_pos():
            global floating_actions_pos
            floating_actions_pos = (root.winfo_x(), root.winfo_y())

        def collapse_now():
            if collapsed["value"]:
                return
            collapsed["value"] = True
            for btn in buttons:
                btn.place_forget()
            remember_pos()
            root.geometry(geometry_at_pos(58, 58, floating_actions_pos))
            bubble.place(x=4, y=4, width=50, height=50)

        def schedule_collapse(_event=None):
            global floating_actions_collapse_after
            floating_actions_collapse_after = time.time() + 0.9

        def expand(_event=None):
            global floating_actions_collapse_after
            floating_actions_collapse_after = 0.0
            if not collapsed["value"]:
                return
            collapsed["value"] = False
            remember_pos()
            root.geometry(geometry_at_pos(420, 136, floating_actions_pos))
            bubble.place(x=181, y=43, width=58, height=50)
            positions = [(12, 12), (100, 12), (260, 12), (348, 12), (12, 86), (168, 86), (324, 86)]
            for btn, pos in zip(buttons, positions):
                btn.place(x=pos[0], y=pos[1], width=78, height=38)

        def start_move(event):
            expand()
            drag_state["x"] = event.x_root - root.winfo_x()
            drag_state["y"] = event.y_root - root.winfo_y()

        def do_move(event):
            root.geometry(f"+{event.x_root - drag_state['x']}+{event.y_root - drag_state['y']}")
            remember_pos()

        bubble = tk.Button(
            root,
            text="☰",
            command=expand,
            font=("Arial", 18, "bold"),
            bg="#111827",
            fg="#e5e7eb",
            relief="flat",
            borderwidth=0,
            highlightthickness=2,
            highlightbackground="#e5e7eb",
        )
        bubble.place(x=4, y=4, width=50, height=50)

        for label, cmd in items:
            btn = tk.Button(root, text=label, command=cmd, width=8, height=1)
            btn.bind("<Enter>", expand)
            btn.bind("<Leave>", schedule_collapse)
            buttons.append(btn)

        root.bind("<Enter>", expand)
        root.bind("<Leave>", schedule_collapse)
        bubble.bind("<Enter>", expand)
        bubble.bind("<ButtonPress-1>", start_move)
        bubble.bind("<B1-Motion>", do_move)
        bubble.bind("<Leave>", schedule_collapse)
        root.collapse_now = collapse_now

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

        make_window_no_activate(root)
        floating_keyboard_root = root
        if not FLOATING_KEYBOARD_VISIBLE:
            root.withdraw()
        return root
    except Exception as e:
        print("[KEYBOARD WARN] No se pudo crear teclado flotante:", e)
        return None


def update_floating_keyboard():
    try:
        global floating_actions_collapse_after
        remember_keyboard_target()
        if floating_keyboard_root is not None:
            update_keyboard_move_mode()
            floating_keyboard_root.update_idletasks()
            floating_keyboard_root.update()
        if floating_actions_root is not None:
            floating_actions_root.update_idletasks()
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
    SELECTING_POINT = True
    tracking_point = None
    prev_gray = None
    last_good_point = None
    smooth_x = None
    smooth_y = None
    selected_anchor_offset = None
    last_face_anchor = None
    print("[TRACK] Seleccioná un punto con click en la ventana")


def reset_wink_calibration():
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


def detect_gesture(lm, ratio_raw, now):
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
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir cámara {index}")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 60)

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


def on_press(key):
    global RUNNING, PAUSED, DWELL_ENABLED
    global CURRENT_SENS_X_INDEX, CURRENT_SENS_Y_INDEX, REL_GAIN_X, REL_GAIN_Y
    global CUSTOM_SENS_X_STEPS, CUSTOM_SENS_Y_STEPS
    global CURRENT_WINK_DIFF_INDEX, WINK_DIFF_THR, WINK_CLOSED_RATIO_THR
    global dwell_progress

    try:
        if key == keyboard.Key.f12:
            print("[HOTKEY] F12 -> salir")
            release_all_inputs(close_context_menu=True)
            RUNNING = False

        elif key == keyboard.Key.f11:
            release_all_inputs(close_context_menu=True)
            PAUSED = not PAUSED
            print("[HOTKEY] F11 -> pausa", PAUSED)

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
            release_all_inputs(close_context_menu=True)

        elif key == keyboard.Key.f3:
            if CUSTOM_SENS_X_STEPS > 0:
                CUSTOM_SENS_X_STEPS -= 1
                REL_GAIN_X = GAIN_X_BY_LEVEL[SENS_LEVELS[-1]] + CUSTOM_SENS_X_STEPS * 8.0
                print(f"[SENS] X -> custom+{CUSTOM_SENS_X_STEPS} {REL_GAIN_X}")
            else:
                CURRENT_SENS_X_INDEX = max(0, CURRENT_SENS_X_INDEX - 1)
                REL_GAIN_X = GAIN_X_BY_LEVEL[SENS_LEVELS[CURRENT_SENS_X_INDEX]]
                print(f"[SENS] X -> {SENS_LEVELS[CURRENT_SENS_X_INDEX]} {REL_GAIN_X}")

        elif key == keyboard.Key.f4:
            if CURRENT_SENS_X_INDEX >= len(SENS_LEVELS) - 1:
                CUSTOM_SENS_X_STEPS += 1
                REL_GAIN_X = GAIN_X_BY_LEVEL[SENS_LEVELS[-1]] + CUSTOM_SENS_X_STEPS * 8.0
                print(f"[SENS] X -> custom+{CUSTOM_SENS_X_STEPS} {REL_GAIN_X}")
            else:
                CURRENT_SENS_X_INDEX += 1
                REL_GAIN_X = GAIN_X_BY_LEVEL[SENS_LEVELS[CURRENT_SENS_X_INDEX]]
                print(f"[SENS] X -> {SENS_LEVELS[CURRENT_SENS_X_INDEX]} {REL_GAIN_X}")

        elif key == keyboard.Key.f1:
            if CUSTOM_SENS_Y_STEPS > 0:
                CUSTOM_SENS_Y_STEPS -= 1
                REL_GAIN_Y = GAIN_Y_BY_LEVEL[SENS_LEVELS[-1]] + CUSTOM_SENS_Y_STEPS * 7.0
                print(f"[SENS] Y -> custom+{CUSTOM_SENS_Y_STEPS} {REL_GAIN_Y}")
            else:
                CURRENT_SENS_Y_INDEX = max(0, CURRENT_SENS_Y_INDEX - 1)
                REL_GAIN_Y = GAIN_Y_BY_LEVEL[SENS_LEVELS[CURRENT_SENS_Y_INDEX]]
                print(f"[SENS] Y -> {SENS_LEVELS[CURRENT_SENS_Y_INDEX]} {REL_GAIN_Y}")

        elif key == keyboard.Key.f2:
            if CURRENT_SENS_Y_INDEX >= len(SENS_LEVELS) - 1:
                CUSTOM_SENS_Y_STEPS += 1
                REL_GAIN_Y = GAIN_Y_BY_LEVEL[SENS_LEVELS[-1]] + CUSTOM_SENS_Y_STEPS * 7.0
                print(f"[SENS] Y -> custom+{CUSTOM_SENS_Y_STEPS} {REL_GAIN_Y}")
            else:
                CURRENT_SENS_Y_INDEX += 1
                REL_GAIN_Y = GAIN_Y_BY_LEVEL[SENS_LEVELS[CURRENT_SENS_Y_INDEX]]
                print(f"[SENS] Y -> {SENS_LEVELS[CURRENT_SENS_Y_INDEX]} {REL_GAIN_Y}")

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
                elif key.char and key.char.lower() == "m":
                    toggle_camera_window()
                elif key.char and key.char.lower() == "k":
                    reset_wink_calibration()
                elif key.char and key.char.lower() == "b":
                    toggle_floating_actions()
            except Exception:
                pass

    except Exception as e:
        print("[HOTKEY WARN]", e)


# =========================================
# ========== INICIALIZACIÓN ===============
# =========================================

cap = open_camera(CAMERA_INDEX)
if cap is None:
    raise SystemExit("No se pudo iniciar la cámara.")

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.4,
    min_tracking_confidence=0.4
)

setup_camera_window()
create_floating_keyboard()
create_quick_actions_bubble()

hotkey_listener = keyboard.Listener(on_press=on_press)
hotkey_listener.start()

print("[TRACK] Hacé click sobre el punto de la cara que querés seguir.")

frame_count = 0
last_debug_print = 0.0

try:
    while RUNNING:
        update_floating_keyboard()

        ok, frame = cap.read()
        if not ok:
            continue

        if PAUSED:
            cv2.putText(frame, "PAUSA - F11 para continuar", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow(WINDOW_NAME, frame)
            pause_key = cv2.waitKey(1) & 0xFF
            if pause_key == ord("q"):
                break
            elif pause_key == ord("m"):
                toggle_camera_window()
            elif pause_key == ord("t"):
                toggle_floating_keyboard()
            time.sleep(0.03)
            continue

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_gray_frame = gray.copy()
        now = time.time()
        frame_count += 1

        # ====================================================
        # Movimiento por Optical Flow
        # ====================================================
        if SELECTING_POINT:
            cv2.putText(frame, "Click sobre nariz/entrecejo para seleccionar punto",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 255, 255), 2)
            cv2.putText(frame, "Recomendado: entrecejo, nariz, ceja o pomulo",
                        (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            prev_gray = gray.copy()

        elif tracking_point is not None and prev_gray is not None:
            next_point, status, err = cv2.calcOpticalFlowPyrLK(
                prev_gray, gray, tracking_point, None, **lk_params
            )

            if next_point is not None and status is not None and status[0][0] == 1:
                old_x, old_y = tracking_point[0][0]
                new_x, new_y = next_point[0][0]

                # Suavizado del punto, no del mouse
                if smooth_x is None:
                    smooth_x, smooth_y = float(new_x), float(new_y)
                else:
                    smooth_x = (1 - POINT_SMOOTH_ALPHA) * smooth_x + POINT_SMOOTH_ALPHA * float(new_x)
                    smooth_y = (1 - POINT_SMOOTH_ALPHA) * smooth_y + POINT_SMOOTH_ALPHA * float(new_y)

                dx_cam = smooth_x - float(old_x)
                dy_cam = smooth_y - float(old_y)

                if abs(dx_cam) < DEADZONE_PX_CAMERA:
                    dx_cam = 0.0
                if abs(dy_cam) < DEADZONE_PX_CAMERA:
                    dy_cam = 0.0

                precision_scale = precision_scale_from_camera_delta(dx_cam, dy_cam)
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
                        tx = int(clamp_with_margin(cur_x + dx_mouse, 0, SCREEN_W - 1))
                        ty = int(clamp_with_margin(cur_y + dy_mouse, 0, SCREEN_H - 1))
                        pyautogui.moveTo(tx, ty)

                        now_pos = pyautogui.position()
                        dt = max(1e-6, time.time() - prev_speed_time)
                        cursor_speed = math.hypot(
                            now_pos[0] - prev_cursor_pos[0],
                            now_pos[1] - prev_cursor_pos[1]
                        ) / dt
                        prev_cursor_pos = now_pos
                        prev_speed_time = time.time()

                # Actualizamos el punto con la posición SUAVIZADA para evitar drift raro
                tracking_point = np.array([[[np.float32(smooth_x), np.float32(smooth_y)]]], dtype=np.float32)
                last_good_point = (smooth_x, smooth_y)

                draw_control_cross(frame, smooth_x, smooth_y)

            else:
                if last_face_anchor is not None and selected_anchor_offset is not None:
                    recover_x = clamp(last_face_anchor[0] + selected_anchor_offset[0], 0, frame.shape[1] - 1)
                    recover_y = clamp(last_face_anchor[1] + selected_anchor_offset[1], 0, frame.shape[0] - 1)
                    smooth_x = float(recover_x)
                    smooth_y = float(recover_y)
                    tracking_point = np.array([[[np.float32(smooth_x), np.float32(smooth_y)]]], dtype=np.float32)
                    last_good_point = (smooth_x, smooth_y)
                    cv2.putText(frame, "Tracking recuperado con MediaPipe",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    draw_control_cross(frame, smooth_x, smooth_y)
                else:
                    cv2.putText(frame, "Tracking perdido - presiona R o click en otro punto",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                    SELECTING_POINT = True
                    tracking_point = None

            prev_gray = gray.copy()

        # ====================================================
        # Gestos con MediaPipe
        # Procesar todos los frames para estabilizar la lectura de párpados
        # ====================================================
        ratio_raw = 0.0
        gesture = None

        if frame_count % FACE_PROCESS_EVERY_N == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            if res.multi_face_landmarks:
                lm = res.multi_face_landmarks[0].landmark
                face_anchor = smooth_face_anchor(face_anchor_px(lm, frame.shape[1], frame.shape[0]))

                ratio_raw = mouth_open_ratio(lm)
                mouth_ratio_vis = 0.5 * mouth_ratio_vis + 0.5 * ratio_raw
                mouth_open_now = ratio_raw >= SLOW_START_RATIO

                gesture = detect_gesture(lm, ratio_raw, now)
                apply_face_anchor_correction(face_anchor)

                left_ear_vis = (1 - EAR_VIS_ALPHA) * left_ear_vis + EAR_VIS_ALPHA * last_left_ear
                right_ear_vis = (1 - EAR_VIS_ALPHA) * right_ear_vis + EAR_VIS_ALPHA * last_right_ear

                if gesture is not None:
                    action_name = GESTURE_ACTIONS.get(gesture, "Nada")
                    print(f"[GESTURE] {gesture} -> {action_name}")
                    execute_action(action_name)

        # ====================================================
        # Dwell click
        # ====================================================
        if DWELL_ENABLED:
            current_cursor_pos = pyautogui.position()

            moved_px = math.hypot(
                current_cursor_pos[0] - last_cursor_pos[0],
                current_cursor_pos[1] - last_cursor_pos[1]
            )

            if moved_px > DWELL_STILL_RADIUS_PX:
                last_move_time = now
                last_cursor_pos = current_cursor_pos
                dwell_progress = 0.0
            else:
                dwell_elapsed = now - last_move_time
                dwell_progress = clamp(dwell_elapsed / DWELL_CLICK_SEC, 0.0, 1.0)

                if dwell_elapsed >= DWELL_CLICK_SEC:
                    if (now - last_dwell_click_time) >= DWELL_POST_CLICK_DELAY:
                        print("[DWELL] CLICK")
                        do_click()
                        last_dwell_click_time = now
                        last_move_time = now
                        last_cursor_pos = pyautogui.position()
                        dwell_progress = 0.0
        else:
            dwell_progress = 0.0

        # ====================================================
        # Auto zoom simple
        # ====================================================
        if AUTO_ZOOM_ENABLED:
            if cursor_speed < 30 and not zoom_active:
                zoom_in_windows()
            elif cursor_speed > 80 and zoom_active:
                zoom_out_windows()

        # ====================================================
        # Overlay visual
        # ====================================================
        if SHOW_OVERLAY:
            status = (
                f"OPTICAL MVP | X:{SENS_LEVELS[CURRENT_SENS_X_INDEX]}+{CUSTOM_SENS_X_STEPS} Y:{SENS_LEVELS[CURRENT_SENS_Y_INDEX]}+{CUSTOM_SENS_Y_STEPS} | "
                f"gain=({REL_GAIN_X:.1f},{REL_GAIN_Y:.1f}) | "
                f"wink:{WINK_DIFF_LEVELS[CURRENT_WINK_DIFF_INDEX]}<{WINK_CLOSED_RATIO_THR:.2f} | "
                f"tracking={'SELECT' if SELECTING_POINT else 'OK'} | "
                f"mouth={GESTURE_ACTIONS['mouth']} winkL={GESTURE_ACTIONS['wink_left']} winkR={GESTURE_ACTIONS['wink_right']} | "
                f"dwell={'ON' if DWELL_ENABLED else 'OFF'}"
            )
            cv2.putText(frame, status, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 2)

            cv2.putText(frame, f"EAR L:{last_left_ear:.3f} R:{last_right_ear:.3f} | norm L:{left_eye_open_norm:.2f} R:{right_eye_open_norm:.2f} | Mouth:{ratio_raw:.3f}",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 220, 120), 2)

            draw_wink_debug(frame, left_eye_open_norm, right_eye_open_norm, last_eye_diff)

            if not wink_calibrated:
                draw_text_with_shadow(frame, "MANTENE AMBOS OJOS ABIERTOS PARA CALIBRAR",
                                      (20, 90), 0.62, (0, 255, 255), 2)

            if wink_warning_text and now < wink_warning_until:
                draw_text_with_shadow(frame, wink_warning_text,
                                      (20, 120), 0.62, (0, 180, 255), 2)

            cv2.putText(frame, "Esc/F10 libera | F12 salir | F7 centro | R punto | K calib | F9/T teclado | B burbuja | F5/F6 guino",
                        (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 2)

        if now - last_debug_print > 0.5:
            print(
                f"[STATE] tracking={'SELECT' if SELECTING_POINT else 'OK'} | "
                f"cursor_speed={cursor_speed:.1f} | dwell={dwell_progress:.2f}"
            )
            last_debug_print = now

        cv2.imshow(WINDOW_NAME, frame)
        k = cv2.waitKey(1) & 0xFF

        if k == ord("q"):
            break
        elif k == ord("r"):
            reset_tracking()
        elif k == 27:
            release_all_inputs(close_context_menu=True)
        elif k == ord("m"):
            toggle_camera_window()
        elif k == ord("t"):
            toggle_floating_keyboard()
        elif k == ord("b"):
            toggle_floating_actions()
        elif k == ord("k"):
            reset_wink_calibration()
        elif k == ord("c"):
            center_mouse()

finally:
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
