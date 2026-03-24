# # -*- coding: utf-8 -*-

# import os
# os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
# os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

# import time
# import cv2
# import mediapipe as mp
# import numpy as np
# import pyautogui
# import tkinter as tk
# from tkinter import ttk
# from collections import deque

# # =========================================
# # ==========   MENU GRAFICO GUI   =========
# # =========================================

# def show_gui_menu():
#     window = tk.Tk()
#     window.title("Configuración FaceMouse")
#     window.geometry("420x420")
#     window.resizable(False, False)

#     click_mode_var = tk.StringVar(value="mouth")
#     cam_index_var = tk.StringVar(value="0")
#     sensitivity_var = tk.StringVar(value="media")

#     title = tk.Label(window, text="FACE MOUSE CONTROL", font=("Arial", 16, "bold"))
#     title.pack(pady=10)

#     frame_click = tk.LabelFrame(window, text="Modo de Click")
#     frame_click.pack(fill="x", padx=20, pady=10)

#     tk.Radiobutton(frame_click, text="Boca (click / doble click)",
#                    variable=click_mode_var, value="mouth").pack(anchor="w", padx=10)

#     tk.Radiobutton(frame_click, text="Guiño izquierdo (click)",
#                    variable=click_mode_var, value="wink_left").pack(anchor="w", padx=10)

#     tk.Radiobutton(frame_click, text="Guiño derecho (click)",
#                    variable=click_mode_var, value="wink_right").pack(anchor="w", padx=10)

#     frame_cam = tk.LabelFrame(window, text="Índice de cámara")
#     frame_cam.pack(fill="x", padx=20, pady=10)

#     ttk.Combobox(frame_cam, textvariable=cam_index_var,
#                  values=["0", "1", "2", "3", "4"]).pack(padx=10, pady=5)

#     frame_sens = tk.LabelFrame(window, text="Sensibilidad")
#     frame_sens.pack(fill="x", padx=20, pady=10)

#     ttk.Combobox(frame_sens, textvariable=sensitivity_var,
#                  values=["baja","media-baja", "media", "media-alta", "alta"]).pack(padx=10, pady=5)

#     def start():
#         window.destroy()

#     tk.Button(window, text="COMENZAR", font=("Arial", 14, "bold"),
#               command=start, bg="#4CAF50", fg="white").pack(pady=20)

#     window.mainloop()
#     return click_mode_var.get(), int(cam_index_var.get()), sensitivity_var.get()

# CLICK_MODE, CAMERA_INDEX, SENS = show_gui_menu()

# print("Modo:", CLICK_MODE)
# print("Cam:", CAMERA_INDEX)
# print("Sens:", SENS)

# # =========================================
# # ==========   CONFIGURACIÓN   ============
# # =========================================

# # Movimiento relativo
# MODE_RELATIVE = True
# REL_GAIN_X = 12000
# REL_GAIN_Y = 7680

# if SENS == "baja":
#     REL_GAIN_X = 3000
#     REL_GAIN_Y = 1920
# elif SENS == "media-baja":
#     REL_GAIN_X = 7500
#     REL_GAIN_Y = 4800
# elif SENS == "media-alta":
#     REL_GAIN_X = 16500
#     REL_GAIN_Y = 10560
    
# elif SENS == "alta":
#     REL_GAIN_X = 21000
#     REL_GAIN_Y = 13440

# ABS_GAIN_X = 2.0
# ABS_GAIN_Y = 1.8

# ALPHA_NOSE = 0.35
# MAX_PIXELS_PER_FRAME = 120
# DEAD_ZONE = 2

# # Boca / clicks
# SLOW_START_RATIO = 0.035
# CLICK_ARM_RATIO  = 0.055
# MIN_SPEED_SCALE_AT_MAX = 0.05
# CLICK_SHORT_SEC = 0.15
# CLICK_LONG_SEC  = 0.50
# CLICK_COOLDOWN_SEC = 0.40

# DBLCLICK_INTERVAL_SEC = 0.12
# SUSPEND_MOVE_SEC = 0.30

# pyautogui.FAILSAFE = True
# SAFE_MARGIN = 8
# SCREEN_W, SCREEN_H = pyautogui.size()

# suspend_move_until = 0.0

# def clamp(v, lo, hi):
#     return max(lo, min(hi, v))

# def clamp_with_margin(v, lo, hi, m=SAFE_MARGIN):
#     return max(lo+m, min(hi-m, v))
# # =========================================
# # ==========    CLICK FUNCTIONS   =========
# # =========================================

