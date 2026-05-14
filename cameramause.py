import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import time
import math
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
from collections import deque
from pynput import keyboard
import ctypes
import threading
from pygrabber.dshow_graph import FilterGraph

class CursorOverlay:
    def __init__(self, master):
        self.root = tk.Toplevel(master)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Usar blanco como color transparente
        self.root.configure(bg="white")
        self.root.attributes("-transparentcolor", "white")

        self.size = 80
        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg="white",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack()

        # Hacer la ventana "click-through" sin tocar layered
        self.root.update_idletasks()
        hwnd = self.root.winfo_id()

        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOOLWINDOW = 0x00000080

        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    def update_overlay(self, cursor_x, cursor_y, progress):
        x = int(cursor_x - self.size // 2)
        y = int(cursor_y - self.size // 2)
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")

        self.canvas.delete("all")

        cx = self.size // 2
        cy = self.size // 2
        r = 22

        # círculo base
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline="gray",
            width=4
        )

        # progreso
        if progress > 0:
            extent = progress * 360
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=90,
                extent=-extent,
                style="arc",
                outline="yellow",
                width=4
            )

        # punto central
        self.canvas.create_oval(
            cx - 3, cy - 3, cx + 3, cy + 3,
            fill="lime", outline="lime"
        )

        self.root.update()

    def hide(self):
        try:
            self.root.withdraw()
        except:
            pass

    def show(self):
        try:
            self.root.deiconify()
            self.root.lift()  # traer al frente
            self.root.attributes("-topmost", True)  # asegurar prioridad
            self.root.update()
        except:
            pass

    def destroy(self):
        try:
            self.root.destroy()
        except:
            pass

def list_camera_names():
    """
    Devuelve una lista de nombres de cámaras disponibles en Windows.
    Si falla, devuelve una lista vacía.
    """
    try:
        graph = FilterGraph()
        devices = graph.get_input_devices()
        return devices if devices else []
    except Exception as e:
        print(f"[WARN] No se pudieron listar cámaras por nombre: {e}")
        return []


def get_camera_options():
    """
    Devuelve:
    - cam_names: lista de nombres visibles en el combobox
    - cam_map: dict nombre -> índice
    """
    cam_names = list_camera_names()

    if not cam_names:
        # fallback
        cam_names = ["Cam 0", "Cam 1", "Cam 2"]

    cam_map = {name: idx for idx, name in enumerate(cam_names)}
    return cam_names, cam_map

AVAILABLE_ACTIONS = [
    "Nada",
    "Click izquierdo",
    "Doble click",
    "Click derecho",
    "Drag toggle"
]

def show_gui_menu():
    window = tk.Tk()
    window.title("Configuración FaceMouse")
    window.resizable(False, False)

    zoom_var = tk.BooleanVar(value=False)
    sensitivity_var = tk.StringVar(value="alta")
    stabilize_var = tk.BooleanVar(value=False)
    movement_point_var = tk.StringVar(value="Punta de nariz")
    dwell_time_var = tk.StringVar(value="2.0")

    mouth_action_var = tk.StringVar(value="Click izquierdo")
    wink_left_action_var = tk.StringVar(value="Nada")
    wink_right_action_var = tk.StringVar(value="Nada")

    cam_names, cam_map = get_camera_options()
    default_cam = cam_names[1] if cam_names else "Cam 0"
    cam_index_var = tk.StringVar(value=default_cam)


    tk.Label(window, text="FACE MOUSE CONTROL", font=("Arial", 18, "bold")).grid(
        row=0, column=0, columnspan=2, pady=12
    )

    left_col = tk.Frame(window)
    left_col.grid(row=1, column=0, padx=15, pady=5, sticky="n")

    right_col = tk.Frame(window)
    right_col.grid(row=1, column=1, padx=15, pady=5, sticky="n")

    # IZQUIERDA: acciones
    frame_click = tk.LabelFrame(left_col, text="Acciones por gesto")
    frame_click.pack(fill="x", pady=8)

    tk.Label(frame_click, text="Boca").pack(anchor="w", padx=10)
    ttk.Combobox(frame_click, textvariable=mouth_action_var,
                 values=AVAILABLE_ACTIONS, state="readonly", width=28).pack(padx=10, pady=4)

    tk.Label(frame_click, text="Guiño izquierdo").pack(anchor="w", padx=10)
    ttk.Combobox(frame_click, textvariable=wink_left_action_var,
                 values=AVAILABLE_ACTIONS, state="readonly", width=28).pack(padx=10, pady=4)

    tk.Label(frame_click, text="Guiño derecho").pack(anchor="w", padx=10)
    ttk.Combobox(frame_click, textvariable=wink_right_action_var,
                 values=AVAILABLE_ACTIONS, state="readonly", width=28).pack(padx=10, pady=4)

    frame_dwell = tk.LabelFrame(left_col, text="Tiempo de autoclick")
    frame_dwell.pack(fill="x", pady=8)

    ttk.Combobox(frame_dwell, textvariable=dwell_time_var,
                 values=["0.5", "1.0", "1.5", "2.0", "2.5", "3.0"],
                 state="readonly", width=28).pack(padx=10, pady=8)

    # DERECHA: cámara/config
    frame_cam = tk.LabelFrame(right_col, text="Cámara")
    frame_cam.pack(fill="x", pady=8)

    ttk.Combobox(frame_cam, textvariable=cam_index_var,
                 values=cam_names, state="readonly", width=28).pack(padx=10, pady=8)

    frame_point = tk.LabelFrame(right_col, text="Punto de movimiento")
    frame_point.pack(fill="x", pady=8)

    ttk.Combobox(frame_point, textvariable=movement_point_var,
                 values=["Punta de nariz", "Centro de cejas"],
                 state="readonly", width=28).pack(padx=10, pady=8)

    frame_sens = tk.LabelFrame(right_col, text="Sensibilidad")
    frame_sens.pack(fill="x", pady=8)

    ttk.Combobox(frame_sens, textvariable=sensitivity_var,
                 values=["baja", "media-baja", "media", "media-alta", "alta"],
                 state="readonly", width=28).pack(padx=10, pady=8)

    frame_stab = tk.LabelFrame(right_col, text="Estabilización")
    frame_stab.pack(fill="x", pady=8)

    tk.Checkbutton(frame_stab, text="Activar anti-temblor",
                   variable=stabilize_var).pack(anchor="w", padx=10, pady=8)

    frame_zoom = tk.LabelFrame(right_col, text="Zoom automático")
    frame_zoom.pack(fill="x", pady=8)

    tk.Checkbutton(frame_zoom, text="Activar zoom en modo preciso/lento",
                   variable=zoom_var).pack(anchor="w", padx=10, pady=8)

    hint = tk.Label(
        window,
        text="F3/F4 sensibilidad | F7 centrar | F8 autoclick | F9 recalibrar guiño | F10 drag | F11 pausa | F12 salir",
        font=("Arial", 9)
    )
    hint.grid(row=2, column=0, columnspan=2, pady=8)

    started = {"value": False}

    def start():
        started["value"] = True
        window.destroy()

    def on_close():
        started["value"] = False
        window.destroy()

    tk.Button(
    window,
    text="COMENZAR",
    font=("Arial", 14, "bold"),
    command=start,
    bg="#4CAF50",
    fg="white"
    ).grid(row=3, column=0, columnspan=2, pady=14)

    

    window.protocol("WM_DELETE_WINDOW", on_close)

    window.mainloop()

    if not started["value"]:
        return None

    return (
        {
            "mouth": mouth_action_var.get(),
            "wink_left": wink_left_action_var.get(),
            "wink_right": wink_right_action_var.get()
        },
        cam_map.get(cam_index_var.get(), 0),
        sensitivity_var.get(),
        bool(stabilize_var.get()),
        bool(zoom_var.get()),
        float(dwell_time_var.get()),
        movement_point_var.get()
    )

