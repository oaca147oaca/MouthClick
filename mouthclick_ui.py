"""Shared native Tk presentation for MouthClick. No device or input logic."""
import tkinter as tk
from tkinter import ttk

COLORS = dict(bg="#070B14", panel="#0C1220", card="#182238", input="#111A2B",
              red="#E31B2B", hover="#F02A38", text="#F5F7FB", muted="#ACBBD0",
              border="#344158", green="#64D995", amber="#FFD078")
FONT = "Segoe UI"


def apply_theme(root):
    root.configure(bg=COLORS["bg"])
    root.option_add("*Font", (FONT, 11))
    root.option_add("*Listbox.background", COLORS["input"])
    root.option_add("*Listbox.foreground", COLORS["text"])
    root.option_add("*Listbox.selectBackground", COLORS["red"])
    root.option_add("*Listbox.selectForeground", COLORS["text"])
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TCombobox", padding=10, arrowsize=20, font=(FONT, 11),
                    foreground=COLORS["text"], fieldbackground=COLORS["input"],
                    background=COLORS["input"], arrowcolor=COLORS["text"],
                    bordercolor=COLORS["border"], lightcolor=COLORS["border"],
                    darkcolor=COLORS["border"], selectbackground=COLORS["input"],
                    selectforeground=COLORS["text"])
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["input"])],
              foreground=[("disabled", COLORS["muted"]), ("readonly", COLORS["text"])],
              bordercolor=[("focus", COLORS["red"])],
              arrowcolor=[("disabled", COLORS["muted"]), ("active", COLORS["text"])])
    style.configure("Vertical.TScrollbar", background=COLORS["border"],
                    troughcolor=COLORS["bg"], arrowcolor=COLORS["muted"],
                    borderwidth=0, arrowsize=20)
    style.map("Vertical.TScrollbar", background=[("active", COLORS["muted"])])


def label(parent, text, secondary=False, size=11, bold=False, **kwargs):
    return tk.Label(parent, text=text, bg=parent.cget("bg"),
                    fg=COLORS["muted" if secondary else "text"],
                    font=(FONT, size, "bold" if bold else "normal"), **kwargs)


def button(parent, text, command, primary=False, **kwargs):
    bg = COLORS["red" if primary else "input"]
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=COLORS["text"],
                  activebackground=COLORS["hover" if primary else "border"],
                  activeforeground=COLORS["text"], relief="flat", bd=0,
                  highlightthickness=2, highlightbackground=bg,
                  highlightcolor=COLORS["text"], font=(FONT, 11, "bold"),
                  padx=18, pady=11, cursor="hand2", takefocus=True, **kwargs)
    b.bind("<Enter>", lambda e: b.configure(bg=COLORS["hover" if primary else "border"]))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    b.bind("<Return>", lambda e: b.invoke())
    return b


class Card(tk.Canvas):
    """Rounded shell; actual controls remain standard keyboard-accessible widgets."""
    def __init__(self, parent, title, number):
        super().__init__(parent, bg=COLORS["bg"], highlightthickness=0, bd=0, width=300)
        self.body = tk.Frame(self, bg=COLORS["card"])
        self.body_id = self.create_window(20, 18, window=self.body, anchor="nw")
        heading = tk.Frame(self.body, bg=COLORS["card"])
        heading.pack(fill="x", pady=(0, 12))
        tk.Label(heading, text=number, bg=COLORS["input"], fg=COLORS["red"],
                 font=(FONT, 11, "bold"), padx=9, pady=6).pack(side="left", padx=(0, 10))
        label(heading, title, size=13, bold=True).pack(side="left")
        self.bind("<Configure>", self._resize)
        self.body.bind("<Configure>", self._height)

    def _height(self, event=None):
        needed = self.body.winfo_reqheight() + 36
        if int(self.cget("height")) != needed:
            self.configure(height=needed)

    def _resize(self, event):
        w, h, r = event.width - 1, event.height - 1, 22
        self.itemconfigure(self.body_id, width=max(1, w - 40))
        self.delete("shell")
        points = [r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1]
        self.create_polygon(points, smooth=True, splinesteps=24, fill=COLORS["card"],
                            outline=COLORS["border"], tags="shell")
        self.tag_lower("shell")