# def do_click():
#     global suspend_move_until
#     x, y = pyautogui.position()
#     suspend_move_until = time.time() + SUSPEND_MOVE_SEC
#     pyautogui.click(x=x, y=y, button="left")

# def do_double_click():
#     global suspend_move_until
#     x, y = pyautogui.position()
#     suspend_move_until = time.time() + SUSPEND_MOVE_SEC
#     pyautogui.click(x=x, y=y)
#     time.sleep(DBLCLICK_INTERVAL_SEC)
#     pyautogui.click(x=x, y=y)

# # =========================================
# # ==========  BOCA Y OJOS (EAR)  ==========
# # =========================================

# def mouth_open_ratio(lm):
#     p_up = lm[13]; p_dn = lm[14]
#     p_top = lm[10]; p_bot = lm[152]
#     dy_mouth = np.hypot(p_up.x - p_dn.x, p_up.y - p_dn.y)
#     dy_face  = np.hypot(p_top.x - p_bot.x, p_top.y - p_bot.y)
#     return dy_mouth / dy_face if dy_face > 1e-6 else 0.0

# LEFT_EYE_IDX  = [33,160,158,133,153,144]
# RIGHT_EYE_IDX = [362,385,387,263,373,380]

# def eye_aspect_ratio(lm, idxs):
#     p = [lm[i] for i in idxs]
#     v1 = np.hypot(p[1].x - p[5].x, p[1].y - p[5].y)
#     v2 = np.hypot(p[2].x - p[4].x, p[2].y - p[4].y)
#     h  = np.hypot(p[0].x - p[3].x, p[0].y - p[3].y)
#     return (v1 + v2) / (2*h) if h > 1e-6 else 0.0

# EYE_CLOSED_THR = 0.22
# OTHER_MARGIN = 0.015
# WINK_COOLDOWN = 0.45

# last_wink_time = 0
# last_left_ear = 0
# last_right_ear = 0

# global mouth_ratio_vis

# # Estados boca
# mouth_ratio_vis = 0
# mouth_open_prev = False
# mouth_open_start = None
# last_click_time = 0
# mouth_click_armed = False

# def detect_click(CLICK_MODE, lm, ratio_raw, now):
#     global mouth_open_prev, mouth_open_start, mouth_click_armed
#     global last_click_time, last_wink_time
#     global last_left_ear, last_right_ear

#     # ========= MODO BOCA =========
#     if CLICK_MODE == "mouth":
#         opened = (ratio_raw >= SLOW_START_RATIO)
#         clicked = None

#         if opened and not mouth_open_prev:
#             mouth_open_start = now

#         if (not opened) and mouth_open_prev and mouth_open_start:
#             dur = now - mouth_open_start
#             if mouth_click_armed and (now - last_click_time >= CLICK_COOLDOWN_SEC):
#                 if dur >= CLICK_LONG_SEC:
#                     clicked = "double"
#                 elif dur >= CLICK_SHORT_SEC:
#                     clicked = "click"
#                 last_click_time = now
#             mouth_open_start = None
#             mouth_click_armed = False

#         if ratio_raw >= CLICK_ARM_RATIO:
#             mouth_click_armed = True

#         mouth_open_prev = opened
#         return clicked

#     # ========= MODOS GUIÑOS =========
#     left = eye_aspect_ratio(lm, LEFT_EYE_IDX)
#     right = eye_aspect_ratio(lm, RIGHT_EYE_IDX)

#     last_left_ear = left
#     last_right_ear = right

#     if CLICK_MODE == "wink_left":
#         if left < EYE_CLOSED_THR and right > EYE_CLOSED_THR + OTHER_MARGIN:
#             if now - last_wink_time > WINK_COOLDOWN:
#                 last_wink_time = now
#                 return "click"

#     if CLICK_MODE == "wink_right":
#         if right < EYE_CLOSED_THR and left > EYE_CLOSED_THR + OTHER_MARGIN:
#             if now - last_wink_time > WINK_COOLDOWN:
#                 last_wink_time = now
#                 return "click"

#     return None

# # =========================================
# # ==========     CÁMARA WINDOWS     ========
# # =========================================

# def open_camera(index):
#     cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
#     if not cap.isOpened():
#         print(f"[ERROR] No se pudo abrir cámara {index}")
#         return None
#     cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
#     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
#     print(f"[INFO] Cámara abierta en índice {index}")
#     return cap
# # =========================================
# # ==========     INICIALIZACIÓN   =========
# # =========================================

