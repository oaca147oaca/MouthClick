"""Accessible live settings window; preview and persistence are separate callbacks."""
import tkinter as tk
from tkinter import ttk
from mouthclick_ui import Card, apply_theme, label, COLORS, FONT, field, hint, toggle, button
from mouthclick_runtime import FACE_POINTS, WINK_LEVELS, RANGES, SettingsSession


def numeric(parent, title, variable, key):
    hint(parent, title)
    low, high, _ = RANGES[key]
    step = 0.005 if key == "mouth_threshold" else 0.05 if key in ("smoothing", "deadzone") else 0.1 if key == "dwell_time" else 1.0
    widget = ttk.Spinbox(parent, textvariable=variable, from_=low, to=high,
                         increment=step, width=12, font=(FONT, 11))
    widget.pack(fill="x", ipady=8, pady=(0, 8))
    return widget


class LiveSettings(tk.Toplevel):
    def __init__(self, master, name, current, apply, save, sound_test, audio_error):
        super().__init__(master)
        self.session = SettingsSession(current, apply, save)
        self.audio_error = audio_error
        self.syncing = False
        apply_theme(self)
        self.title(f"MouthClick Ajustes · {name}")
        self.attributes("-topmost", True)
        width, height = min(780, self.winfo_screenwidth()-40), min(680, self.winfo_screenheight()-90)
        self.geometry(f"{width}x{height}")
        self.minsize(min(560,width), min(520,height))
        self.protocol("WM_DELETE_WINDOW", self.discard)
        header = tk.Frame(self, bg=COLORS["panel"], padx=20, pady=10)
        header.pack(fill="x")
        label(header, "Sensibilidades", size=20, bold=True).pack(anchor="w")
        label(header, f"Perfil: {name} · Ajustes en vivo", secondary=True, size=10).pack(anchor="w")
        footer = tk.Frame(self, bg=COLORS["panel"], padx=16, pady=10)
        footer.pack(side="bottom", fill="x")
        self.message = tk.Label(footer, text="Probá los cambios. Cerrar sin guardar restaura los valores anteriores.",
                                bg=COLORS["panel"], fg=COLORS["muted"], justify="left", font=(FONT,10))
        self.message.pack(fill="x", pady=(0,6))
        self.message.bind("<Configure>", lambda e: self.message.configure(wraplength=max(100,e.width-4)))
        actions = tk.Frame(footer, bg=COLORS["panel"])
        actions.pack(fill="x")
        actions.columnconfigure((0,1),weight=1,uniform="actions")
        button(actions, "Guardar en perfil", self.commit, primary=True).grid(row=0,column=0,sticky="ew",padx=(0,5))
        button(actions, "Cerrar sin guardar", self.discard).grid(row=0,column=1,sticky="ew",padx=(5,0))
        navigation = tk.Frame(self, bg=COLORS["bg"], padx=16, pady=8)
        navigation.pack(side="bottom",fill="x")
        self.previous_button = button(navigation, "← Anterior", lambda:self.show_page(self.page_index-1))
        self.previous_button.pack(side="left")
        self.next_button = button(navigation, "Siguiente →", lambda:self.show_page(self.page_index+1))
        self.next_button.pack(side="right")
        self.page_label = label(navigation, "", secondary=True, size=11)
        self.page_label.pack(expand=True,fill="both")
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(fill="both",expand=True,padx=16,pady=8)
        self.pages = []
        self.page_index = 0
        self.vars = {}
        for key in RANGES:
            self.vars[key] = tk.StringVar(self, value=f"{current[key]:g}")
        for key in ("face_point", "wink_diff_sens"):
            self.vars[key] = tk.StringVar(self, value=current[key])
        for key in ("stabilize", "zoom", "dwell_enabled", "sound_enabled"):
            self.vars[key] = tk.BooleanVar(self, value=current[key])
        point = self.add_page("Punto facial")
        field(point, "Punto de la cara", self.vars["face_point"], list(FACE_POINTS))
        hint(point, "El punto se detecta automáticamente. Podés probar otro sin reiniciar.")
        motion = self.add_page("Movimiento")
        numeric(motion, "Sensibilidad horizontal · X", self.vars["gain_x"], "gain_x")
        numeric(motion, "Sensibilidad vertical · Y", self.vars["gain_y"], "gain_y")
        precision = self.add_page("Estabilización")
        toggle(precision, "Estabilizar el movimiento", self.vars["stabilize"])
        numeric(precision, "Suavizado · menor = más suave", self.vars["smoothing"], "smoothing")
        deadzone = self.add_page("Zona muerta")
        numeric(deadzone, "Movimiento mínimo · píxeles de cámara", self.vars["deadzone"], "deadzone")
        hint(deadzone, "Ignora movimientos menores a este valor para reducir temblores del cursor.")
        gestures = self.add_page("Gestos")
        field(gestures, "Sensibilidad del guiño", self.vars["wink_diff_sens"], WINK_LEVELS)
        numeric(gestures, "Umbral de boca · menor = más sensible", self.vars["mouth_threshold"], "mouth_threshold")
        audio = self.add_page("Sonido")
        toggle(audio, "Sonido de las acciones", self.vars["sound_enabled"])
        button(audio, "Probar sonido", sound_test).pack(fill="x", pady=4)
        dwell = self.add_page("Autoclick")
        toggle(dwell, "Autoclick por permanencia", self.vars["dwell_enabled"])
        numeric(dwell, "Tiempo de espera · segundos", self.vars["dwell_time"], "dwell_time")
        aids = self.add_page("Tolerancia y zoom")
        numeric(aids, "Tolerancia del autoclick · píxeles", self.vars["dwell_radius"], "dwell_radius")
        toggle(aids, "Zoom automático", self.vars["zoom"])
        for variable in self.vars.values():
            variable.trace_add("write", self.preview)
        self.bind("<Alt-Left>",lambda e:self.show_page(self.page_index-1))
        self.bind("<Alt-Right>",lambda e:self.show_page(self.page_index+1))
        self.show_page(0)

    def add_page(self, title):
        card = Card(self.content,title,f"{len(self.pages)+1:02}")
        self.pages.append(card)
        return card.body

    def show_page(self, index):
        if not 0 <= index < len(self.pages):
            return
        for page in self.pages:
            page.pack_forget()
        self.page_index = index
        self.pages[index].pack(fill="both",expand=True)
        self.page_label.configure(text=f"{index+1} / {len(self.pages)}")
        self.previous_button.configure(state="normal" if index else "disabled")
        self.next_button.configure(state="normal" if index<len(self.pages)-1 else "disabled")
        # Keep keyboard focus on a visible control when changing pages.
        self.next_button.focus_set() if index<len(self.pages)-1 else self.previous_button.focus_set()

    def preview(self, *args):
        if self.syncing:
            return True
        try:
            self.session.preview({key: variable.get() for key, variable in self.vars.items()})
            self.message.configure(text="Cambios aplicados para probar · todavía sin guardar", fg=COLORS["muted"])
            return True
        except (ValueError, tk.TclError) as exc:
            self.message.configure(text=f"Revisá el valor ingresado. {exc}", fg=COLORS["amber"])
            return False

    def sync(self, values):
        """Reflect keyboard shortcuts without resetting the cancel snapshot."""
        self.syncing = True
        try:
            self.session.values.update(values)
            for key, var in self.vars.items():
                var.set(values[key])
        finally:
            self.syncing = False

    def commit(self):
        if not self.preview():
            return
        try:
            self.session.commit()
        except (OSError, ValueError) as exc:
            self.message.configure(text=f"No se guardó el perfil: {exc}", fg=COLORS["amber"])
            return
        self.destroy()

    def discard(self):
        self.session.cancel()
        self.destroy()