menu_result = show_gui_menu()

if menu_result is None:
    raise SystemExit("Programa cancelado desde el menú inicial.")

GESTURE_ACTIONS, CAMERA_INDEX, SENS, STABILIZE, AUTO_ZOOM_ENABLED, DWELL_CLICK_SEC, MOVEMENT_POINT = menu_result

MOVEMENT_LANDMARK_INDEX = 1 if MOVEMENT_POINT == "Punta de nariz" else 168
print("Punto de movimiento:", MOVEMENT_POINT, MOVEMENT_LANDMARK_INDEX)
print("Acciones:", GESTURE_ACTIONS)
print("Cam:", CAMERA_INDEX)
print("Sens:", SENS)
print("Stabilize:", STABILIZE)
print("DwellTime", DWELL_CLICK_SEC)


overlay_root = tk.Tk()
overlay_root.withdraw()
cursor_overlay = CursorOverlay(overlay_root)

# =========================================
# ==========   CONFIGURACIÓN   ============
# =========================================

MODE_RELATIVE = True

SENS_MULT = 1.0
SENS_STEP = 1.12

REL_GAIN_X = 16500
REL_GAIN_Y = 10560

SENS_LEVELS = ["baja", "media-baja", "media", "media-alta", "alta"]
CURRENT_SENS_INDEX = SENS_LEVELS.index(SENS) if SENS in SENS_LEVELS else 2
SENS_LEVELS = ["baja", "media-baja", "media", "media-alta", "alta"]
CURRENT_SENS_INDEX = SENS_LEVELS.index(SENS) if SENS in SENS_LEVELS else 2

def apply_sensitivity(level_name):
    global REL_GAIN_X, REL_GAIN_Y

    SENS_PRESETS = {
        "baja":       (5000,  5000),
        "media-baja": (8000,  8000),
        "media":      (12000, 12000),
        "media-alta": (16000, 16000),
        "alta":       (22000, 22000),
    }

    base_x, base_y = SENS_PRESETS[level_name]

    REL_GAIN_X = base_x * SENS_MULT
    REL_GAIN_Y = (base_y * 1.35) * SENS_MULT

    print(
        f"[SENS] {level_name} x{SENS_MULT:.2f} -> "
        f"X={REL_GAIN_X:.0f} Y={REL_GAIN_Y:.0f}"
    )

apply_sensitivity(SENS_LEVELS[CURRENT_SENS_INDEX])

ABS_GAIN_X = 2.0
ABS_GAIN_Y = 1.8

ALPHA_NOSE = 0.72
MAX_PIXELS_PER_FRAME = 220

# ✅ Zona muerta en píxeles (tuya)
DEAD_ZONE = 1

# ✅ Zona muerta en coordenadas normalizadas (anti jitter real)
# Valores típicos: 0.0015–0.006
NOSE_DEADZONE_NORM = 0.0008 if STABILIZE else 0.0

# ✅ “Leaky integrator”: atenúa micro-drift del modo relativo
LEAK = 0.015 if STABILIZE else 0.0
# LEAK = 0.06 if STABILIZE else 0.0  # 0–0.15

# Boca / clicks
SLOW_START_RATIO = 0.035
CLICK_ARM_RATIO  = 0.055
MIN_SPEED_SCALE_AT_MAX = 0.05
CLICK_SHORT_SEC = 0.15
CLICK_LONG_SEC  = 0.50
CLICK_COOLDOWN_SEC = 0.40
# Drag (boca mantenida)
DRAG_START_SEC = 0.35   # tiempo con boca abierta para activar "click sostenido"

DBLCLICK_INTERVAL_SEC = 0.12
SUSPEND_MOVE_SEC = 0.30

pyautogui.FAILSAFE = True
SAFE_MARGIN = 8
SCREEN_W, SCREEN_H = pyautogui.size()

suspend_move_until = 0.0