def hint(parent, text):
    widget = label(parent, text, secondary=True, size=10, justify="left", anchor="w")
    widget.pack(fill="x", pady=(4, 8))
    widget.bind("<Configure>", lambda e: widget.configure(wraplength=max(100, e.width-2)))
    return widget


def field(parent, title, variable, values=None, readonly=True):
    label(parent, title, secondary=True, anchor="w").pack(fill="x", pady=(5, 5))
    if values is None:
        widget = tk.Entry(parent, textvariable=variable, bg=COLORS["input"],
                          fg=COLORS["text"], insertbackground=COLORS["text"],
                          relief="flat", highlightthickness=2,
                          highlightbackground=COLORS["border"], highlightcolor=COLORS["red"],
                          font=(FONT, 11))
        widget.pack(fill="x", ipady=10, pady=(0, 8))
    else:
        widget = ttk.Combobox(parent, textvariable=variable, values=values,
                              state="readonly" if readonly else "normal", width=12)
        widget.pack(fill="x", pady=(0, 8))
    return widget


def toggle(parent, title, variable):
    row = tk.Frame(parent, bg=COLORS["card"])
    row.pack(fill="x", pady=4)
    control = tk.Checkbutton(row, text=title, variable=variable, anchor="w",
                            bg=COLORS["card"], fg=COLORS["text"],
                            activebackground=COLORS["card"], activeforeground=COLORS["text"],
                            selectcolor=COLORS["input"], font=(FONT, 11),
                            highlightcolor=COLORS["red"], highlightbackground=COLORS["card"],
                            highlightthickness=2, bd=0, pady=10, padx=4, takefocus=True)
    control.pack(fill="x")
    control.bind("<Configure>", lambda e: control.configure(wraplength=max(100, e.width-45)))
    return control


