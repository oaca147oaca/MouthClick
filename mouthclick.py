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

# =========================================
# ==========   MENU GRAFICO GUI   =========
# =========================================

def show_gui_menu():
    window = tk.Tk()
    window.title("Configuración FaceMouse")
    window.resizable(False, False)

    # Tamaño automático según contenido (anti cortes)
    window.update_idletasks()
    window.geometry("")

    click_mode_var = tk.StringVar(value="mouth")
    cam_index_var = tk.StringVar(value="0")
    sensitivity_var = tk.StringVar(value="media")
    stabilize_var = tk.BooleanVar(value=True)  # ✅ nuevo

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

    ttk.Combobox(frame_cam, textvariable=cam_index_var,
                 values=["0", "1", "2", "3", "4"]).pack(padx=10, pady=5)

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

    tk.Button(window, text="COMENZAR", font=("Arial", 14, "bold"),
              command=start, bg="#4CAF50", fg="white").pack(pady=18)

    window.mainloop()
    return click_mode_var.get(), int(cam_index_var.get()), sensitivity_var.get(), bool(stabilize_var.get())

CLICK_MODE, CAMERA_INDEX, SENS, STABILIZE = show_gui_menu()
print("Modo:", CLICK_MODE)
print("Cam:", CAMERA_INDEX)
print("Sens:", SENS)
print("Stabilize:", STABILIZE)

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

# =========================================
# ==========    CLICK FUNCTIONS   =========
# =========================================

def do_click():
    global suspend_move_until
    x, y = pyautogui.position()
    suspend_move_until = time.time() + SUSPEND_MOVE_SEC
    pyautogui.click(x=x, y=y, button="left")

def do_double_click():
    global suspend_move_until
    x, y = pyautogui.position()
    suspend_move_until = time.time() + SUSPEND_MOVE_SEC
    pyautogui.click(x=x, y=y)
    time.sleep(DBLCLICK_INTERVAL_SEC)
    pyautogui.click(x=x, y=y)

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
    global drag_active
    if drag_active:
        pyautogui.mouseUp(button="left")
        drag_active = False
        print("DRAG STOP")

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

EYE_CLOSED_THR = 0.22
OTHER_MARGIN = 0.015
WINK_COOLDOWN = 0.45

last_wink_time = 0.0
last_left_ear = 0.0
last_right_ear = 0.0

# Estados boca
mouth_ratio_vis = 0.0
mouth_open_prev = False
mouth_open_start = None
last_click_time = 0.0
mouth_click_armed = False

drag_active = False
drag_started_at = None


def detect_click(mode, lm, ratio_raw, now):
    global drag_active, drag_started_at
    global mouth_open_prev, mouth_open_start, mouth_click_armed
    global last_click_time, last_wink_time
    global last_left_ear, last_right_ear

    # =========================
    # MODO BOCA (click/doble/drag)
    # =========================
    if mode == "mouth":
        opened = (ratio_raw >= SLOW_START_RATIO)
        clicked = None

        # inicio de apertura
        if opened and not mouth_open_prev:
            mouth_open_start = now
            drag_started_at = None  # reset drag timer

        # mientras está abierta
        if opened:
            # “armar” click cuando supera el umbral fuerte
            if ratio_raw >= CLICK_ARM_RATIO:
                mouth_click_armed = True

                # iniciar conteo para drag
                if drag_started_at is None:
                    drag_started_at = now

                # si se mantuvo abierta suficiente → empezar drag
                if (not drag_active) and (now - drag_started_at >= DRAG_START_SEC):
                    start_drag()
            else:
                # si abrió un poco pero no llegó a “armar”, no cuenta drag
                drag_started_at = None

        # cierre de boca
        if (not opened) and mouth_open_prev and (mouth_open_start is not None):
            dur = now - mouth_open_start

            # si estaba arrastrando, al cerrar suelta y NO hace click
            if drag_active:
                stop_drag()
            else:
                # click / doble click como antes
                if mouth_click_armed and (now - last_click_time >= CLICK_COOLDOWN_SEC):
                    if dur >= CLICK_LONG_SEC:
                        clicked = "double"
                    elif dur >= CLICK_SHORT_SEC:
                        clicked = "click"
                    last_click_time = now

            # reset
            mouth_open_start = None
            mouth_click_armed = False
            drag_started_at = None

        mouth_open_prev = opened
        return clicked

    # =========================
    # MODOS GUIÑO (EAR)
    # =========================
    left = eye_aspect_ratio(lm, LEFT_EYE_IDX)
    right = eye_aspect_ratio(lm, RIGHT_EYE_IDX)
    last_left_ear = left
    last_right_ear = right

    if mode == "wink_left":
        if left < EYE_CLOSED_THR and right > EYE_CLOSED_THR + OTHER_MARGIN:
            if (now - last_wink_time) > WINK_COOLDOWN:
                last_wink_time = now
                return "click"

    if mode == "wink_right":
        if right < EYE_CLOSED_THR and left > EYE_CLOSED_THR + OTHER_MARGIN:
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

