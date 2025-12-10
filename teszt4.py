import customtkinter as ctk
from tkinter import filedialog, Canvas, messagebox, simpledialog
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance, ImageDraw

# Alapbeállítások a modern kinézethez
ctk.set_appearance_mode("Dark")  # Témák: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Témák: "blue", "green", "dark-blue"

class KepSzerkesztoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Ablak beállításai
        self.title("Modern Python Képszerkesztő")
        self.geometry("1100x700")

        # Állapotváltozók
        self.original_image = None
        self.current_image = None
        self.display_image = None
        self.history = []  # Visszavonáshoz
        self.draw_mode = False
        self.crop_mode = False
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.brush_color = "red"
        self.brush_size = 5

        # UI Felépítése
        self.setup_ui()

    def setup_ui(self):
        # --- Bal oldali vezérlőpanel ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        # Fájlkezelés gombok
        ctk.CTkLabel(self.sidebar, text="Fájlkezelés", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        ctk.CTkButton(self.sidebar, text="Kép Megnyitása", command=self.open_image).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Mentés", command=self.save_image, fg_color="green").pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Visszavonás (Undo)", command=self.undo, fg_color="gray").pack(pady=5, padx=20)

        # Eszközök
        ctk.CTkLabel(self.sidebar, text="Eszközök", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        
        # Effektek
        self.create_sidebar_btn("Fekete-Fehér", self.filter_bw)
        self.create_sidebar_btn("Elmosás", self.filter_blur)
        self.create_sidebar_btn("Élesítés", self.filter_sharpen)
        self.create_sidebar_btn("Élénkítés", self.filter_vibrance)
        
        # Transzformációk
        ctk.CTkLabel(self.sidebar, text="Transzformáció", font=("Arial", 16, "bold")).pack(pady=(20, 10))
        self.create_sidebar_btn("Forgatás (90°)", self.rotate_image)
        self.create_sidebar_btn("Tükrözés", self.flip_image)
        self.create_sidebar_btn("Átméretezés", self.resize_image_dialog)
        
        # Különleges módok (Vágás / Rajz)
        self.crop_btn = ctk.CTkButton(self.sidebar, text="Vágás Mód: KI", command=self.toggle_crop, fg_color="#d35400")
        self.crop_btn.pack(pady=5, padx=20)

        self.draw_btn = ctk.CTkButton(self.sidebar, text="Rajzolás: KI", command=self.toggle_draw, fg_color="#8e44ad")
        self.draw_btn.pack(pady=5, padx=20)

        # --- Középső terület (Canvas) ---
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # A Canvas a kép megjelenítéséhez és a rajzoláshoz
        self.canvas = Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Egér események (rajzoláshoz és vágáshoz)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def create_sidebar_btn(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, command=command)
        btn.pack(pady=3, padx=20)
        return btn

    # --- Fájlkezelés ---
    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path:
            self.original_image = Image.open(path)
            self.current_image = self.original_image.copy()
            self.history = [] # Történet törlése új képnél
            self.show_image()

    def save_image(self):
        if self.current_image:
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")])
            if path:
                self.current_image.save(path)
                messagebox.showinfo("Siker", "Kép sikeresen elmentve!")

    def add_to_history(self):
        """Minden módosítás előtt elmentjük a jelenlegi állapotot."""
        if self.current_image:
            self.history.append(self.current_image.copy())

    def undo(self):
        if self.history:
            self.current_image = self.history.pop()
            self.show_image()
        else:
            messagebox.showinfo("Infó", "Nincs több visszavonható lépés.")

    def show_image(self):
        """A kép átméretezése a képernyőhöz és megjelenítése."""
        if self.current_image is None:
            return

        # Canvas mérete
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Ha a canvas még nem töltődött be (induláskor), adjunk alapértéket
        if canvas_width < 2: canvas_width = 800
        if canvas_height < 2: canvas_height = 600

        # Kép arányos átméretezése megjelenítéshez (thumbnail)
        img_copy = self.current_image.copy()
        img_copy.thumbnail((canvas_width, canvas_height))
        
        self.display_image = ImageTk.PhotoImage(img_copy)
        
        # Kép középre igazítása
        self.canvas.delete("all")
        x_pos = (canvas_width - self.display_image.width()) // 2
        y_pos = (canvas_height - self.display_image.height()) // 2
        
        # Fontos: eltolást (offset) tárolunk, hogy tudjuk, hol van a kép a canvason belül
        self.img_offset_x = x_pos
        self.img_offset_y = y_pos
        self.scale_factor = self.current_image.width / self.display_image.width()

        self.canvas.create_image(x_pos, y_pos, image=self.display_image, anchor="nw")

    # --- Effektek ---
    def filter_bw(self):
        if self.current_image:
            self.add_to_history()
            self.current_image = ImageOps.grayscale(self.current_image)
            self.show_image()

    def filter_blur(self):
        if self.current_image:
            self.add_to_history()
            self.current_image = self.current_image.filter(ImageFilter.BLUR)
            self.show_image()

    def filter_sharpen(self):
        if self.current_image:
            self.add_to_history()
            self.current_image = self.current_image.filter(ImageFilter.SHARPEN)
            self.show_image()
            
    def filter_vibrance(self):
        if self.current_image:
            self.add_to_history()
            enhancer = ImageEnhance.Color(self.current_image)
            self.current_image = enhancer.enhance(1.5) # +50% szaturáció
            self.show_image()

    # --- Transzformációk ---
    def rotate_image(self):
        if self.current_image:
            self.add_to_history()
            self.current_image = self.current_image.rotate(-90, expand=True)
            self.show_image()

    def flip_image(self):
        if self.current_image:
            self.add_to_history()
            self.current_image = ImageOps.mirror(self.current_image)
            self.show_image()

    def resize_image_dialog(self):
        if self.current_image:
            new_width = simpledialog.askinteger("Méretezés", "Új szélesség (pixel):", initialvalue=self.current_image.width)
            if new_width:
                aspect_ratio = self.current_image.height / self.current_image.width
                new_height = int(new_width * aspect_ratio)
                
                self.add_to_history()
                self.current_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.show_image()

    # --- Vágás (Crop) Logika ---
    def toggle_crop(self):
        self.crop_mode = not self.crop_mode
        self.draw_mode = False # Ne lehessen egyszerre rajzolni és vágni
        self.update_mode_buttons()

    # --- Rajzolás (Draw) Logika ---
    def toggle_draw(self):
        self.draw_mode = not self.draw_mode
        self.crop_mode = False 
        self.update_mode_buttons()

    def update_mode_buttons(self):
        if self.crop_mode:
            self.crop_btn.configure(text="Vágás Mód: BE", fg_color="green")
            self.canvas.config(cursor="cross")
        else:
            self.crop_btn.configure(text="Vágás Mód: KI", fg_color="#d35400")
        
        if self.draw_mode:
            self.draw_btn.configure(text="Rajzolás: BE", fg_color="green")
            self.canvas.config(cursor="pencil")
        else:
            self.draw_btn.configure(text="Rajzolás: KI", fg_color="#8e44ad")
            
        if not self.crop_mode and not self.draw_mode:
            self.canvas.config(cursor="")

    # --- Egérkezelők (Vágás és Rajzolás) ---
    def on_mouse_down(self, event):
        if self.current_image is None: return
        self.start_x = event.x
        self.start_y = event.y

        if self.draw_mode:
            self.add_to_history() # Rajzolás kezdete előtt mentés

    def on_mouse_drag(self, event):
        if self.current_image is None: return

        if self.crop_mode:
            # Téglalap frissítése a vásznon (vizuális visszajelzés)
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="white", width=2, dash=(4, 4))

        elif self.draw_mode:
            # Rajzolás a vászonra
            x1, y1 = (event.x - 1), (event.y - 1)
            x2, y2 = (event.x + 1), (event.y + 1)
            self.canvas.create_oval(x1, y1, x2, y2, fill=self.brush_color, outline=self.brush_color, width=self.brush_size)
            
            # Rajzolás a PIL képre (koordináták átszámolása)
            draw = ImageDraw.Draw(self.current_image)
            
            # Az egér koordinátát át kell számolni a valódi kép méretére
            real_x = (event.x - self.img_offset_x) * self.scale_factor
            real_y = (event.y - self.img_offset_y) * self.scale_factor
            
            r = self.brush_size * self.scale_factor / 2
            draw.ellipse((real_x - r, real_y - r, real_x + r, real_y + r), fill=self.brush_color)

    def on_mouse_up(self, event):
        if self.current_image is None: return

        if self.crop_mode and self.rect_id:
            # Vágás végrehajtása
            self.canvas.delete(self.rect_id)
            self.rect_id = None
            
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)

            # Koordináták konvertálása a valódi képméretre
            real_x1 = (x1 - self.img_offset_x) * self.scale_factor
            real_y1 = (y1 - self.img_offset_y) * self.scale_factor
            real_x2 = (x2 - self.img_offset_x) * self.scale_factor
            real_y2 = (y2 - self.img_offset_y) * self.scale_factor

            # Határok ellenőrzése
            if real_x2 > real_x1 and real_y2 > real_y1:
                self.add_to_history()
                self.current_image = self.current_image.crop((real_x1, real_y1, real_x2, real_y2))
                self.show_image()
                self.toggle_crop() # Vágás után kilépés a módból

# Alkalmazás indítása
if __name__ == "__main__":
    app = KepSzerkesztoApp()
    app.mainloop()