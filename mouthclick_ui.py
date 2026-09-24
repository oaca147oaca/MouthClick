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
    style.configure("TSpinbox", padding=8, arrowsize=22, foreground=COLORS["text"],
                    fieldbackground=COLORS["input"], background=COLORS["input"],
                    arrowcolor=COLORS["text"], bordercolor=COLORS["border"])
    style.map("TSpinbox", bordercolor=[("focus", COLORS["red"])])


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
    control.configure(cursor="hand2")
    # One toggle on release anywhere in the row, including the caption.
    control.bind("<ButtonPress-1>", lambda e: "break")
    def activate(event):
        if 0 <= event.x < control.winfo_width() and 0 <= event.y < control.winfo_height():
            control.invoke()
        return "break"
    control.bind("<ButtonRelease-1>", activate)
    row.bind("<ButtonRelease-1>", lambda e: control.invoke())
    control.bind("<Configure>", lambda e: control.configure(wraplength=max(100, e.width-45)))
    return control


class Menu:
    def __init__(self, window, title="MouthClick", subtitle="Tecnología de asistencia · Control accesible del computador"):
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
        label(header, title, size=28, bold=True).pack(anchor="w", pady=(8,0))
        label(header, subtitle,
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
                self.content.columnconfigure(col, weight=1 if col < columns else 0,
                                             uniform="cards" if col < columns else "", minsize=0)
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

    def finish(self, start, shortcuts, editing=False):
        help_card = self.card("Durante el uso")
        hint(help_card, shortcuts)
        hint(help_card, "Tab: siguiente control · Mayús + Tab: anterior · Espacio: activar opción")
        tk.Label(self.footer, text="●  CONFIGURACIÓN · Control en curso" if editing else "●  CONFIGURACIÓN · Control sin iniciar",
                 bg="#30271A", fg=COLORS["amber"], font=(FONT, 10),
                 padx=12, pady=5).pack(anchor="w", pady=(0,8))
        button(self.footer, "Guardar y aplicar  →" if editing else "Comenzar control  →", start, primary=True).pack(fill="x")
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


def compact_card(card):
    """Reduce spacing, keeping font sizes and full-width click targets."""
    ttk.Style(card).configure("Compact.TCombobox", padding=4)
    def visit(parent):
        for widget in parent.winfo_children():
            if widget.winfo_manager() == "pack":
                widget.pack_configure(pady=2)
                if isinstance(widget, (tk.Entry, ttk.Spinbox)):
                    widget.pack_configure(ipady=2)
            if isinstance(widget, tk.Checkbutton):
                widget.configure(pady=4)
            if isinstance(widget, ttk.Combobox):
                widget.configure(style="Compact.TCombobox")
            visit(widget)
    visit(card.body)


class PagedMenu:
    """Main configuration in paired cards, with no scrolling container."""
    def __init__(self, window):
        self.window = window
        apply_theme(window)
        window.title("MouthClick · Menú principal")
        scale = float(window.tk.call("tk", "scaling"))/1.3333
        window.geometry("1080x820")
        window.minsize(min(round(1000*scale),window.winfo_screenwidth()),
                       min(round(950*scale),window.winfo_screenheight()))
        header = tk.Frame(window,bg=COLORS["panel"],padx=22,pady=10)
        header.pack(fill="x")
        label(header,"Menú principal",size=22,bold=True).pack(anchor="w")
        label(header,"Perfil, gestos y movimiento · Teletón Labs",size=10,secondary=True).pack(anchor="w")
        self.footer = tk.Frame(window,bg=COLORS["panel"],padx=18,pady=10)
        self.footer.pack(side="bottom",fill="x")
        nav=tk.Frame(window,bg=COLORS["bg"],padx=18,pady=8)
        nav.pack(side="bottom",fill="x")
        self.previous=button(nav,"← Anterior",lambda:self.show_page(self.index-1))
        self.previous.pack(side="left")
        self.next=button(nav,"Siguiente →",lambda:self.show_page(self.index+1))
        self.next.pack(side="right")
        self.counter=label(nav,"",secondary=True)
        self.counter.pack(expand=True)
        self.content=tk.Frame(window,bg=COLORS["bg"])
        self.content.pack(fill="both",expand=True,padx=18,pady=8)
        self.pages=[]
        self.cards=[]
        self.index=0
        window.bind("<Alt-Left>",lambda e:self.show_page(self.index-1))
        window.bind("<Alt-Right>",lambda e:self.show_page(self.index+1))
        window.paged_menu=self

    def card(self,title):
        number=len(self.cards)
        if number%4==0:
            page=tk.Frame(self.content,bg=COLORS["bg"])
            page.columnconfigure((0,1),weight=1,uniform="cards")
            page.rowconfigure((0,1),weight=1)
            self.pages.append(page)
        card=Card(self.pages[-1],title,f"{number+1:02}")
        card.grid(row=(number%4)//2,column=number%2,sticky="nsew",padx=(0,8) if number%2==0 else (8,0),pady=5)
        self.cards.append(card)
        return card.body

    def show_page(self,index):
        if not 0<=index<len(self.pages):
            return
        for page in self.pages:
            page.pack_forget()
        self.index=index
        self.pages[index].pack(fill="both",expand=True)
        self.counter.configure(text=f"{index+1} / {len(self.pages)}")
        self.previous.configure(state="normal" if index else "disabled")
        self.next.configure(state="normal" if index<len(self.pages)-1 else "disabled")
        (self.next if index<len(self.pages)-1 else self.previous).focus_set()

    def finish(self,start,shortcuts,editing=False):
        help_body=self.card("Atajos y ayuda")
        hint(help_body,shortcuts)
        hint(help_body,"Alt + flecha izquierda/derecha: cambiar de página")
        button(self.footer,"Guardar y aplicar →" if editing else "Comenzar control →",start,primary=True).pack(fill="x")
        for card in self.cards:
            compact_card(card)
        self.show_page(0)


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
        self.panel_height = 170 + 52*((len(items)+2)//2)
        self.factor = max(1.0, float(self.tk.call("tk", "scaling"))/1.3333)
        self.factor = min(self.factor, (self.winfo_screenwidth()-32)/340,
                          (self.winfo_screenheight()-48)/self.panel_height)
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
        self.status = label(self.panel, "Buscando cara…", size=9, secondary=True, wraplength=self.px(290), justify="left")
        self.status.pack(fill="x", pady=(0,6))
        grid = tk.Frame(self.panel, bg=COLORS["card"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0,1), weight=1, uniform="actions")
        titles = {"Esc":"Liberar · Esc", "Click":"Clic izquierdo", "Derecho":"Clic derecho",
                  "Drag":"Arrastrar", "Teclado":"Teclado", "Calib":"Calibrar guiño", "Centro":"Centrar cursor", "Pausa":"Pausar", "Salir":"Salir de la app"}
        self.action_buttons = []
        self.pause_button = None
        self.mode_buttons = {}
        for i, (title, command) in enumerate(items):
            b = button(grid, titles.get(title,title), command, primary=(title == "Sensibilidades"))
            b.configure(padx=4, pady=7, font=(FONT,10,"bold"))
            b.grid(row=i//2, column=i%2, sticky="nsew", padx=3, pady=4)
            grid.rowconfigure(i//2, weight=1)
            self.action_buttons.append(b)
            if title == "Pausa":
                self.pause_button = b
            if title in ("Drag", "Oficina"):
                self.mode_buttons[title] = b
        close = button(grid, "Contraer  ↑", self.collapse_now)
        close.configure(padx=4, pady=7, font=(FONT,10,"bold"))
        close.grid(row=len(items)//2,column=len(items)%2,sticky="nsew",padx=3,pady=4)
        grid.rowconfigure(len(items)//2, weight=1)
        hint(self.panel, "Clic en encabezado: mover · otro clic: fijar")
        self.moving = False
        self.move_after = None
        self.header = header
        self.bind("<Enter>", lambda e: self.cancel(), add="+")
        self.bind("<Leave>", self._leave, add="+")
        self.pill.bind("<Enter>", lambda e: self.expand(), add="+")
        for target in (self.pill, header, *header.winfo_children()):
            target.bind("<ButtonPress-1>", self._drag_start, add="+")
            target.bind("<B1-Motion>", self._drag, add="+")
            target.bind("<ButtonRelease-1>", self._drag_end, add="+")
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
        self._geometry(340,self.panel_height)
        self.panel.place(x=self.px(16),y=self.px(16),width=self.px(308),height=self.px(self.panel_height-32))

    def collapse_now(self):
        if getattr(self, "moving", False):
            return
        self.cancel()
        self.expanded=False
        self.panel.place_forget()
        self._geometry(158,62)
        self.pill.place(x=self.px(12),y=self.px(8),width=self.px(134),height=self.px(46))

    def _leave(self, event):
        if self.moving:
            return
        x,y=self.winfo_pointerxy()
        if not (self.winfo_rootx() <= x < self.winfo_rootx()+self.winfo_width()
                and self.winfo_rooty() <= y < self.winfo_rooty()+self.winfo_height()):
            self.schedule()

    def _drag_start(self,event):
        self.was_moving = self.moving
        self.physical_drag = False
        self.press_position = (event.x_root,event.y_root)
        self.drag_offset=(event.x_root-self.winfo_x(),event.y_root-self.winfo_y())

    def _drag(self,event):
        if abs(event.x_root-self.press_position[0])+abs(event.y_root-self.press_position[1]) < 5:
            return
        self.physical_drag = True
        self.cancel()
        dx,dy=self.drag_offset
        self.position=(event.x_root-dx,event.y_root-dy)
        self._geometry(340 if self.expanded else 158,self.panel_height if self.expanded else 62)

    def _drag_end(self, event):
        if self.was_moving or self.physical_drag:
            self.stop_moving()
        else:
            self.moving = True
            self._follow_pointer()

    def _follow_pointer(self):
        if not self.moving:
            return
        self.cancel()
        x,y = self.winfo_pointerxy()
        dx,dy = self.drag_offset
        self.position = (x-dx,y-dy)
        self._geometry(340 if self.expanded else 158,self.panel_height if self.expanded else 62)
        self.move_after = self.after(30,self._follow_pointer)

    def stop_moving(self):
        self.moving = False
        if self.move_after is not None:
            self.after_cancel(self.move_after)
            self.move_after = None

    def destroy(self):
        self.stop_moving()
        super().destroy()

    def set_status(self, text):
        if self.status.cget("text") != text:
            self.status.configure(text=text)

    def set_paused(self, paused):
        if self.pause_button is not None:
            self.pause_button.configure(text="Continuar" if paused else "Pausar")
        if paused:
            self.set_status("PAUSADO · Elegí Continuar")

    def set_modes(self, drag, office):
        for key, active, title in (("Drag", drag, "Arrastre"), ("Oficina", office, "Oficina")):
            if key in self.mode_buttons:
                b = self.mode_buttons[key]
                bg = COLORS["red"] if active else COLORS["input"]
                hover = COLORS["hover"] if active else COLORS["border"]
                b.configure(text=f"{title} {'ON · salir' if active else 'OFF'}",
                            bg=bg, activebackground=hover, highlightbackground=bg)
                b.bind("<Enter>", lambda e,w=b,c=hover:w.configure(bg=c))
                b.bind("<Leave>", lambda e,w=b,c=bg:w.configure(bg=c))
