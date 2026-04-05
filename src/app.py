import customtkinter as ctk
from tkinter import filedialog, messagebox
import os, shutil, subprocess, ctypes, locale, sys # Added sys for resource_path
from PIL import Image 
import translations 

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # for PyInstaller temp folder
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

class SyrianSegoeApp(ctk.CTk):
    def __init__(self):
        super().__init__()


        # CHANGE THIS VARIABLE TO UPDATE THE FONT FOR THE ENTIRE APP IF WANTED
        self.ui_font_family = "Tahoma" 
        
        # Standardized font objects used throughout the UI
        self.font_base = ctk.CTkFont(family=self.ui_font_family, size=13)
        self.font_title = ctk.CTkFont(family=self.ui_font_family, size=32, weight="bold")
        self.font_sub = ctk.CTkFont(family=self.ui_font_family, size=14)
        self.font_bold = ctk.CTkFont(family=self.ui_font_family, size=13, weight="bold")
        self.font_small = ctk.CTkFont(family=self.ui_font_family, size=11)

        # --- Data Initialization ---
        self.latin_reg = None; self.latin_bold = None; self.latin_black = None
        self.arabic_reg = None; self.arabic_bold = None; self.arabic_black = None

        # --- Window Setup ---
        self.detect_language()
        self.title("SyrianSegoe")
        self.geometry("700x750") 

        # --- Icon Integration ---
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SyrianSegoe.App.1.0")

        if not is_admin():
            messagebox.showwarning("Admin", self.t("admin_warn", is_popup=True))

        self.run_backup()

        # --- 1. Top Bar & Language ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(10, 0))
        
        self.lang_menu = ctk.CTkOptionMenu(top_bar, values=["System Language", "English", "Türkçe", "العربية"], 
                                           command=self.change_lang_event, font=self.font_base, dropdown_font=self.font_base)
        self.lang_menu.pack(side="right")

        # --- 2. THE BANNER ---
        banner_file = os.path.join(os.path.dirname(__file__), "SyrianSegoe_Banner.png")
        if os.path.exists(banner_file):
            raw_img = Image.open(banner_file)
            self.banner_img = ctk.CTkImage(
                light_image=raw_img, 
                dark_image=raw_img, 
                size=(640, 242)
            )
            self.banner_label = ctk.CTkLabel(self, image=self.banner_img, text="")
            self.banner_label.pack(pady=(10, 5))
        else:
            self.title_label = ctk.CTkLabel(self, text=self.t("title"), font=self.font_title)
            self.title_label.pack(pady=(20, 5))

        self.sub_label = ctk.CTkLabel(self, text=self.t("sub_text"), font=self.font_sub)
        self.sub_label.pack(pady=(0, 15))


        # --- 3. Font Selection Sections ---
        self.setup_section("latin", self.t("latin_sec"))
        self.setup_section("arabic", self.t("arab_sec"))

        # --- 4. Action Buttons ---
        self.apply_btn = ctk.CTkButton(self, text=self.t("build"), fg_color="green", hover_color="darkgreen", height=50, 
                                       command=self.build_and_apply, font=self.font_bold)
        self.apply_btn.pack(pady=(35, 10))

        self.revert_btn = ctk.CTkButton(self, text=self.t("restore"), fg_color="#444", height=40, 
                                        command=self.restore_system, font=self.font_base)
        self.revert_btn.pack(pady=(0, 20))

        self.refresh_ui_text()

    def t(self, key, is_popup=False):
        return translations.get_text(key, self.current_lang, is_popup=is_popup)

    def detect_language(self):
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            lang_map = {1055: "tr", 1025: "ar", 1033: "en", 2057: "en"}
            self.current_lang = lang_map.get(lang_id, "en")
        except: self.current_lang = "en"

    def change_lang_event(self, choice):
        mapping = {"English": "en", "Türkçe": "tr", "العربية": "ar"}
        if choice == "System Language": self.detect_language()
        else: self.current_lang = mapping[choice]
        self.refresh_ui_text()

    def refresh_ui_text(self):
        if hasattr(self, 'title_label'): self.title_label.configure(text=self.t("title"))
        self.sub_label.configure(text=self.t("sub_text"))
        self.apply_btn.configure(text=self.t("build"))
        self.revert_btn.configure(text=self.t("restore"))
        self.latin_sec_lbl.configure(text=self.t("latin_sec"))
        self.arabic_sec_lbl.configure(text=self.t("arabic_sec"))
        for lang in ["latin", "arabic"]:
            getattr(self, f"{lang}_browse_btn").configure(text=self.t("browse").format(lang.capitalize()))
            getattr(self, f"{lang}_clear_btn").configure(text=self.t("clear"))
            getattr(self, f"{lang}_bold_btn").configure(text=self.t("bold"))
            getattr(self, f"{lang}_black_btn").configure(text=self.t("black"))
            if not getattr(self, f"{lang}_reg"):
                getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"))

    def setup_section(self, lang, title):
        section_frame = ctk.CTkFrame(self, fg_color="transparent"); section_frame.pack(pady=5, fill="x", padx=40)
        header_frame = ctk.CTkFrame(section_frame, fg_color="transparent"); header_frame.pack(fill="x")
        title_lbl = ctk.CTkLabel(header_frame, text=title, font=self.font_bold); title_lbl.pack(side="left")
        setattr(self, f"{lang}_sec_lbl", title_lbl)
        clear_btn = ctk.CTkButton(header_frame, text=self.t("clear"), width=60, height=20, fg_color="#882222", 
                                  command=lambda l=lang: self.unload_section(l), font=self.font_base)
        clear_btn.pack(side="right"); setattr(self, f"{lang}_clear_btn", clear_btn)
        browse_btn = ctk.CTkButton(section_frame, text=self.t("browse").format(lang.capitalize()), 
                                   command=lambda l=lang: self.select_regular(l), font=self.font_base)
        browse_btn.pack(pady=5); setattr(self, f"{lang}_browse_btn", browse_btn)
        lbl = ctk.CTkLabel(section_frame, text=self.t("no_file"), text_color="gray", font=self.font_base); lbl.pack()
        setattr(self, f"{lang}_lbl", lbl)
        frame = ctk.CTkFrame(section_frame, fg_color="transparent"); setattr(self, f"{lang}_frame", frame)
        bold_btn = ctk.CTkButton(frame, text=self.t("bold"), width=120, command=lambda l=lang: self.select_weight(l, "bold"), font=self.font_base)
        bold_btn.grid(row=0, column=0, padx=10, pady=2); setattr(self, f"{lang}_bold_btn", bold_btn)
        setattr(self, f"{lang}_bold_lbl", ctk.CTkLabel(frame, text="None", text_color="gray", font=self.font_small))
        getattr(self, f"{lang}_bold_lbl").grid(row=1, column=0)
        black_btn = ctk.CTkButton(frame, text=self.t("black"), width=120, command=lambda l=lang: self.select_weight(l, "black"), font=self.font_base)
        black_btn.grid(row=0, column=1, padx=10, pady=2); setattr(self, f"{lang}_black_btn", black_btn)
        setattr(self, f"{lang}_black_lbl", ctk.CTkLabel(frame, text="None", text_color="gray", font=self.font_small))
        getattr(self, f"{lang}_black_lbl").grid(row=1, column=1)

    def unload_section(self, lang):
        setattr(self, f"{lang}_reg", None); setattr(self, f"{lang}_bold", None); setattr(self, f"{lang}_black", None)
        getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"), text_color="gray")
        getattr(self, f"{lang}_bold_lbl").configure(text="None"); getattr(self, f"{lang}_black_lbl").configure(text="None")
        getattr(self, f"{lang}_frame").pack_forget()

    def run_backup(self):
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Original_Segoe_Backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            s_path = os.path.join(os.environ['WINDIR'], 'Fonts')
            for f in ["segoeui.ttf", "segoeuib.ttf", "seguibl.ttf"]:
                src = os.path.join(s_path, f)
                if os.path.exists(src): shutil.copy(src, backup_dir)

    def select_regular(self, lang):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            setattr(self, f"{lang}_reg", path)
            getattr(self, f"{lang}_lbl").configure(text=os.path.basename(path), text_color="white")
            getattr(self, f"{lang}_frame").pack(pady=5)
            self.auto_detect(path, lang)

    def auto_detect(self, path, lang):
        dir_p = os.path.dirname(path); prefix = os.path.basename(path).split("-")[0].split(" ")[0].lower()
        for f in os.listdir(dir_p):
            f_l = f.lower()
            if prefix in f_l and "italic" not in f_l:
                full = os.path.join(dir_p, f)
                if "bold" in f_l and "semi" not in f_l:
                    setattr(self, f"{lang}_bold", full)
                    getattr(self, f"{lang}_bold_lbl").configure(text=self.t("auto_tag") + f, text_color="#00FFCC")
                elif "black" in f_l or "heavy" in f_l:
                    setattr(self, f"{lang}_black", full)
                    getattr(self, f"{lang}_black_lbl").configure(text=self.t("auto_tag") + f, text_color="#00FFCC")

    def select_weight(self, lang, weight):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            setattr(self, f"{lang}_{weight}", path)
            getattr(self, f"{lang}_{weight}_lbl").configure(text=os.path.basename(path), text_color="white")

    def restore_system(self):
        if not is_admin(): return
        if not messagebox.askyesno("Confirm", self.t("confirm_restore", is_popup=True)): return
        reg = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        try:
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI (TrueType)', '/t', 'REG_SZ', '/d', 'segoeui.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Bold (TrueType)', '/t', 'REG_SZ', '/d', 'segoeuib.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Black (TrueType)', '/t', 'REG_SZ', '/d', 'seguibl.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Variable (TrueType)', '/t', 'REG_SZ', '/d', 'SegUIVar.ttf', '/f'], check=True)
            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
        except: pass

    def get_fontforge_path(self):
        """Checks common installation paths for FontForge."""
        paths = [
            r"C:\Program Files\FontForgeBuilds\bin\ffpython.exe",
            r"C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe"
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def install_fontforge(self):
        """Attempts to install FontForge using winget."""
        try:
            messagebox.showinfo("Installing", "Downloading and installing FontForge...\n\nThis may take a minute or two. The app will freeze during installation. Please wait.", parent=self)
            
            
            # Run the winget command silently and accept agreements automatically
            subprocess.run(
                ["winget", "install", "-e", "--id", "FontForge.FontForge", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
                check=True, 
                creationflags=CREATE_NO_WINDOW
            )
            
            # Verify if it actually installed
            if self.get_fontforge_path():
                messagebox.showinfo("Success", "FontForge was installed successfully!", parent=self)
                return True
            else:
                messagebox.showerror("Error", "Installation seemed to finish, but the path wasn't found. Please restart the app or install manually.", parent=self)
                return False
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install FontForge via winget.\n\nDetails: {str(e)}", parent=self)
            return False
            
            
    def build_and_apply(self):
        if not self.latin_reg: 
            messagebox.showerror("Error", self.t("sel_err", is_popup=True))
            return
        if not is_admin():
            messagebox.showerror("Error", self.t("admin_err", is_popup=True))
            return
            
        # ---NEW FONTFORGE CHECK ---
        ff_exe = self.get_fontforge_path()
        if not ff_exe:
            if messagebox.askyesno("Dependency Missing", "FontForge is required to build the fonts but is not installed on this system.\n\nWould you like to install it automatically now?", parent=self):
                if not self.install_fontforge():
                    return  
                ff_exe = self.get_fontforge_path() # Update path after install
            else:
                return # Stop the build process if they said no

        self.apply_btn.configure(text="...", state="disabled"); self.update()
        l_r = self.latin_reg; l_b = self.latin_bold or "NONE"; l_bl = self.latin_black or "NONE"
        a_r = self.arabic_reg or "NONE"; a_b = self.arabic_bold or "NONE"; a_bl = self.arabic_black or "NONE"
        
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            subprocess.run([ff_exe, resource_path("engine.py"), l_r, l_b, l_bl, a_r, a_b, a_bl], cwd=curr_dir, check=True)
            
            f_dir = os.path.join(os.environ['WINDIR'], 'Fonts'); reg = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            
            for f in ["segoeui_system_mod.ttf", "segoeuib_system_mod.ttf", "seguibl_system_mod.ttf"]:
                src = os.path.join(curr_dir, f)
                if os.path.exists(src):
                    subprocess.run(['cmd', '/c', 'copy', '/y', src, os.path.join(f_dir, f)], check=True)
            
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI (TrueType)', '/t', 'REG_SZ', '/d', 'segoeui_system_mod.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Bold (TrueType)', '/t', 'REG_SZ', '/d', 'segoeuib_system_mod.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Black (TrueType)', '/t', 'REG_SZ', '/d', 'seguibl_system_mod.ttf', '/f'], check=True)
            subprocess.run(['reg', 'add', reg, '/v', 'Segoe UI Variable (TrueType)', '/t', 'REG_SZ', '/d', 'segoeui_system_mod.ttf', '/f'], check=True)

            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: self.apply_btn.configure(text=self.t("build"), state="normal")

if __name__ == "__main__":
    app = SyrianSegoeApp()
    app.mainloop()