# cap = open_camera(CAMERA_INDEX)
# if cap is None:
#     raise SystemExit("No se pudo iniciar la cámara.")

# mp_face_mesh = mp.solutions.face_mesh
# face_mesh = mp_face_mesh.FaceMesh(
#     static_image_mode=False,
#     max_num_faces=1,
#     refine_landmarks=False,
#     min_detection_confidence=0.3,
#     min_tracking_confidence=0.3
# )

# cur_x, cur_y = SCREEN_W // 2, SCREEN_H // 2
# nose_hist = deque(maxlen=1)
# nose_sx = nose_sy = None
# center_x = center_y = 0.5

# SHOW_OVERLAY = True

# # =========================================
# # ==========     LOOP PRINCIPAL    =========
# # =========================================

# while True:
#     ok, frame = cap.read()
#     if not ok:
#         continue

#     frame = cv2.flip(frame, 1)
#     rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#     res = face_mesh.process(rgb)
#     now = time.time()

#     if res.multi_face_landmarks:
#         lm = res.multi_face_landmarks[0].landmark
#         nose = lm[1]

#         # Boca suavizada
#         ratio_raw = mouth_open_ratio(lm)
#         mouth_ratio_vis = (1 - 0.5)*mouth_ratio_vis + 0.5*ratio_raw

#         # CLICK LOGIC
#         action = detect_click(CLICK_MODE, lm, ratio_raw, now)
#         if action == "click":
#             do_click()
#         elif action == "double":
#             do_double_click()

#         # Suavizado nariz
#         if nose_sx is None:
#             nose_sx, nose_sy = nose.x, nose.y
#         else:
#             nose_sx = (1-ALPHA_NOSE)*nose_sx + ALPHA_NOSE*nose.x
#             nose_sy = (1-ALPHA_NOSE)*nose_sy + ALPHA_NOSE*nose.y

#         # Velocidad según boca
#         if ratio_raw <= SLOW_START_RATIO:
#             speed = 1.0
#         elif ratio_raw >= CLICK_ARM_RATIO:
#             speed = MIN_SPEED_SCALE_AT_MAX
#         else:
#             t = (ratio_raw - SLOW_START_RATIO) / (CLICK_ARM_RATIO - SLOW_START_RATIO)
#             speed = 1.0 - t*t*(1 - MIN_SPEED_SCALE_AT_MAX)

#         # Movimiento RELATIVO
#         if MODE_RELATIVE:
#             if len(nose_hist) == 0:
#                 nose_hist.append((nose_sx, nose_sy))
#             px, py = nose_hist[-1]
#             dx = (nose_sx - px) * (REL_GAIN_X * speed)
#             dy = (nose_sy - py) * (REL_GAIN_Y * speed)
#             nose_hist.append((nose_sx, nose_sy))

#             target_x = cur_x + dx
#             target_y = cur_y + dy

#             # límite de velocidad
#             dist = np.hypot(target_x - cur_x, target_y - cur_y)
#             vmax = max(5, int(MAX_PIXELS_PER_FRAME * speed))

#             if dist > vmax:
#                 k = vmax / dist
#                 target_x = cur_x + (target_x - cur_x)*k
#                 target_y = cur_y + (target_y - cur_y)*k

#             # mover mouse
#             if time.time() >= suspend_move_until:
#                 target_x = int(clamp_with_margin(target_x, 0, SCREEN_W-1))
#                 target_y = int(clamp_with_margin(target_y, 0, SCREEN_H-1))
#                 pyautogui.moveTo(target_x, target_y, duration=0.01)
#                 cur_x, cur_y = target_x, target_y

#         # ========= Overlay =========
#         if SHOW_OVERLAY:
#             h, w = frame.shape[:2]
#             cx = int(nose_sx * w)
#             cy = int(nose_sy * h)
#             cv2.circle(frame, (cx, cy), 5, (0,255,0), -1)

#             # Barra boca
#             cv2.rectangle(frame, (10,50), (210,70), (40,40,40), -1)
#             bl = int(min(200, 200*(mouth_ratio_vis/0.055)))
#             cv2.rectangle(frame, (10,50), (10+bl,70), (0,255,255), -1)

#             cv2.putText(frame, f"EAR L:{last_left_ear:.3f} R:{last_right_ear:.3f}",
#                         (10,150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,200,0), 2)

