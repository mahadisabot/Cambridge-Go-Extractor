import customtkinter as ctk
import threading
import os
from tkinter import messagebox
from PIL import Image
from cambridge_downloader import CambridgeDownloader

# Configuration
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

import json

CONFIG_FILE = "user_config.json"

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, client, on_success):
        super().__init__(master)
        self.client = client
        self.on_success = on_success
        
        # UI Elements
        self.label_title = ctk.CTkLabel(self, text="Cambridge Downloader", font=("Roboto Medium", 24))
        self.label_title.pack(pady=30)

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Username / Email", width=300)
        self.entry_user.pack(pady=10)

        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Password", show="*", width=300)
        self.entry_pass.pack(pady=10)
        
        # Remember Me
        self.remember_var = ctk.BooleanVar(value=True)
        self.chk_remember = ctk.CTkCheckBox(self, text="Remember Me", variable=self.remember_var)
        self.chk_remember.pack(pady=5)

        self.btn_login = ctk.CTkButton(self, text="Login", command=self.handle_login, width=300)
        self.btn_login.pack(pady=20)
        
        # Offline Mode Toggle
        self.switch_var = ctk.StringVar(value="on")
        self.switch = ctk.CTkSwitch(self, text="Use Online Mode", command=self.toggle_mode,
                                   variable=self.switch_var, onvalue="on", offvalue="off")
        self.switch.pack(pady=10)
        
        self.label_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.label_status.pack(pady=5)
        
        # Check for saved credentials
        self.check_saved_login()
        
        # Initial Mode
        self.toggle_mode()

    def check_saved_login(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get("username") and data.get("password"):
                        self.entry_user.insert(0, data["username"])
                        self.entry_pass.insert(0, data["password"])
                        self.remember_var.set(True)
                        # Auto-click login
                        self.after(500, self.handle_login)
            except: 
                pass

    def toggle_mode(self):
        is_online = (self.switch_var.get() == "on")
        self.client.set_mode(is_online)
        if is_online:
            self.entry_user.configure(state="normal")
            self.entry_pass.configure(state="normal")
            self.btn_login.configure(state="normal", text="Login")
        else:
            self.entry_user.configure(state="disabled")
            self.entry_pass.configure(state="disabled")
            self.btn_login.configure(state="normal", text="Skip Login (Offline Mode)")

    def handle_login(self):
        if self.switch_var.get() == "off":
            # Offline Mode -> Skip Auth
            self.on_success()
            return

        user = self.entry_user.get()
        password = self.entry_pass.get()
        
        if not user or not password:
            self.label_status.configure(text="Please enter credentials", text_color="red")
            return

        self.btn_login.configure(state="disabled", text="Logging in...")
        self.label_status.configure(text="Authenticating...", text_color="white")
        
        threading.Thread(target=self._login_thread, args=(user, password)).start()

    def _login_thread(self, user, password):
        success, message = self.client.login(user, password)
        self.after(0, lambda: self._post_login(success, message, user, password))

    def _post_login(self, success, message, user, password):
        self.btn_login.configure(state="normal", text="Login")
        if success:
            self.label_status.configure(text=f"Success! {message}", text_color="green")
            
            # Save Credentials if "Remember Me"
            if self.remember_var.get():
                try:
                    with open(CONFIG_FILE, 'w') as f:
                        json.dump({"username": user, "password": password}, f)
                except: pass
            else:
                 if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
            
            self.on_success()
        else:
            self.label_status.configure(text=f"Error: {message}", text_color="red")


class LibraryFrame(ctk.CTkFrame):
    def __init__(self, master, client, on_logout):
        super().__init__(master)
        self.client = client
        self.on_logout = on_logout
        self.books = []
        self.check_vars = {} # {book_id: IntVar}
        self.is_downloading = False
        
        # Top Bar
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=20, pady=10)
        
        self.label_title = ctk.CTkLabel(self.top_bar, text="My Library", font=("Roboto Medium", 20))
        self.label_title.pack(side="left")
        
        # Directory Control
        self.btn_dir = ctk.CTkButton(self.top_bar, text="Set Output Folder", command=self.choose_directory, width=120)
        self.btn_dir.pack(side="right", padx=10)
        
        self.btn_refresh = ctk.CTkButton(self.top_bar, text="Refresh", command=self.refresh_library, width=100)
        self.btn_refresh.pack(side="right", padx=10)
        
        self.btn_logout = ctk.CTkButton(self.top_bar, text="Logout", command=self.logout, width=80, fg_color="red", hover_color="darkred")
        self.btn_logout.pack(side="right")
        
        # Selection Bar
        self.select_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.select_bar.pack(fill="x", padx=20, pady=(0,5))
        
        self.btn_select_all = ctk.CTkButton(self.select_bar, text="Select All", width=80, height=24, command=self.select_all)
        self.btn_select_all.pack(side="left")
        
        self.btn_download_selected = ctk.CTkButton(self.select_bar, text="Download Selected", width=150, height=24, 
                                                  fg_color="green", hover_color="darkgreen", command=self.download_selected)
        self.btn_download_selected.pack(side="right")
        
        # Book List
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Available Books")
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Status Bar / Progress
        self.status_bar = ctk.CTkFrame(self, height=40)
        self.status_bar.pack(fill="x", padx=20, pady=10)
        
        self.progress = ctk.CTkProgressBar(self.status_bar)
        self.progress.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.progress.set(0)
        
        self.label_status = ctk.CTkLabel(self.status_bar, text="Ready")
        self.label_status.pack(side="right", padx=10)
        
        # Auto load
        self.refresh_library()

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            self.on_logout()

    def choose_directory(self):
        new_dir = ctk.filedialog.askdirectory(title="Select Download Folder")
        if new_dir:
            self.client.set_download_dir(new_dir)
            messagebox.showinfo("Folder Set", f"Downloads will be saved to:\n{new_dir}")

    def refresh_library(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.check_vars = {}

        self.label_status.configure(text="Scanning library...")
        self.update()
        
        # Thread scan
        threading.Thread(target=self._scan_thread).start()
        
    def _scan_thread(self):
        self.books = self.client.scan_library()
        self.after(0, self._render_books)

    def _render_books(self):
        self.label_status.configure(text=f"Found {len(self.books)} books")
        
        if not self.books:
             ctk.CTkLabel(self.scrollable_frame, text="No books found.").pack(pady=20)
             return

        for book in self.books:
            self._create_book_card(book)

    def _create_book_card(self, book):
        card = ctk.CTkFrame(self.scrollable_frame)
        card.pack(fill="x", pady=5)
        
        # Checkbox
        var = ctk.IntVar()
        self.check_vars[book['id']] = var
        chk = ctk.CTkCheckBox(card, text="", variable=var, width=24)
        chk.pack(side="left", padx=(10, 0))
        
        # Cover Image (if available)
        if book.get('cover_local') and os.path.exists(book['cover_local']):
            try:
                # Load and Resize
                pil_img = Image.open(book['cover_local'])
                # Maintain Aspect Ratio roughly
                pil_img.thumbnail((60, 90)) 
                cover_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                lbl_img = ctk.CTkLabel(card, text="", image=cover_img)
                lbl_img.pack(side="left", padx=10, pady=5)
            except:
                pass # Fallback to no image
        
        # Info Column
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # Title
        title_label = ctk.CTkLabel(info_frame, text=book['title'], font=("Roboto Medium", 14), anchor="w")
        title_label.pack(anchor="w", pady=(5,0))
        
        # Metadata
        status = book.get('status', 'Unknown')
        color = "green" if status == "Cloud" else "orange"
        meta_text = f"Status: {status}"
        if book.get('offline'):
             size_mb = book.get('size', 0) / (1024 * 1024)
             meta_text += f" | Size: {size_mb:.1f} MB"
             
        meta_lbl = ctk.CTkLabel(info_frame, text=meta_text, text_color="gray", font=("Roboto", 12))
        meta_lbl.pack(anchor="w")

    def select_all(self):
        # Toggle based on first item
        if not self.check_vars: return
        new_val = 1 if list(self.check_vars.values())[0].get() == 0 else 0
        for v in self.check_vars.values():
            v.set(new_val)

    def download_selected(self):
        if self.is_downloading:
             messagebox.showwarning("Busy", "Download in progress.")
             return

        selected_ids = [bid for bid, var in self.check_vars.items() if var.get() == 1]
        
        if not selected_ids:
            messagebox.showinfo("None Selected", "Please select books to download.")
            return

        msg = f"Download {len(selected_ids)} books?"
        if not messagebox.askyesno("Confirm", msg):
            return
            
        self.is_downloading = True
        self.label_status.configure(text="Starting Bulk Download...")
        self.progress.set(0)
        
        threading.Thread(target=self._bulk_download_thread, args=(selected_ids,)).start()

    def _bulk_download_thread(self, book_ids):
        total = len(book_ids)
        success_count = 0
        
        for idx, bid in enumerate(book_ids):
            # Update Status
            title = next((b['title'] for b in self.books if b['id'] == bid), bid)
            self.after(0, lambda t=title, i=idx: self.label_status.configure(text=f"Downloading ({i+1}/{total}): {t}..."))
            
            # Callback for per-book progress (optional, maybe just show overall items)
            # For simpler UI, we just update progress bar per book completion
            def sub_prog(p):
                # Calculate global progress: ((idx * 100) + p) / (total * 100)
                global_p = ((idx * 100) + p) / (total * 100)
                self.after(0, lambda: self.progress.set(global_p))
            
            success, _ = self.client.download_book(bid, progress_callback=sub_prog)
            if success: success_count += 1
            
        self.after(0, lambda: self._post_bulk(success_count, total))

    def _post_bulk(self, success_count, total):
        self.is_downloading = False
        self.progress.set(1)
        self.label_status.configure(text=f"Completed {success_count}/{total}")
        messagebox.showinfo("Batch Complete", f"Downloaded {success_count} of {total} books.")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cambridge Downloader")
        self.geometry("1000x800")
        
        self.client = CambridgeDownloader() # Using the new manager
        
        self.login_frame = LoginFrame(self, self.client, self.show_library)
        self.library_frame = None
        
        self.login_frame.pack(fill="both", expand=True)
        
        # Handle close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_library(self):
        if self.login_frame: self.login_frame.pack_forget()
        
        # Destroy old library frame if exists to refresh
        if self.library_frame:
            self.library_frame.destroy()
            
        self.library_frame = LibraryFrame(self, self.client, self.logout)
        self.library_frame.pack(fill="both", expand=True)

    def logout(self):
        if self.library_frame:
            self.library_frame.pack_forget()
            self.library_frame.destroy()
            self.library_frame = None
            
        self.client.use_online = False # Reset mode
        self.login_frame = LoginFrame(self, self.client, self.show_library)
        self.login_frame.pack(fill="both", expand=True)
        
    def on_closing(self):
        self.destroy()
        os._exit(0) # Ensure threads kill

if __name__ == "__main__":
    app = App()
    app.mainloop()