SHOW_OVERLAY = True

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def clamp_with_margin(v, lo, hi, m=SAFE_MARGIN):
    return max(lo+m, min(hi-m, v))

# Auto click por permanencia
DWELL_ENABLED = True
DWELL_STILL_RADIUS_PX = 20
DWELL_POST_CLICK_DELAY = 1.0

last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()
dwell_progress = 0.0

ZOOM_TRIGGER_SPEED = 0.20      # activa zoom cuando speed baja de esto
ZOOM_EXIT_SPEED = 0.80         # se apaga recién cuando speed sube bastante
zoom_active = False

ZOOM_MIN_ON_SEC = 1.5          # una vez prendido, queda al menos este tiempo
zoom_on_since = 0.0

DEBUG_CONSOLE = True
DEBUG_PRINT_EVERY_SEC = 0.30
last_debug_print = 0.0

RUNNING = True
PAUSED = False


cursor_speed = 0
prev_cursor_pos = pyautogui.position()
prev_speed_time = time.time()




# =========================================
# ========== DWELL CLICK CONFIG ===========
# =========================================
DWELL_ENABLED = True
DWELL_STILL_RADIUS_PX = 20
DWELL_POST_CLICK_DELAY = 1.0

last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()
dwell_progress = 0.0




# =========================================
# ==========  One Euro Filter  ============
# =========================================
# Suaviza temblores sin agregar mucha latencia cuando el movimiento es intencional

def _alpha(cutoff, dt):
    r = 2.0 * math.pi * cutoff * dt
    return r / (r + 1.0)