#     cv2.imshow("Face Mouse", frame)
#     k = cv2.waitKey(1)
#     if k == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()
# -*- coding: utf-8 -*-

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

# =========================================
# ==========   MENU GRAFICO GUI   =========
# =========================================

def show_gui_menu():
    window = tk.Tk()
    window.title("Configuración FaceMouse")
    window.resizable(False, False)
    zoom_var = tk.BooleanVar(value=True)

    # Tamaño automático según contenido (anti cortes)
    window.update_idletasks()
    window.geometry("")

    click_mode_var = tk.StringVar(value="mouth")
    sensitivity_var = tk.StringVar(value="media")
    stabilize_var = tk.BooleanVar(value=False)  # ✅ nuevo

    title = tk.Label(window, text="FACE MOUSE CONTROL", font=("Arial", 16, "bold"))
    title.pack(pady=10)

    frame_click = tk.LabelFrame(window, text="Modo de Click")
    frame_click.pack(fill="x", padx=20, pady=10)

    tk.Radiobutton(frame_click, text="Boca (click / doble click)",
                   variable=click_mode_var, value="mouth").pack(anchor="w", padx=10)

    tk.Radiobutton(frame_click, text="Guiño izquierdo (click)",
                   variable=click_mode_var, value="wink_left").pack(anchor="w", padx=10)

    tk.Radiobutton(frame_click, text="Guiño derecho (click)",
                   variable=click_mode_var, value="wink_right").pack(anchor="w", padx=10)

    frame_cam = tk.LabelFrame(window, text="Índice de cámara")
    frame_cam.pack(fill="x", padx=20, pady=10)

    cam_names, cam_map = get_camera_options()

    default_cam = cam_names[0] if cam_names else "Cam 0"
    cam_index_var = tk.StringVar(value=default_cam)

    ttk.Combobox(
        frame_cam,
        textvariable=cam_index_var,
        values=cam_names,
        state="readonly"
    ).pack(padx=10, pady=5)

    frame_sens = tk.LabelFrame(window, text="Sensibilidad")
    frame_sens.pack(fill="x", padx=20, pady=10)

    ttk.Combobox(frame_sens, textvariable=sensitivity_var,
                 values=["baja","media-baja", "media", "media-alta", "alta"]).pack(padx=10, pady=5)

    # ✅ Nuevo: Estabilización
    frame_stab = tk.LabelFrame(window, text="Estabilización (anti-temblor)")
    frame_stab.pack(fill="x", padx=20, pady=10)

    tk.Checkbutton(frame_stab, text="Activar estabilización de nariz (recomendado para pacientes)",
                   variable=stabilize_var).pack(anchor="w", padx=10, pady=5)

    hint = tk.Label(window,
                    text="Tip: Si queda muy 'lento', desactivá estabilización o subí sensibilidad.\n"
                         "Durante click por boca, el mouse se frena automáticamente.",
                    font=("Arial", 9))
    hint.pack(pady=5)

    def start():
        window.destroy()

    frame_zoom = tk.LabelFrame(window, text="Zoom automático")
    frame_zoom.pack(fill="x", padx=20, pady=10)

    tk.Checkbutton(
        frame_zoom,
        text="Activar zoom al entrar en modo preciso/lento",
        variable=zoom_var
    ).pack(anchor="w", padx=10, pady=5)

    tk.Button(window, text="COMENZAR", font=("Arial", 14, "bold"),
              command=start, bg="#4CAF50", fg="white").pack(pady=18)

    window.mainloop()

    return (
        click_mode_var.get(),
        cam_map.get(cam_index_var.get(), 0),
        sensitivity_var.get(),
        bool(stabilize_var.get()),
        bool(zoom_var.get())
    )
    

CLICK_MODE, CAMERA_INDEX, SENS, STABILIZE, AUTO_ZOOM_ENABLED = show_gui_menu()
print("Modo:", CLICK_MODE)
print("Cam:", CAMERA_INDEX)
print("Sens:", SENS)
print("Stabilize:", STABILIZE)


overlay_root = tk.Tk()
overlay_root.withdraw()
cursor_overlay = CursorOverlay(overlay_root)

# =========================================
# ==========   CONFIGURACIÓN   ============
# =========================================

MODE_RELATIVE = True

REL_GAIN_X = 12000
REL_GAIN_Y = 7680

if SENS == "baja":
    REL_GAIN_X = 3000
    REL_GAIN_Y = 1920
