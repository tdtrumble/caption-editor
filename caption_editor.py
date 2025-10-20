import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


class CaptionEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Caption Editor")
        self.master.geometry("900x900")

        # === Image Display ===
        self.image_label = tk.Label(master, bg="#222")
        self.image_label.pack(fill="both", expand=True)

        # === Caption Text Box ===
        self.text = tk.Text(master, height=5, wrap="word", font=("Arial", 12))
        self.text.pack(fill="x", padx=10, pady=10)

        # === Button Controls ===
        button_frame = tk.Frame(master)
        button_frame.pack(fill="x", pady=5)

        tk.Button(button_frame, text="◀ Prev", width=10, command=self.prev_image).pack(side="left", padx=5)
        tk.Button(button_frame, text="Save", width=10, command=self.save_caption).pack(side="left", padx=5)
        tk.Button(button_frame, text="Next ▶", width=10, command=self.next_image).pack(side="left", padx=5)
        tk.Button(button_frame, text="Open Folder", width=12, command=self.load_folder).pack(side="right", padx=5)

        # === Bind keys ===
        master.bind("<Left>", lambda e: self.prev_image())
        master.bind("<Right>", lambda e: self.next_image())
        master.bind("<Control-s>", lambda e: self.save_caption())

        # === Internal state ===
        self.folder = None
        self.files = []
        self.index = 0
        self.tk_img = None

    def load_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if not folder:
            return

        self.folder = folder
        self.files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        )
        if not self.files:
            messagebox.showerror("No Images Found", "No image files found in this folder.")
            return

        self.index = 0
        self.show_image()

    def show_image(self):
        if not self.files:
            return

        img_path = os.path.join(self.folder, self.files[self.index])
        txt_path = os.path.splitext(img_path)[0] + ".txt"

        # === Load image ===
        try:
            img = Image.open(img_path)
            img.thumbnail((850, 750))
            self.tk_img = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_img)
        except Exception as e:
            self.image_label.config(text=f"Error loading image: {e}", image="", compound="center")

        # === Load caption ===
        caption = ""
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                caption = f.read()

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, caption)

        # === Update title ===
        self.master.title(f"{self.files[self.index]} ({self.index + 1}/{len(self.files)})")

    def save_caption(self):
        if not self.files:
            return

        txt_path = os.path.splitext(os.path.join(self.folder, self.files[self.index]))[0] + ".txt"
        caption = self.text.get("1.0", tk.END).strip()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(caption)
        self.master.title(f"Saved: {self.files[self.index]} ({self.index + 1}/{len(self.files)})")

    def next_image(self):
        if self.files and self.index < len(self.files) - 1:
            self.save_caption()
            self.index += 1
            self.show_image()

    def prev_image(self):
        if self.files and self.index > 0:
            self.save_caption()
            self.index -= 1
            self.show_image()


if __name__ == "__main__":
    root = tk.Tk()
    app = CaptionEditor(root)
    root.mainloop()
