import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageOps

APP_TITLE = "NDS Icon Maker"
NDS_SIZE = 32
TRANSPARENT_RGB = (255, 0, 255)

BG = "#111315"
PANEL = "#1A1D21"
PANEL_2 = "#22262B"
TEXT = "#F4F4F5"
MUTED = "#A1A1AA"
ACCENT = "#6EA8FE"
ACCENT_HOVER = "#8BBAFF"
SUCCESS = "#62D394"
BORDER = "#30343A"

class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, width=180, height=46, accent=True):
        super().__init__(master, width=width, height=height, bg=master["bg"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.accent = accent
        self.normal = ACCENT if accent else PANEL_2
        self.hover = ACCENT_HOVER if accent else "#2C3137"
        self._draw(self.normal)
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self._draw(self.hover))
        self.bind("<Leave>", lambda e: self._draw(self.normal))

    def _draw(self, color):
        self.delete("all")
        r = 14
        w, h = self.width, self.height
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        self.create_text(w/2, h/2, text=self.text, fill="#0B0D10" if self.accent else TEXT,
                         font=("Segoe UI Semibold", 11))

def build_palette_from_opaque(img_rgba):
    opaque = [p[:3] for p in img_rgba.getdata() if p[3] > 8]
    if not opaque:
        return [(0, 0, 0)] * 15

    strip = Image.new("RGB", (len(opaque), 1))
    strip.putdata(opaque)
    q = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    raw = q.getpalette()[:45]
    colors = [tuple(raw[i:i+3]) for i in range(0, len(raw), 3)]

    while len(colors) < 15:
        colors.append(colors[-1] if colors else (0, 0, 0))
    return colors[:15]

def nearest_color_index(rgb, palette):
    r, g, b = rgb
    best_i = 0
    best_d = 10**9
    for i, (pr, pg, pb) in enumerate(palette):
        d = (r-pr)*(r-pr) + (g-pg)*(g-pg) + (b-pb)*(b-pb)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def convert_to_nds_indices(source):
    rgba = source.convert("RGBA")

    # Keep aspect ratio, nearest-neighbor for crisp small icons.
    rgba.thumbnail((28, 28), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (NDS_SIZE, NDS_SIZE), (255, 255, 255, 0))
    x = (NDS_SIZE - rgba.width) // 2
    y = (NDS_SIZE - rgba.height) // 2
    canvas.alpha_composite(rgba, (x, y))

    colors = build_palette_from_opaque(canvas)
    palette = [TRANSPARENT_RGB] + colors

    indices = []
    preview = Image.new("RGBA", (NDS_SIZE, NDS_SIZE), (255, 255, 255, 0))
    out = preview.load()
    pix = canvas.load()

    for yy in range(NDS_SIZE):
        row = []
        for xx in range(NDS_SIZE):
            r, g, b, a = pix[xx, yy]
            if a <= 8:
                idx = 0
                out[xx, yy] = (0, 0, 0, 0)
            else:
                idx = 1 + nearest_color_index((r, g, b), colors)
                pr, pg, pb = palette[idx]
                out[xx, yy] = (pr, pg, pb, 255)
            row.append(idx)
        indices.append(row)

    return palette, indices, preview

def write_bmp_4bpp(path, palette, indices):
    width = height = NDS_SIZE
    row_bytes = ((width + 1) // 2 + 3) & ~3
    pixel_data_size = row_bytes * height
    offset = 14 + 40 + 16 * 4
    file_size = offset + pixel_data_size

    data = bytearray()

    # BITMAPFILEHEADER
    data += b"BM"
    data += file_size.to_bytes(4, "little")
    data += (0).to_bytes(2, "little")
    data += (0).to_bytes(2, "little")
    data += offset.to_bytes(4, "little")

    # BITMAPINFOHEADER
    data += (40).to_bytes(4, "little")
    data += width.to_bytes(4, "little", signed=True)
    data += height.to_bytes(4, "little", signed=True)
    data += (1).to_bytes(2, "little")
    data += (4).to_bytes(2, "little")  # 4 bpp
    data += (0).to_bytes(4, "little")  # BI_RGB
    data += pixel_data_size.to_bytes(4, "little")
    data += (2835).to_bytes(4, "little", signed=True)
    data += (2835).to_bytes(4, "little", signed=True)
    data += (16).to_bytes(4, "little")
    data += (16).to_bytes(4, "little")

    # Palette: BGRA
    pal = list(palette[:16])
    while len(pal) < 16:
        pal.append((0, 0, 0))
    for r, g, b in pal:
        data += bytes((b, g, r, 0))

    # Bottom-up rows, two pixels per byte.
    for y in range(height - 1, -1, -1):
        row = bytearray()
        for x in range(0, width, 2):
            hi = indices[y][x] & 0x0F
            lo = indices[y][x+1] & 0x0F
            row.append((hi << 4) | lo)
        while len(row) < row_bytes:
            row.append(0)
        data += row

    Path(path).write_bytes(data)

def checkerboard(size=320, cell=20):
    im = Image.new("RGB", (size, size), "#D9D9D9")
    p = im.load()
    a = (224, 224, 224)
    b = (196, 196, 196)
    for y in range(size):
        for x in range(size):
            p[x, y] = a if ((x // cell) + (y // cell)) % 2 == 0 else b
    return im

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x560")
        self.minsize(720, 520)
        self.configure(bg=BG)

        self.source_path = None
        self.source_image = None
        self.palette = None
        self.indices = None
        self.preview_image = None
        self.tk_preview = None

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=32, pady=(26, 16))

        tk.Label(header, text="NDS Icon Maker", bg=BG, fg=TEXT,
                 font=("Segoe UI Semibold", 22)).pack(anchor="w")
        tk.Label(header, text="PNG → icon.bmp Nintendo DS • 32×32 • 16 colori • 4bpp",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(0, 28))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(left, text="SORGENTE", bg=PANEL, fg=MUTED,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=20, pady=(18, 10))

        self.source_box = tk.Frame(left, bg=PANEL_2, height=250)
        self.source_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.source_box.pack_propagate(False)

        self.source_label = tk.Label(
            self.source_box,
            text="Nessuna immagine\nselezionata",
            bg=PANEL_2, fg=MUTED,
            font=("Segoe UI", 13),
            justify="center"
        )
        self.source_label.pack(expand=True)

        choose = RoundedButton(left, "Scegli PNG", self.choose_png, width=180, height=44, accent=False)
        choose.pack(pady=(0, 20))

        tk.Label(right, text="ANTEPRIMA NDS", bg=PANEL, fg=MUTED,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=20, pady=(18, 10))

        self.preview_box = tk.Frame(right, bg=PANEL_2, height=250)
        self.preview_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.preview_box.pack_propagate(False)

        self.preview_label = tk.Label(
            self.preview_box,
            text="32×32\n4bpp",
            bg=PANEL_2, fg=MUTED,
            font=("Segoe UI", 13),
            justify="center"
        )
        self.preview_label.pack(expand=True)

        self.export_btn = RoundedButton(right, "Esporta icon.bmp", self.export_bmp,
                                        width=190, height=44, accent=True)
        self.export_btn.pack(pady=(0, 20))

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=32, pady=(0, 20))
        self.status = tk.Label(footer, text="Pronto", bg=BG, fg=MUTED,
                               font=("Segoe UI", 9))
        self.status.pack(anchor="w")

    def choose_png(self):
        path = filedialog.askopenfilename(
            title="Scegli un'immagine PNG",
            filetypes=[("PNG", "*.png"), ("Immagini", "*.png;*.jpg;*.jpeg;*.webp"), ("Tutti i file", "*.*")]
        )
        if not path:
            return

        try:
            self.source_path = Path(path)
            self.source_image = Image.open(path).convert("RGBA")
            self.palette, self.indices, self.preview_image = convert_to_nds_indices(self.source_image)
            self._show_source()
            self._show_preview()
            self.status.config(text=f"Caricato: {self.source_path.name}")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Impossibile aprire l'immagine.\n\n{exc}")

    def _show_source(self):
        img = self.source_image.copy()
        img.thumbnail((250, 250), Image.Resampling.LANCZOS)
        bg = checkerboard(250, 16).convert("RGBA")
        x = (250 - img.width) // 2
        y = (250 - img.height) // 2
        bg.alpha_composite(img, (x, y))
        self.tk_source = ImageTk.PhotoImage(bg.convert("RGB"))
        self.source_label.config(image=self.tk_source, text="")

    def _show_preview(self):
        scaled = self.preview_image.resize((256, 256), Image.Resampling.NEAREST)
        bg = checkerboard(256, 16).convert("RGBA")
        bg.alpha_composite(scaled)
        self.tk_preview = ImageTk.PhotoImage(bg.convert("RGB"))
        self.preview_label.config(image=self.tk_preview, text="")

    def export_bmp(self):
        if self.indices is None or self.palette is None:
            messagebox.showinfo(APP_TITLE, "Prima scegli un'immagine PNG.")
            return

        default_name = "icon.bmp"
        path = filedialog.asksaveasfilename(
            title="Salva icona Nintendo DS",
            defaultextension=".bmp",
            initialfile=default_name,
            filetypes=[("Bitmap Nintendo DS", "*.bmp")]
        )
        if not path:
            return

        try:
            write_bmp_4bpp(path, self.palette, self.indices)
            self.status.config(text=f"Creato: {Path(path).name}", fg=SUCCESS)
            messagebox.showinfo(
                APP_TITLE,
                "Icona creata correttamente.\n\n"
                "Formato: 32×32, 16 colori, BMP 4bpp."
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Errore durante l'esportazione.\n\n{exc}")

if __name__ == "__main__":
    App().mainloop()