elif SENS == "media-baja":
    REL_GAIN_X = 7500
    REL_GAIN_Y = 4800
elif SENS == "media-alta":
    REL_GAIN_X = 16500
    REL_GAIN_Y = 10560
elif SENS == "alta":
    REL_GAIN_X = 21000
    REL_GAIN_Y = 13440

ABS_GAIN_X = 2.0
ABS_GAIN_Y = 1.8

ALPHA_NOSE = 0.35
MAX_PIXELS_PER_FRAME = 120

# ✅ Zona muerta en píxeles (tuya)
DEAD_ZONE = 2

# ✅ Zona muerta en coordenadas normalizadas (anti jitter real)
# Valores típicos: 0.0015–0.006
NOSE_DEADZONE_NORM = 0.0035 if STABILIZE else 0.0

# ✅ “Leaky integrator”: atenúa micro-drift del modo relativo
LEAK = 0.06 if STABILIZE else 0.0  # 0–0.15

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
DWELL_CLICK_SEC = 3.0
last_move_time = time.time()

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
DWELL_CLICK_SEC = 3.0              # segundos quieto para click
DWELL_STILL_RADIUS_PX = 12         # tolerancia de movimiento para considerarlo "quieto"
DWELL_POST_CLICK_DELAY = 1.0       # evita clicks repetidos inmediatos

