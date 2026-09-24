"""Accessible live settings window; preview and persistence are separate callbacks."""
import tkinter as tk
from tkinter import ttk
from mouthclick_ui import Card, apply_theme, label, COLORS, FONT, field, hint, toggle, button, compact_card
from mouthclick_runtime import FACE_POINTS, WINK_LEVELS, RANGES, SettingsSession


def numeric(parent, title, variable, key):
    hint(parent, title)
    low, high, _ = RANGES[key]
    step = 0.005 if key == "mouth_threshold" else 0.05 if key in ("smoothing", "deadzone") else 0.1 if key == "dwell_time" else 1.0
    widget = ttk.Spinbox(parent, textvariable=variable, from_=low, to=high,
                         increment=step, width=12, font=(FONT, 11))
    widget.pack(fill="x", ipady=5, pady=(0, 8))
    return widget


class LiveSettings(tk.Toplevel):
    def __init__(self, master, name, current, apply, save, sound_test, audio_error, movement_levels=None):
        super().__init__(master)
        self.session = SettingsSession(current, apply, save)
        self.audio_error = audio_error
        self.syncing = False
        self.movement_levels = movement_levels or {
            "gain_x": {"baja":42.,"media":62.,"alta":74.,"muy alta":88.,"extrema":104.},
            "gain_y": {"baja":36.,"media":52.,"alta":64.,"muy alta":78.,"extrema":92.}}
        self.level_vars = {}
        apply_theme(self)
        self.title(f"MouthClick Ajustes · {name}")
        self.attributes("-topmost", False)
        width, height = min(780, self.winfo_screenwidth()-40), min(680, self.winfo_screenheight()-90)
        self.geometry(f"{width}x{height}")
        scale = float(self.tk.call("tk", "scaling"))/1.3333
        self.minsize(min(round(1000*scale),self.winfo_screenwidth()-40),
                     min(round(730*scale),self.winfo_screenheight()))
        self.protocol("WM_DELETE_WINDOW", self.discard)
        self.chrome = WindowChrome(self, self.discard)
        header = tk.Frame(self, bg=COLORS["panel"], padx=20, pady=10)
        header.pack(fill="x")
        label(header, "Sensibilidades", size=20, bold=True).pack(anchor="w")
        label(header, f"Perfil: {name} · Ajustes en vivo", secondary=True, size=10).pack(anchor="w")
        footer = tk.Frame(self, bg=COLORS["panel"], padx=16, pady=10)
        footer.pack(side="bottom", fill="x")
        self.message = tk.Label(footer, text="Probá los cambios. Cerrar sin guardar restaura los valores anteriores.",
                                bg=COLORS["panel"], fg=COLORS["muted"], justify="left", font=(FONT,10))
        self.message.pack(fill="x", pady=(0,6))
        if name == "Por Defecto":
            self.message.configure(text="La base Por Defecto se conserva. Los cambios se guardan en un perfil Personalizado nuevo.")
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
        for key,title in (("gain_x","Sensibilidad horizontal · X"),("gain_y","Sensibilidad vertical · Y")):
            variable = tk.StringVar(self)
            self.level_vars[key] = variable
            combo = field(motion,title,variable,list(self.movement_levels[key])+["Personalizada"])
            combo.bind("<<ComboboxSelected>>",lambda e,k=key:self.select_level(k))
        button(motion,"Ajuste fino X/Y →",lambda:self.show_page(2)).pack(fill="x",pady=2)
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
        fine = self.add_page("Ajuste fino X/Y")
        numeric(fine,"Valor exacto horizontal · X",self.vars["gain_x"],"gain_x")
        numeric(fine,"Valor exacto vertical · Y",self.vars["gain_y"],"gain_y")
        button(fine,"← Volver a niveles",lambda:self.show_page(0)).pack(fill="x")
        for page in self.pages:
            for card in page.cards:
                compact_card(card)
        self.sync_levels()
        for variable in self.vars.values():
            variable.trace_add("write", self.preview)
        self.bind("<Alt-Left>",lambda e:self.show_page(self.page_index-1))
        self.bind("<Alt-Right>",lambda e:self.show_page(self.page_index+1))
        self.show_page(0)
        self.chrome.maximize()

    def add_page(self, title):
        number = getattr(self, "card_count", 0)
        if number % 4 == 0:
            page = tk.Frame(self.content, bg=COLORS["bg"])
            page.columnconfigure((0,1), weight=1, uniform="cards")
            page.rowconfigure((0,1), weight=1, uniform="rows")
            page.cards = []
            self.pages.append(page)
        page = self.pages[-1]
        card = Card(page, title, f"{number+1:02}")
        card.grid(row=(number%4)//2, column=number%2, sticky="nsew", padx=(0,8) if number%2==0 else (8,0),pady=5)
        page.cards.append(card)
        self.card_count = number+1
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

    def select_level(self,key):
        value = self.movement_levels[key].get(self.level_vars[key].get())
        if value is not None:
            self.vars[key].set(f"{value:g}")

    def sync_levels(self):
        for key,var in self.level_vars.items():
            try:
                value = float(self.vars[key].get())
                var.set(next((name for name,gain in self.movement_levels[key].items() if gain==value),"Personalizada"))
            except ValueError:
                var.set("Personalizada")

    def preview(self, *args):
        if self.syncing:
            return True
        try:
            self.sync_levels()
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
            self.sync_levels()

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


class WindowChrome:
    """Custom controls; restore native decorations temporarily to minimize on Windows."""
    def __init__(self, window, close, caption="MouthClick · Sensibilidades"):
        self.window = window
        self.maximized = False
        self.minimized = False
        self.restore_geometry = window.geometry()
        window.overrideredirect(True)
        bar = tk.Frame(window, bg=COLORS["panel"])
        children = window.pack_slaves()
        bar.pack(fill="x", **({"before": children[0]} if children else {}))
        title = label(bar, caption, size=11)
        title.pack(side="left", padx=18)
        for text, callback in (("Cerrar ×", close), ("Restaurar □", self.toggle), ("Minimizar −", self.minimize)):
            control = button(bar, text, callback)
            control.configure(pady=4, padx=10, font=(FONT,10,"bold"))
            control.pack(side="right", padx=3, pady=4)
            if text.startswith("Restaurar"):
                self.max_button = control
        for target in (bar, title):
            target.bind("<ButtonPress-1>", self.drag_start)
            target.bind("<B1-Motion>", self.drag)
        window.bind("<Map>", self.mapped, add="+")

    def maximize(self):
        self.maximized = True
        self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}+0+0")
        self.max_button.configure(text="Restaurar □")

    def toggle(self):
        if self.maximized:
            self.maximized = False
            self.window.geometry(self.restore_geometry)
            self.max_button.configure(text="Maximizar □")
        else:
            self.restore_geometry = self.window.geometry()
            self.maximize()

    def minimize(self):
        self.minimized = True
        self.window.overrideredirect(False)
        self.window.iconify()

    def mapped(self, event):
        if event.widget is self.window and self.minimized and self.window.state() != "iconic":
            self.minimized = False
            self.window.after_idle(lambda: self.window.overrideredirect(True))

    def drag_start(self, event):
        self.offset = (event.x_root-self.window.winfo_x(), event.y_root-self.window.winfo_y())

    def drag(self, event):
        if not self.maximized:
            x, y = self.offset
            self.window.geometry(f"+{max(0,event.x_root-x)}+{max(0,event.y_root-y)}")


class ConfirmAction(tk.Toplevel):
    """Nonblocking confirmation: face tracking stays active until acceptance."""
    def __init__(self, master, title, explanation, accept):
        super().__init__(master)
        apply_theme(self)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        width = min(640, self.winfo_screenwidth()-32)
        height = min(440, self.winfo_screenheight()-40)
        self.geometry(f"{width}x{height}+{(self.winfo_screenwidth()-width)//2}+{(self.winfo_screenheight()-height)//2}")
        body = tk.Frame(self, bg=COLORS["card"], padx=24, pady=24,
                        highlightbackground=COLORS["border"], highlightthickness=1)
        body.pack(fill="both", expand=True)
        label(body, title, size=20, bold=True).pack(anchor="w")
        label(body, explanation, size=11, wraplength=width-55, justify="left").pack(fill="x", pady=18)
        def confirmed():
            self.destroy()
            accept()
        self.cancel_button = button(body, "Cancelar · seguir usando", self.destroy)
        self.cancel_button.pack(side="bottom", fill="x", pady=4)
        self.accept_button = button(body, "Confirmar", confirmed, primary=True)
        self.accept_button.pack(side="bottom", fill="x", pady=4)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