cur_x, cur_y = SCREEN_W // 2, SCREEN_H // 2

# relativo: guardamos última nariz filtrada para delta
nose_prev_fx = None
nose_prev_fy = None

# para que al comenzar no “salte”
NOSE_FILTER_X.reset()
NOSE_FILTER_Y.reset()

# =========================================
# ==========     LOOP PRINCIPAL    =========
# =========================================

while True:
    ok, frame = cap.read()
    if not ok:
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

        # Click
        action = detect_click(CLICK_MODE, lm, ratio_raw, now)
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
                    last_move_time = time.time()
            
            # =========================================
            # ========== DWELL CLICK (AUTO) ===========
            # =========================================
            # Si está quieto X segundos → click automático
            # (no se dispara si estás arrastrando, ni durante cooldown, ni si la boca está abierta)
            if (not drag_active) and (time.time() >= suspend_move_until):
                if (time.time() - last_move_time) >= DWELL_CLICK_SEC:
                    # Evitar autoclick mientras está “abriendo” boca (para que no choque con tu click por boca)
                    if ratio_raw < SLOW_START_RATIO:
                        do_click()
                        # Reinicio para que no haga clicks en loop
                        last_move_time = time.time() + 0.75
                        # Reset filtros para evitar salto post click
                        NOSE_FILTER_X.reset()
                        NOSE_FILTER_Y.reset()
                        nose_prev_fx = None
                        nose_prev_fy = None

        status_text = f"Face: OK | mode={CLICK_MODE} | stabilize={'ON' if STABILIZE else 'OFF'} | speed={speed:.2f}"

        # -------- Overlay --------
        if SHOW_OVERLAY:
            h, w = frame.shape[:2]
            cx = int(clamp(fx, 0, 1) * w)
            cy = int(clamp(fy, 0, 1) * h)
            cv2.circle(frame, (cx, cy), 5, (0,255,0), -1)

            # Barra boca
            cv2.rectangle(frame, (10,50), (210,70), (40,40,40), -1)
            bl = int(min(200, 200*(mouth_ratio_vis/0.055)))
            cv2.rectangle(frame, (10,50), (10+bl,70), (0,255,255), -1)

            cv2.putText(frame, status_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

            cv2.putText(frame, f"EAR L:{last_left_ear:.3f} R:{last_right_ear:.3f}",
                        (10,150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,200,0), 2)

            cv2.putText(frame, f"DeadzoneNorm: {NOSE_DEADZONE_NORM:.4f}  Leak: {LEAK:.2f}",
                        (10,180), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,255,180), 2)

    k = cv2.waitKey(1)

    if k == ord('q'):
        break

    elif k == ord('c'):
        center_mouse()  
    
cap.release()
cv2.destroyAllWindows()
face_mesh.close()