last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()




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
NOSE_FILTER_X = OneEuroFilter1D(min_cutoff=1.4, beta=0.05, d_cutoff=1.0)
NOSE_FILTER_Y = OneEuroFilter1D(min_cutoff=1.4, beta=0.05, d_cutoff=1.0)


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

    print("[CAL] Calibrando ojos abiertos... mirá al frente y mantené los ojos relajados.")

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

        remaining = max(0.0, WINK_CALIBRATION_SEC - (time.time() - start_time))

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark

            left_ear = eye_aspect_ratio(lm, LEFT_EYE_IDX)
            right_ear = eye_aspect_ratio(lm, RIGHT_EYE_IDX)

            # evitar valores absurdos
            if 0.05 < left_ear < 0.80:
                samples_left.append(left_ear)
            if 0.05 < right_ear < 0.80:
                samples_right.append(right_ear)

            cv2.putText(frame, "CALIBRANDO OJOS ABIERTOS...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            cv2.putText(frame, f"Tiempo restante: {remaining:.1f}s", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 255, 200), 2)

            cv2.putText(frame, f"L EAR: {left_ear:.3f}  R EAR: {right_ear:.3f}", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)
        else:
            cv2.putText(frame, "No detecto la cara...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 255), 2)

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

def detect_click(mode, lm, ratio_raw, now):
    global mouth_open_prev, mouth_open_start, mouth_click_armed
    global last_click_time, last_wink_time
    global last_left_ear, last_right_ear

    if mode == "mouth":
        opened = (ratio_raw >= SLOW_START_RATIO)
        clicked = None

        if opened and not mouth_open_prev:
            mouth_open_start = now

        if (not opened) and mouth_open_prev and (mouth_open_start is not None):
            dur = now - mouth_open_start

            if mouth_click_armed and (now - last_click_time >= CLICK_COOLDOWN_SEC):
                if dur >= CLICK_LONG_SEC:
                    clicked = "double"
                elif dur >= CLICK_SHORT_SEC:
                    clicked = "click"
                last_click_time = now

            mouth_open_start = None
            mouth_click_armed = False

        if ratio_raw >= CLICK_ARM_RATIO:
            mouth_click_armed = True

        mouth_open_prev = opened
        return clicked

    left = eye_aspect_ratio(lm, LEFT_EYE_IDX)
    right = eye_aspect_ratio(lm, RIGHT_EYE_IDX)
    last_left_ear = left
    last_right_ear = right

    if mode == "wink_left":
        left_closed = left < LEFT_EYE_CLOSED_THR
        right_open = right > RIGHT_EYE_OPEN_THR

        if left_closed and right_open:
            if (now - last_wink_time) > WINK_COOLDOWN:
                last_wink_time = now
                return "click"

    if mode == "wink_right":
        right_closed = right < RIGHT_EYE_CLOSED_THR
        left_open = left > LEFT_EYE_OPEN_THR

        if right_closed and left_open:
            if (now - last_wink_time) > WINK_COOLDOWN:
                last_wink_time = now
                return "click"

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
    global RUNNING, PAUSED, drag_active, DWELL_ENABLED
    global dwell_progress, WINK_CLOSED_FACTOR, WINK_OPEN_FACTOR

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
DWELL_CLICK_SEC = 2.0
DWELL_STILL_RADIUS_PX = 20
DWELL_POST_CLICK_DELAY = 1.0

last_move_time = time.time()
last_dwell_click_time = 0.0
last_cursor_pos = pyautogui.position()
dwell_progress = 0.0

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
        nose = lm[1]

        # Boca suavizada (solo visual y freno)
        ratio_raw = mouth_open_ratio(lm)
        mouth_ratio_vis = (1 - 0.5)*mouth_ratio_vis + 0.5*ratio_raw
        mouth_open_now = ratio_raw >= SLOW_START_RATIO

        # Click
        action = detect_click(CLICK_MODE, lm, ratio_raw, now)

        left_ear_vis = (1 - EAR_VIS_ALPHA) * left_ear_vis + EAR_VIS_ALPHA * last_left_ear
        right_ear_vis = (1 - EAR_VIS_ALPHA) * right_ear_vis + EAR_VIS_ALPHA * last_right_ear

        if action == "click":
            do_click()
            # reset de filtros para evitar “rebote” post-click
            NOSE_FILTER_X.reset()
            NOSE_FILTER_Y.reset()
            nose_prev_fx = None
            nose_prev_fy = None
        elif action == "double":
            do_double_click()
            NOSE_FILTER_X.reset()
            NOSE_FILTER_Y.reset()
            nose_prev_fx = None
            nose_prev_fy = None

        # -------- Nariz: filtro anti temblor --------
        nx, ny = float(nose.x), float(nose.y)

        if STABILIZE:
            fx = NOSE_FILTER_X.apply(nx, now)
            fy = NOSE_FILTER_Y.apply(ny, now)
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

            # ✅ Zona muerta en normalizado (anti jitter real)
            if abs(dnx) < NOSE_DEADZONE_NORM:
                dnx = 0.0
            if abs(dny) < NOSE_DEADZONE_NORM:
                dny = 0.0

            # ✅ “leak” para frenar micro-drift
            # (suaviza el integrado cuando el paciente tiembla)
            if LEAK > 0:
                dnx *= (1.0 - LEAK)
                dny *= (1.0 - LEAK)

            dx = dnx * (REL_GAIN_X * speed)
            dy = dny * (REL_GAIN_Y * speed)

            nose_prev_fx, nose_prev_fy = fx, fy

            target_x = cur_x + dx
            target_y = cur_y + dy

            # límite de velocidad
            dist = np.hypot(target_x - cur_x, target_y - cur_y)
            vmax = max(5, int(MAX_PIXELS_PER_FRAME * speed))
            if dist > vmax and dist > 0:
                k = vmax / dist
                target_x = cur_x + (target_x - cur_x)*k
                target_y = cur_y + (target_y - cur_y)*k

            # mover mouse
            if drag_active or (time.time() >= suspend_move_until):
                target_x = int(clamp_with_margin(target_x, 0, SCREEN_W-1))
                target_y = int(clamp_with_margin(target_y, 0, SCREEN_H-1))

                # ✅ deadzone en píxeles final
                if abs(target_x - cur_x) >= DEAD_ZONE or abs(target_y - cur_y) >= DEAD_ZONE:
                    pyautogui.moveTo(target_x, target_y, duration=0.01)
                    cur_x, cur_y = target_x, target_y

                    now_pos = pyautogui.position()
                    dt = time.time() - prev_speed_time

                    if dt > 0:
                        dist = np.hypot(
                            now_pos[0] - prev_cursor_pos[0],
                            now_pos[1] - prev_cursor_pos[1]
                        )

                        cursor_speed = dist / dt

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
            f"Face: OK | mode={CLICK_MODE} | speed={speed:.2f} | "
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

            left_active = (CLICK_MODE == "wink_left" and last_left_ear < LEFT_EYE_CLOSED_THR)
            right_active = (CLICK_MODE == "wink_right" and last_right_ear < RIGHT_EYE_CLOSED_THR)

            draw_eye_bar(
                frame, 10, 235, 220, 18,
                left_ear_vis, LEFT_EYE_CLOSED_THR, LEFT_EYE_OPEN_EAR,
                "L EAR", active=left_active
            )

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
            
            cv2.putText(frame, f"Dwell: {'ON' if DWELL_ENABLED else 'OFF'}  prog={dwell_progress:.2f}",
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