class OneEuroFilter1D:
    def __init__(self, min_cutoff=1.2, beta=0.03, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def apply(self, x, t):
        if self.t_prev is None:
            self.t_prev = t
            self.x_prev = x
            self.dx_prev = 0.0
            return x

        dt = max(1e-6, t - self.t_prev)
        self.t_prev = t

        # derivada
        dx = (x - self.x_prev) / dt
        a_d = _alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        self.dx_prev = dx_hat

        # cutoff dinámico
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = _alpha(cutoff, dt)

        x_hat = a * x + (1 - a) * self.x_prev
        self.x_prev = x_hat
        return x_hat

# Filtros para nariz (x,y) en normalizado 0..1
# Valores recomendados:
# - min_cutoff más alto = más estable, pero más "pesado"
# - beta más alto = reacciona mejor a movimientos rápidos (menos lag)
NOSE_FILTER_X = OneEuroFilter1D(min_cutoff=3.0, beta=0.25, d_cutoff=1.0)
NOSE_FILTER_Y = OneEuroFilter1D(min_cutoff=3.0, beta=0.25, d_cutoff=1.0)


# - Círculo de AutoClick

def draw_dwell_ring(frame, center, progress, radius=28, thickness=4):
    """
    Dibuja un anillo de progreso en sentido horario.
    progress: 0.0 a 1.0
    """
    x, y = center

    # círculo base gris
    cv2.circle(frame, (x, y), radius, (80, 80, 80), thickness)

    # progreso
    if progress > 0:
        end_angle = int(360 * progress)
        cv2.ellipse(
            frame,
            (x, y),
            (radius, radius),
            -90,          # arranca arriba
            0,
            end_angle,
            (0, 255, 255),
            thickness
        )


def draw_eye_bar(frame, x, y, width, height, value, closed_thr, open_ear, label, active=False):
    # fondo
    cv2.rectangle(frame, (x, y), (x + width, y + height), (40, 40, 40), -1)

    # valor normalizado respecto al ojo abierto calibrado
    denom = max(open_ear, 1e-6)
    frac = max(0.0, min(1.0, value / denom))
    fill_w = int(width * frac)

    color = (0, 255, 255) if active else (180, 220, 255)
    cv2.rectangle(frame, (x, y), (x + fill_w, y + height), color, -1)

    # marca de cerrado
    thr_frac = max(0.0, min(1.0, closed_thr / denom))
    thr_x = x + int(width * thr_frac)
    cv2.line(frame, (thr_x, y - 3), (thr_x, y + height + 3), (0, 100, 255), 2)

    cv2.putText(
        frame,
        f"{label}: {value:.3f}",
        (x, y - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 220, 120),
        2
    )

# =========================================
# ==========    CLICK FUNCTIONS   =========
# =========================================

def do_click():
    global suspend_move_until

    x, y = pyautogui.position()
    suspend_move_until = time.time() + SUSPEND_MOVE_SEC

    try:
        cursor_overlay.hide()
    except:
        pass

    time.sleep(0.03)
    pyautogui.click(x=x, y=y, button="left")
    time.sleep(0.03)

    try:
        cursor_overlay.show()
    except:
        pass

def do_right_click():
    global suspend_move_until

    x, y = pyautogui.position()
    suspend_move_until = time.time() + SUSPEND_MOVE_SEC

    try:
        cursor_overlay.hide()
    except:
        pass

    time.sleep(0.03)
    pyautogui.click(x=x, y=y, button="right")
    time.sleep(0.03)

    try:
        cursor_overlay.show()
    except:
        pass

def execute_action(action_name):
    if action_name == "Nada":
        return

    elif action_name == "Click izquierdo":
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

def do_double_click():
    global suspend_move_until

    x, y = pyautogui.position()
    suspend_move_until = time.time() + SUSPEND_MOVE_SEC

    try:
        cursor_overlay.hide()
    except:
        pass

    time.sleep(0.03)
    pyautogui.click(x=x, y=y)
    time.sleep(DBLCLICK_INTERVAL_SEC)
    pyautogui.click(x=x, y=y)
    time.sleep(0.03)

    try:
        cursor_overlay.show()
    except:
        pass

# =========================================
# ==========   WINDOWS MAGNIFIER ==========
# =========================================

last_zoom_toggle_time = 0.0
ZOOM_TOGGLE_COOLDOWN = 0.8   # evita ON/OFF muy rápido

VK_LWIN = 0x5B
VK_ESCAPE = 0x1B
VK_ADD_NUMPAD = 0x6B   # tecla + del keypad numérico

KEYEVENTF_KEYUP = 0x0002

def press_vk(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

def hotkey_zoom_open():
    # Win + Numpad +
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_ADD_NUMPAD, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_ADD_NUMPAD, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

def hotkey_zoom_close():
    # Win + Esc
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

def zoom_in_windows():
    global zoom_active, last_zoom_toggle_time, zoom_on_since

    now = time.time()
    if zoom_active:
        return
    if now - last_zoom_toggle_time < ZOOM_TOGGLE_COOLDOWN:
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
    global zoom_active, last_zoom_toggle_time, zoom_on_since

    now = time.time()
    if not zoom_active:
        return
    if now - last_zoom_toggle_time < ZOOM_TOGGLE_COOLDOWN:
        return

    # no apagar demasiado pronto
    if (now - zoom_on_since) < ZOOM_MIN_ON_SEC:
        return

    try:
        hotkey_zoom_close()
        zoom_active = False
        last_zoom_toggle_time = now
        print("[ZOOM] OFF")
    except Exception as e:
        print("[ZOOM] No se pudo desactivar:", e)

# =========================================
# ========== DRAG FUNCTIONS ===============
# =========================================

drag_active = False
drag_started_at = None

def start_drag():
    global drag_active
    if not drag_active:
        pyautogui.mouseDown(button="left")
        drag_active = True
        print("DRAG START")

def stop_drag():
    global drag_active, last_move_time, dwell_progress, last_cursor_pos

    if drag_active:
        pyautogui.mouseUp(button="left")
        drag_active = False
        print("DRAG STOP")

        # resetear dwell correctamente
        last_move_time = time.time()
        last_cursor_pos = pyautogui.position()
        dwell_progress = 0.0

def center_mouse():
    global cur_x, cur_y
    global nose_prev_fx, nose_prev_fy
    global last_move_time, last_cursor_pos, dwell_progress
    global suspend_move_until

    cur_x = SCREEN_W // 2
    cur_y = SCREEN_H // 2

    # mover cursor real al centro
    pyautogui.moveTo(cur_x, cur_y, duration=0.05)

    # reset de filtros / historial para evitar salto
    nose_prev_fx = None
    nose_prev_fy = None
    NOSE_FILTER_X.reset()
    NOSE_FILTER_Y.reset()

    # reset dwell
    last_move_time = time.time()
    last_cursor_pos = pyautogui.position()
    dwell_progress = 0.0

    # pequeño cooldown para no clickear o saltar enseguida
    suspend_move_until = time.time() + 0.15

    print("[HOTKEY] Mouse centrado")

# =========================================
# ==========  BOCA Y OJOS (EAR)  ==========
# =========================================

def mouth_open_ratio(lm):
    p_up = lm[13]; p_dn = lm[14]
    p_top = lm[10]; p_bot = lm[152]
    dy_mouth = np.hypot(p_up.x - p_dn.x, p_up.y - p_dn.y)
    dy_face  = np.hypot(p_top.x - p_bot.x, p_top.y - p_bot.y)
    return dy_mouth / dy_face if dy_face > 1e-6 else 0.0

LEFT_EYE_IDX  = [33,160,158,133,153,144]
RIGHT_EYE_IDX = [362,385,387,263,373,380]

def eye_aspect_ratio(lm, idxs):
    p = [lm[i] for i in idxs]
    v1 = np.hypot(p[1].x - p[5].x, p[1].y - p[5].y)
    v2 = np.hypot(p[2].x - p[4].x, p[2].y - p[4].y)
    h  = np.hypot(p[0].x - p[3].x, p[0].y - p[3].y)
    return (v1 + v2) / (2*h) if h > 1e-6 else 0.0

def calibrate_wink_thresholds(cap, face_mesh):
    global LEFT_EYE_OPEN_EAR, RIGHT_EYE_OPEN_EAR
    global LEFT_EYE_CLOSED_THR, RIGHT_EYE_CLOSED_THR
    global LEFT_EYE_OPEN_THR, RIGHT_EYE_OPEN_THR

    print("[CAL] Calibrando ojos abiertos... mirá el círculo del centro y mantené los ojos relajados.")

    start_time = time.time()
    samples_left = []
    samples_right = []

    while time.time() - start_time < WINK_CALIBRATION_SEC:
        ok, frame = cap.read()
        if not ok:
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        elapsed = time.time() - start_time
        remaining = max(0.0, WINK_CALIBRATION_SEC - elapsed)
        progress = min(1.0, elapsed / WINK_CALIBRATION_SEC)

        h, w = frame.shape[:2]
        cx = w // 2
        cy = h // 2
        r = 40

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark

            left_ear = eye_aspect_ratio(lm, LEFT_EYE_IDX)
            right_ear = eye_aspect_ratio(lm, RIGHT_EYE_IDX)

            if 0.05 < left_ear < 0.80:
                samples_left.append(left_ear)
            if 0.05 < right_ear < 0.80:
                samples_right.append(right_ear)

            cv2.putText(frame, "CALIBRANDO OJOS ABIERTOS", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            cv2.putText(frame, f"Tiempo restante: {remaining:.1f}s", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 200), 2)

            cv2.putText(frame, f"L EAR: {left_ear:.3f}  R EAR: {right_ear:.3f}", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)
        else:
            cv2.putText(frame, "No detecto la cara...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 255), 2)

        # círculo guía central
        cv2.circle(frame, (cx, cy), r, (120, 120, 120), 3)

        # progreso de calibración
        end_angle = int(360 * progress)
        cv2.ellipse(
            frame,
            (cx, cy),
            (r, r),
            -90,
            0,
            end_angle,
            (0, 255, 255),
            4
        )

        # punto central
        cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        cv2.putText(frame, "Mira este punto", (cx - 70, cy + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Calibracion de Guiño", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyWindow("Calibracion de Guiño")

    if len(samples_left) < 10 or len(samples_right) < 10:
        print("[CAL] No se pudo calibrar bien. Se mantienen umbrales por defecto.")
        return

    LEFT_EYE_OPEN_EAR = float(np.median(samples_left))
    RIGHT_EYE_OPEN_EAR = float(np.median(samples_right))

    recompute_wink_thresholds()

    print("[CAL] Calibración completada:")
    print(f"      LEFT open={LEFT_EYE_OPEN_EAR:.3f} closed_thr={LEFT_EYE_CLOSED_THR:.3f} open_thr={LEFT_EYE_OPEN_THR:.3f}")
    print(f"      RIGHT open={RIGHT_EYE_OPEN_EAR:.3f} closed_thr={RIGHT_EYE_CLOSED_THR:.3f} open_thr={RIGHT_EYE_OPEN_THR:.3f}")


# ===== Calibración de guiño =====
WINK_COOLDOWN = 0.45
WINK_CALIBRATION_SEC = 3.0

LEFT_EYE_OPEN_EAR = 0.30
RIGHT_EYE_OPEN_EAR = 0.30

# Sensibilidad ajustable en tiempo real
# más alto = más sensible (requiere menos cerrar)
WINK_CLOSED_FACTOR = 0.92
WINK_OPEN_FACTOR = 0.85

LEFT_EYE_CLOSED_THR = 0.22
RIGHT_EYE_CLOSED_THR = 0.22
LEFT_EYE_OPEN_THR = 0.26
RIGHT_EYE_OPEN_THR = 0.26

last_wink_time = 0.0
last_left_ear = 0.0
last_right_ear = 0.0

left_ear_vis = 0.0
right_ear_vis = 0.0
EAR_VIS_ALPHA = 0.35

# Estados boca
mouth_ratio_vis = 0.0
mouth_open_prev = False
mouth_open_start = None
last_click_time = 0.0
mouth_click_armed = False

drag_active = False
drag_started_at = None


def recompute_wink_thresholds():
    global LEFT_EYE_CLOSED_THR, RIGHT_EYE_CLOSED_THR
    global LEFT_EYE_OPEN_THR, RIGHT_EYE_OPEN_THR

    LEFT_EYE_CLOSED_THR = LEFT_EYE_OPEN_EAR * WINK_CLOSED_FACTOR
    RIGHT_EYE_CLOSED_THR = RIGHT_EYE_OPEN_EAR * WINK_CLOSED_FACTOR

    LEFT_EYE_OPEN_THR = LEFT_EYE_OPEN_EAR * WINK_OPEN_FACTOR
    RIGHT_EYE_OPEN_THR = RIGHT_EYE_OPEN_EAR * WINK_OPEN_FACTOR

    print("[WINK] Sensibilidad actualizada:")
    print(f"       closed_factor={WINK_CLOSED_FACTOR:.2f} open_factor={WINK_OPEN_FACTOR:.2f}")
    print(f"       L closed<{LEFT_EYE_CLOSED_THR:.3f} open>{LEFT_EYE_OPEN_THR:.3f}")
    print(f"       R closed<{RIGHT_EYE_CLOSED_THR:.3f} open>{RIGHT_EYE_OPEN_THR:.3f}")

def detect_gesture(lm, ratio_raw, now):
    global mouth_open_prev, mouth_open_start, mouth_click_armed
    global last_click_time, last_wink_time
    global last_left_ear, last_right_ear

    # ===== Boca =====
    opened = (ratio_raw >= SLOW_START_RATIO)

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

    # ===== Ojos =====
    left = eye_aspect_ratio(lm, LEFT_EYE_IDX)
    right = eye_aspect_ratio(lm, RIGHT_EYE_IDX)
    last_left_ear = left
    last_right_ear = right

    left_closed = left < LEFT_EYE_CLOSED_THR
    right_closed = right < RIGHT_EYE_CLOSED_THR
    left_open = left > LEFT_EYE_OPEN_THR
    right_open = right > RIGHT_EYE_OPEN_THR

    if left_closed and right_open:
        if (now - last_wink_time) > WINK_COOLDOWN:
            last_wink_time = now
            return "wink_left"

    if right_closed and left_open:
        if (now - last_wink_time) > WINK_COOLDOWN:
            last_wink_time = now
            return "wink_right"

    return None

# =========================================
# ==========     CÁMARA WINDOWS     ========
# =========================================

def open_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir cámara {index}")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print(f"[INFO] Cámara abierta en índice {index}")
    return cap

# =========================================
# ==========   GLOBAL HOTKEYS   ===========
# =========================================
def on_press(key):
    global RUNNING, PAUSED, drag_active, DWELL_ENABLED, dwell_progress
    global WINK_CLOSED_FACTOR, WINK_OPEN_FACTOR
    global CURRENT_SENS_INDEX, SENS_MULT

    try:
        if key == keyboard.Key.f12:
            print("[HOTKEY] F12 -> salir")
            if zoom_active:
                zoom_out_windows()
            RUNNING = False

        elif key == keyboard.Key.f11:
            PAUSED = not PAUSED
            print("[HOTKEY] F11 -> pausa", PAUSED)

        elif key == keyboard.Key.f10:
            if drag_active:
                stop_drag()
                print("[HOTKEY] DRAG OFF")
            else:
                start_drag()
                print("[HOTKEY] DRAG ON")

        elif key == keyboard.Key.f9:
            print("[HOTKEY] F9 -> recalibrar guiño")
            calibrate_wink_thresholds(cap, face_mesh)

        elif key == keyboard.Key.f8:
            DWELL_ENABLED = not DWELL_ENABLED
            print(f"[HOTKEY] F8 -> autoclick {'ON' if DWELL_ENABLED else 'OFF'}")
            dwell_progress = 0.0
            if DWELL_ENABLED:
                cursor_overlay.show()
            else:
                cursor_overlay.hide()

        elif key == keyboard.Key.f7:
            center_mouse()

        elif key == keyboard.Key.f5:
            WINK_CLOSED_FACTOR = min(0.98, WINK_CLOSED_FACTOR + 0.02)
            recompute_wink_thresholds()
            print("[HOTKEY] F5 -> guiño más sensible")

        elif key == keyboard.Key.f6:
            WINK_CLOSED_FACTOR = max(0.70, WINK_CLOSED_FACTOR - 0.02)
            recompute_wink_thresholds()
            print("[HOTKEY] F6 -> guiño menos sensible")


        elif key == keyboard.Key.f3:
            SENS_MULT /= SENS_STEP
            apply_sensitivity(SENS_LEVELS[CURRENT_SENS_INDEX])
            print(f"[HOTKEY] F3 -> sensibilidad x{SENS_MULT:.2f}")

        elif key == keyboard.Key.f4:
            SENS_MULT *= SENS_STEP
            apply_sensitivity(SENS_LEVELS[CURRENT_SENS_INDEX])
            print(f"[HOTKEY] F4 -> sensibilidad x{SENS_MULT:.2f}")

    except Exception:
        pass

hotkey_listener = keyboard.Listener(on_press=on_press)
hotkey_listener.start()



# =========================================
# ==========     INICIALIZACIÓN   =========
# =========================================

cap = open_camera(CAMERA_INDEX)
if cap is None:
    raise SystemExit("No se pudo iniciar la cámara.")

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)

calibrate_wink_thresholds(cap, face_mesh)

cur_x, cur_y = SCREEN_W // 2, SCREEN_H // 2

# relativo: guardamos última nariz filtrada para delta
nose_prev_fx = None
nose_prev_fy = None

# para que al comenzar no “salte”
NOSE_FILTER_X.reset()
NOSE_FILTER_Y.reset()

dwell_progress = 0.0
mouth_open_now = False
speed = 1.0

# DWELL CLICK
DWELL_ENABLED = False
DWELL_STILL_RADIUS_PX = 20
DWELL_POST_CLICK_DELAY = 1.0

last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()
dwell_progress = 0.0

WINDOW_CENTERED = False

# =========================================
# ==========     KALMAN FILTER   ==========
# =========================================

kalman_x = cv2.KalmanFilter(2, 1)
kalman_y = cv2.KalmanFilter(2, 1)

for kf in [kalman_x, kalman_y]:

    # estado: [posición, velocidad]
    kf.transitionMatrix = np.array([
        [1, 1],
        [0, 1]
    ], np.float32)

    kf.measurementMatrix = np.array([
        [1, 0]
    ], np.float32)

    kf.processNoiseCov = np.array([
        [1e-4, 0],
        [0, 1e-3]
    ], np.float32)

    kf.measurementNoiseCov = np.array([
        [1e-2]
    ], np.float32)

    kf.errorCovPost = np.eye(2, dtype=np.float32)

    kf.statePost = np.zeros((2,1), np.float32)



# =========================================
# ==========     LOOP PRINCIPAL    =========
# =========================================

while RUNNING:
    ok, frame = cap.read()
    if not ok:
        continue
    if PAUSED:
        time.sleep(0.05)
        continue
    
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)
    now = time.time()

    status_text = "Face: NOT FOUND"

    if res.multi_face_landmarks:
        lm = res.multi_face_landmarks[0].landmark
        control_point = lm[MOVEMENT_LANDMARK_INDEX]

        # Boca suavizada (solo visual y freno)
        ratio_raw = mouth_open_ratio(lm)
        mouth_ratio_vis = (1 - 0.5)*mouth_ratio_vis + 0.5*ratio_raw
        mouth_open_now = ratio_raw >= SLOW_START_RATIO

        # Detectar gesto (nuevo sistema)
        gesture = detect_gesture(lm, ratio_raw, now)
            
        # suavizado visual de ojos (lo mantenés igual)
        left_ear_vis = (1 - EAR_VIS_ALPHA) * left_ear_vis + EAR_VIS_ALPHA * last_left_ear
        right_ear_vis = (1 - EAR_VIS_ALPHA) * right_ear_vis + EAR_VIS_ALPHA * last_right_ear

        # Ejecutar acción según configuración
        if gesture is not None:
            action_name = GESTURE_ACTIONS.get(gesture, "Nada")

            execute_action(action_name)

            # reset de filtros para evitar “rebote” post-click
            NOSE_FILTER_X.reset()
            NOSE_FILTER_Y.reset()
            nose_prev_fx = None
            nose_prev_fy = None

        # -------- Nariz: filtro anti temblor --------
        nx, ny = float(control_point.x), float(control_point.y)

        if STABILIZE:
            fx_raw = NOSE_FILTER_X.apply(nx, now)
            fy_raw = NOSE_FILTER_Y.apply(ny, now)

            # predict
            pred_x = kalman_x.predict()
            pred_y = kalman_y.predict()

            # correct
            meas_x = np.array([[np.float32(fx_raw)]])
            meas_y = np.array([[np.float32(fy_raw)]])

            corr_x = kalman_x.correct(meas_x)
            corr_y = kalman_y.correct(meas_y)

            fx = float(corr_x[0])
            fy = float(corr_y[0])
        else:
            # solo EMA liviano
            if nose_prev_fx is None:
                fx, fy = nx, ny
            else:
                fx = (1-ALPHA_NOSE)*nose_prev_fx + ALPHA_NOSE*nx
                fy = (1-ALPHA_NOSE)*nose_prev_fy + ALPHA_NOSE*ny

        # velocidad según boca (freno progresivo)
        if ratio_raw <= SLOW_START_RATIO:
            speed = 1.0
        elif ratio_raw >= CLICK_ARM_RATIO:
            speed = MIN_SPEED_SCALE_AT_MAX
        else:
            t = (ratio_raw - SLOW_START_RATIO) / (CLICK_ARM_RATIO - SLOW_START_RATIO)
            speed = 1.0 - t*t*(1 - MIN_SPEED_SCALE_AT_MAX)

        # =========================================
        # ==========   AUTO ZOOM WINDOWS  =========
        # =========================================
        if AUTO_ZOOM_ENABLED:

            if cursor_speed < 40 and not zoom_active:
                zoom_in_windows()

            elif cursor_speed > 80 and zoom_active:
                zoom_out_windows()
        # -------- Movimiento RELATIVO --------
        if MODE_RELATIVE:
            if nose_prev_fx is None:
                nose_prev_fx, nose_prev_fy = fx, fy

            dnx = fx - nose_prev_fx
            dny = fy - nose_prev_fy

            # Guardar última posición filtrada
            nose_prev_fx, nose_prev_fy = fx, fy

            # =========================================
            # ========== MOVIMIENTO MÁS SOFT ==========
            # =========================================

            movement_mag = np.hypot(dnx, dny)

            # Zona muerta real anti-jitter
            if abs(dnx) < NOSE_DEADZONE_NORM:
                dnx = 0.0
            if abs(dny) < NOSE_DEADZONE_NORM:
                dny = 0.0

            # Micro drift extra
            if abs(dnx) < 0.0015:
                dnx *= 0.2
            if abs(dny) < 0.0015:
                dny *= 0.2

            # Leak / fricción
            if LEAK > 0:
                dnx *= (1.0 - LEAK)
                dny *= (1.0 - LEAK)

            # Modo precisión automático cuando el movimiento es chico
            local_speed = speed
            if movement_mag < 0.004:
                local_speed *= 0.45

            # Curva tipo Camera Mouse, pero sin matar el movimiento
            CURVE_POWER = 1.15       # 1.0 lineal / 1.25 suave / 1.5 más pesado
            SOFT_ZONE = 0.000025      # zona muerta chica
            REF_DELTA = 0.012        # referencia de movimiento normal
            MICRO_GAIN = 0.75        # fuerza en movimientos pequeños

            def curved_motion(v):
                sign = 1 if v >= 0 else -1
                mag = abs(v)

                if mag < SOFT_ZONE:
                    return 0.0

                mag = mag - SOFT_ZONE

                # Normalizamos para que la curva no destruya el movimiento
                norm = min(1.0, mag / REF_DELTA)

                curved = (norm ** CURVE_POWER) * REF_DELTA

                # Los movimientos pequeños no quedan muertos
                if mag < 0.004:
                    curved *= MICRO_GAIN

                return sign * curved

            mx = curved_motion(dnx)
            my = curved_motion(dny)

            # X un poco más sensible, Y un poco más suave
            dx = mx * (REL_GAIN_X * local_speed) * 4.0
            dy = my * (REL_GAIN_Y * local_speed) * 3.2

            movement_mag = np.hypot(dnx, dny)

            accel = 1.0 + min(2.5, movement_mag * 120)

            dx *= accel
            dy *= accel

            target_x = cur_x + dx
            target_y = cur_y + dy

            # límite de velocidad más suave
            dist = np.hypot(target_x - cur_x, target_y - cur_y)
            vmax = max(20, int(MAX_PIXELS_PER_FRAME * speed * 2.8))

            if dist > vmax and dist > 0:
                k = vmax / dist
                target_x = cur_x + (target_x - cur_x) * k
                target_y = cur_y + (target_y - cur_y) * k

            # mover mouse
            if drag_active or (time.time() >= suspend_move_until):
                target_x = int(clamp_with_margin(target_x, 0, SCREEN_W - 1))
                target_y = int(clamp_with_margin(target_y, 0, SCREEN_H - 1))

                if abs(target_x - cur_x) >= DEAD_ZONE or abs(target_y - cur_y) >= DEAD_ZONE:
                    pyautogui.moveTo(target_x, target_y, duration=0.01)
                    cur_x, cur_y = target_x, target_y

                    now_pos = pyautogui.position()
                    dt = time.time() - prev_speed_time

                    if dt > 0:
                        moved_dist = np.hypot(
                            now_pos[0] - prev_cursor_pos[0],
                            now_pos[1] - prev_cursor_pos[1]
                        )
                        cursor_speed = moved_dist / dt

                    prev_cursor_pos = now_pos
                    prev_speed_time = time.time()

            # =========================================
            # ========== DWELL CLICK (AUTO) ===========
            # =========================================
            if DWELL_ENABLED:
                current_cursor_pos = pyautogui.position()

                moved_px = np.hypot(
                    current_cursor_pos[0] - last_cursor_pos[0],
                    current_cursor_pos[1] - last_cursor_pos[1]
                )

                if moved_px > DWELL_STILL_RADIUS_PX:
                    last_move_time = now
                    last_cursor_pos = current_cursor_pos
                    dwell_progress = 0.0
                else:
                    if (not drag_active) and (now >= suspend_move_until):
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

                                NOSE_FILTER_X.reset()
                                NOSE_FILTER_Y.reset()
                                nose_prev_fx = None
                                nose_prev_fy = None
                    else:
                        dwell_progress = 0.0
            else:
                dwell_progress = 0.0

                
        status_text = (
            f"Face: OK | mode={GESTURE_ACTIONS if 'GESTURE_ACTIONS' in globals() else 'legacy'} | "
            f"sens={SENS_LEVELS[CURRENT_SENS_INDEX]} x{SENS_MULT:.2f} | "
            f"speed={speed:.2f} | "
            f"cursor={cursor_speed:.1f} | "
            f"drag={'ON' if drag_active else 'OFF'} | "
            f"zoom={'ON' if zoom_active else 'OFF'} | "
            f"mouth={'OPEN' if mouth_open_now else 'CLOSED'} | "
            f"stab={'ON' if STABILIZE else 'OFF'}"
        )


        # -------- Overlay --------
        if SHOW_OVERLAY:
            h, w = frame.shape[:2]
            cx = int(clamp(fx, 0, 1) * w)
            cy = int(clamp(fy, 0, 1) * h)
            cv2.circle(frame, (cx, cy), 5, (0,255,0), -1)

            # Barra boca
            cv2.rectangle(frame, (10, 50), (260, 75), (40, 40, 40), -1)

            left_active = (
                GESTURE_ACTIONS.get("wink_left", "Nada") != "Nada"
                and last_left_ear < LEFT_EYE_CLOSED_THR
            )

            right_active = (
                GESTURE_ACTIONS.get("wink_right", "Nada") != "Nada"
                and last_right_ear < RIGHT_EYE_CLOSED_THR
            )

            if GESTURE_ACTIONS.get("wink_left") != "Nada":
                draw_eye_bar(
                    frame, 10, 235, 220, 18,
                    left_ear_vis, LEFT_EYE_CLOSED_THR, LEFT_EYE_OPEN_EAR,
                    "L EAR", active=left_active
                )

            if GESTURE_ACTIONS.get("wink_right") != "Nada":
                draw_eye_bar(
                    frame, 10, 285, 220, 18,
                    right_ear_vis, RIGHT_EYE_CLOSED_THR, RIGHT_EYE_OPEN_EAR,
                    "R EAR", active=right_active
                )

            cv2.putText(
                frame,
                f"Wink sens: closed_factor={WINK_CLOSED_FACTOR:.2f} open_factor={WINK_OPEN_FACTOR:.2f}",
                (10, 335),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 220, 120),
                2
            )

            cv2.namedWindow("Face Mouse", cv2.WINDOW_NORMAL)

            cv2.putText(frame, f"Boca={GESTURE_ACTIONS['mouth']} | LI={GESTURE_ACTIONS['wink_left']} | LD={GESTURE_ACTIONS['wink_right']}",
            (10, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 220, 120), 2)


            # llenado
            bar_max = 240
            bl = int(min(bar_max, bar_max * (mouth_ratio_vis / max(CLICK_ARM_RATIO, 0.001))))
            cv2.rectangle(frame, (10, 50), (10 + bl, 75), (0, 255, 255), -1)

            # marcas de umbral
            slow_x = 10 + int(bar_max * (SLOW_START_RATIO / max(CLICK_ARM_RATIO, 0.001)))
            arm_x  = 10 + int(bar_max * (CLICK_ARM_RATIO / max(CLICK_ARM_RATIO, 0.001)))
            cv2.line(frame, (slow_x, 45), (slow_x, 80), (180, 180, 255), 2)
            cv2.line(frame, (arm_x, 45), (arm_x, 80), (0, 180, 255), 2)

            cv2.putText(
                frame,
                f"MOUTH: {'OPEN' if mouth_open_now else 'CLOSED'}  ratio={ratio_raw:.3f}",
                (10, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 255, 200),
                2
            )

            cv2.putText(frame, status_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

            cv2.putText(frame, f"EAR L:{last_left_ear:.3f} R:{last_right_ear:.3f}",
                        (10,150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,200,0), 2)

            cv2.putText(frame, f"DeadzoneNorm: {NOSE_DEADZONE_NORM:.4f}  Leak: {LEAK:.2f}",
                        (10,180), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,255,180), 2)
            
            cv2.putText(frame,f"Dwell: {'ON' if DWELL_ENABLED else 'OFF'}  t={DWELL_CLICK_SEC:.1f}s  prog={dwell_progress:.2f}",
                    (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,255,255), 2)

        if DEBUG_CONSOLE and (now - last_debug_print) >= DEBUG_PRINT_EVERY_SEC:
            print(
                f"[STATE] speed={speed:.2f} | "
                f"cursor_speed={cursor_speed:.2f} | "
                f"drag={'ON' if drag_active else 'OFF'} | "
                f"zoom={'ON' if zoom_active else 'OFF'} | "
                f"mouth={'OPEN' if mouth_open_now else 'CLOSED'} | "
                f"ratio={ratio_raw:.3f} | "
                f"dwell={dwell_progress:.2f} | "
                f"stab={'ON' if STABILIZE else 'OFF'}"
            )
            last_debug_print = now

        cursor_pos = pyautogui.position()
        test_progress = dwell_progress if DWELL_ENABLED else 0.25
        if DWELL_ENABLED:
            cursor_overlay.show()
            cursor_overlay.update_overlay(cursor_pos[0], cursor_pos[1], dwell_progress)
        else:
            cursor_overlay.hide()   
    
    cv2.imshow("Face Mouse", frame)

    if not WINDOW_CENTERED:
        win_w = 1100
        win_h = 700
        screen_w, screen_h = pyautogui.size()
        x = int((screen_w - win_w) / 2)
        y = int((screen_h - win_h) / 2)

        cv2.resizeWindow("Face Mouse", win_w, win_h)
        cv2.moveWindow("Face Mouse", x, y)

        WINDOW_CENTERED = True

    if cv2.getWindowProperty("Face Mouse", cv2.WND_PROP_VISIBLE) < 1:
        RUNNING = False
        break
    

    k = cv2.waitKey(1)

    if k == ord('q'):
        if zoom_active:
            zoom_out_windows()
        break
    elif k == ord('c'):
        center_mouse()  

try:
    if zoom_active:
        zoom_out_windows()
except:
    pass

try:
    hotkey_listener.stop()
except:
    pass

try:
    face_mesh.close()
except:
    pass

try:
    cursor_overlay.destroy()
except:
    pass

try:
    face_mesh.close()
except Exception:
    pass

cap.release()
cv2.destroyAllWindows()



#hacer burbuja flotante que se pueda cambiar click o doble click en el momento