class Menu:
    def __init__(self, window):
        self.window = window
        apply_theme(window)
        window.title("MouthClick · Teletón Labs")
        window.resizable(True, True)
        sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
        width, height = min(1080, sw-60), min(820, sh-90)
        window.geometry(f"{width}x{height}+{max(0,(sw-width)//2)}+{max(0,(sh-height)//2-25)}")
        window.minsize(min(480, sw-60), min(420, sh-90))
        header = tk.Frame(window, bg=COLORS["panel"], padx=26, pady=18)
        header.pack(fill="x")
        # Text identity: reserved space for an official asset, no invented logo.
        brand = tk.Frame(header, bg=COLORS["panel"])
        brand.pack(anchor="w")
        label(brand, "Teletón", size=14, bold=True).pack(side="left")
        tk.Label(brand, text=" Labs", bg=COLORS["panel"], fg=COLORS["red"],
                 font=(FONT, 14)).pack(side="left")
        label(header, "MouthClick", size=28, bold=True).pack(anchor="w", pady=(8,0))
        label(header, "Tecnología de asistencia · Control accesible del computador",
              secondary=True, size=10, wraplength=420, justify="left").pack(anchor="w", pady=(3,0))
        self.footer = tk.Frame(window, bg=COLORS["panel"], padx=22, pady=12)
        self.footer.pack(side="bottom", fill="x")
        outer = tk.Frame(window, bg=COLORS["bg"])
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, bg=COLORS["bg"], bd=0, highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.content = tk.Frame(self.canvas, bg=COLORS["bg"])
        self.content_id = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.cards = []
        self.columns = 0
        self.canvas.bind("<Configure>", self._layout)
        window.bind("<MouseWheel>", self._wheel, add="+")
        window.bind("<FocusIn>", self._focus, add="+")

    def card(self, title):
        card = Card(self.content, title, f"{len(self.cards)+1:02}")
        self.cards.append(card)
        self.columns = 0
        return card.body

    def _layout(self, event):
        self.canvas.itemconfigure(self.content_id, width=event.width)
        # Font-relative breakpoint also responds to Windows text scaling.
        columns = 2 if event.width >= self.window.winfo_fpixels("1i") * 8.2 else 1
        if columns != self.columns:
            self.columns = columns
            for col in range(2):
                self.content.columnconfigure(col, weight=1 if col < columns else 0, uniform="cards")
            for i, card in enumerate(self.cards):
                card.grid(row=i//columns, column=i%columns, sticky="new", padx=12, pady=10)

    def _wheel(self, event):
        if not isinstance(event.widget, ttk.Combobox):
            self.canvas.yview_scroll(-int(event.delta/120), "units")

    def _focus(self, event):
        widget = event.widget
        if not str(widget).startswith(str(self.content) + "."):
            return
        self.window.update_idletasks()
        y = widget.winfo_rooty() - self.content.winfo_rooty()
        top = self.canvas.canvasy(0)
        bottom = top + self.canvas.winfo_height()
        if y < top or y + widget.winfo_height() > bottom:
            total = max(1, self.content.winfo_height())
            self.canvas.yview_moveto(max(0, y-24)/total)

    def finish(self, start, shortcuts):
        help_card = self.card("Durante el uso")
        hint(help_card, shortcuts)
        hint(help_card, "Tab: siguiente control · Mayús + Tab: anterior · Espacio: activar opción")
        tk.Label(self.footer, text="●  CONFIGURACIÓN · Control sin iniciar",
                 bg="#30271A", fg=COLORS["amber"], font=(FONT, 10),
                 padx=12, pady=5).pack(anchor="w", pady=(0,8))
        button(self.footer, "Comenzar control  →", start, primary=True).pack(fill="x")
        self.window.update_idletasks()
        self._layout(type("Size", (), {"width": self.canvas.winfo_width()})())
        # Native caption keeps Windows move/resize, keyboard and system-menu behavior.
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
            enabled = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
        except (AttributeError, OSError):
            pass


def style_floating(root):
    """Recolor existing floating widgets without replacing commands or bindings."""
    root.configure(bg=COLORS["bg"])
    def visit(widget):
        if isinstance(widget, tk.Button):
            widget.configure(bg=COLORS["input"], fg=COLORS["text"],
                             activebackground=COLORS["border"], activeforeground=COLORS["text"],
                             relief="flat", bd=0, highlightthickness=1,
                             highlightbackground=COLORS["border"], highlightcolor=COLORS["red"])
        elif isinstance(widget, tk.Entry):
            widget.configure(bg=COLORS["input"], fg=COLORS["text"], insertbackground=COLORS["text"])
        elif isinstance(widget, (tk.Frame, tk.Label)):
            widget.configure(bg=COLORS["panel"])
            if isinstance(widget, tk.Label):
                widget.configure(fg=COLORS["text"])
        for child in widget.winfo_children():
            visit(child)
    visit(root)


def draw_status(frame, text, state):
    """Presentation only: preserve frame dimensions and camera click coordinates."""
    import cv2
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    color = (149, 217, 100) if state == "success" else (120, 208, 255)
    height, width = frame.shape[:2]
    scale = min(0.55, max(0.3, width / 1200))
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = max(0, width-tw-30), max(0, height-65)
    cv2.rectangle(frame, (x, y), (width-8, y+32), (32, 18, 12), -1)
    cv2.rectangle(frame, (x, y), (width-8, y+32), color, 1)
    cv2.putText(frame, text, (x+10, y+21), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


class ActionsBubble(tk.Toplevel):
    """Compact access pill and rounded panel; keeps native actionable buttons."""
    def __init__(self, master, items, position, remember, schedule, cancel):
        super().__init__(master)
        self.withdraw()
        self.title("MouthClick Acciones")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#010203")
        self.attributes("-transparentcolor", "#010203")
        self.remember, self.schedule, self.cancel = remember, schedule, cancel
        self.expanded = False
        self.factor = max(1.0, float(self.tk.call("tk", "scaling"))/1.3333)
        self.factor = min(self.factor, (self.winfo_screenwidth()-32)/340,
                          (self.winfo_screenheight()-48)/370)
        self.px = lambda value: round(value*self.factor)
        self.position = position or (self.winfo_screenwidth()-self.px(158)-24, 90)
        self.shell = tk.Canvas(self, bg="#010203", bd=0, highlightthickness=0)
        self.shell.pack(fill="both", expand=True)
        self.shell.bind("<Configure>", self._paint)
        self.pill = button(self.shell, "☰  Accesos", self.expand)
        self.pill.configure(bg=COLORS["card"], highlightbackground=COLORS["card"], padx=0, pady=0)
        self.panel = tk.Frame(self.shell, bg=COLORS["card"])
        header = tk.Frame(self.panel, bg=COLORS["card"])
        header.pack(fill="x", pady=(0,self.px(10)))
        label(header, "MouthClick", size=14, bold=True).pack(anchor="w")
        label(header, "ACCESOS RÁPIDOS", size=9, secondary=True).pack(anchor="w", pady=(3,0))
        grid = tk.Frame(self.panel, bg=COLORS["card"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0,1), weight=1, uniform="actions")
        titles = {"Esc":"Liberar · Esc", "Click":"Clic izquierdo", "Derecho":"Clic derecho",
                  "Drag":"Arrastrar", "Teclado":"Teclado", "Calib":"Calibrar guiño", "Centro":"Centrar cursor"}
        self.action_buttons = []
        for i, (title, command) in enumerate(items):
            b = button(grid, titles.get(title,title), command, primary=(title == "Teclado"))
            b.configure(padx=4, pady=7, font=(FONT,10,"bold"))
            b.grid(row=i//2, column=i%2, sticky="nsew", padx=3, pady=4)
            grid.rowconfigure(i//2, weight=1)
            self.action_buttons.append(b)
        close = button(grid, "Contraer  ↑", self.collapse_now)
        close.configure(padx=4, pady=7, font=(FONT,10,"bold"))
        close.grid(row=3,column=1,sticky="nsew",padx=3,pady=4)
        hint(self.panel, "Arrastrá el encabezado para mover")
        self.bind("<Enter>", lambda e: self.cancel(), add="+")
        self.bind("<Leave>", self._leave, add="+")
        self.pill.bind("<Enter>", lambda e: self.expand(), add="+")
        for target in (self.pill, header, *header.winfo_children()):
            target.bind("<ButtonPress-1>", self._drag_start, add="+")
            target.bind("<B1-Motion>", self._drag, add="+")
        self.collapse_now()
        self.deiconify()

    def _paint(self, event):
        w,h,r=event.width-1,event.height-1,self.px(22)
        self.shell.delete("surface")
        self.shell.create_polygon(r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1,
                                  smooth=True,splinesteps=24,fill=COLORS["card"],
                                  outline=COLORS["border"],width=1,tags="surface")
        self.shell.tag_lower("surface")

    def _geometry(self, width, height):
        width,height=self.px(width),self.px(height)
        x,y=self.position
        x=max(0,min(x,self.winfo_screenwidth()-width))
        y=max(0,min(y,self.winfo_screenheight()-height-40))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.position=(x,y)
        self.remember(x,y)

    def expand(self):
        self.cancel()
        if self.expanded:
            return
        self.expanded=True
        self.pill.place_forget()
        self._geometry(340,370)
        self.panel.place(x=self.px(16),y=self.px(16),width=self.px(308),height=self.px(338))

    def collapse_now(self):
        self.cancel()
        self.expanded=False
        self.panel.place_forget()
        self._geometry(158,62)
        self.pill.place(x=self.px(12),y=self.px(8),width=self.px(134),height=self.px(46))

    def _leave(self, event):
        x,y=self.winfo_pointerxy()
        if not (self.winfo_rootx() <= x < self.winfo_rootx()+self.winfo_width()
                and self.winfo_rooty() <= y < self.winfo_rooty()+self.winfo_height()):
            self.schedule()

    def _drag_start(self,event):
        self.drag_offset=(event.x_root-self.winfo_x(),event.y_root-self.winfo_y())

    def _drag(self,event):
        self.cancel()
        dx,dy=self.drag_offset
        self.position=(event.x_root-dx,event.y_root-dy)
        self._geometry(340 if self.expanded else 158,370 if self.expanded else 62)
