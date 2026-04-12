import customtkinter as ctk
from tkinter import filedialog, messagebox
import os, shutil, subprocess, ctypes, sys
from PIL import Image 
import translations 

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
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
        self.latin_light = None; self.latin_semilight = None; self.latin_reg = None
        self.latin_semibold = None; self.latin_bold = None; self.latin_black = None
        
        self.arabic_light = None; self.arabic_semilight = None; self.arabic_reg = None
        self.arabic_semibold = None; self.arabic_bold = None; self.arabic_black = None
        
        self.latin_is_var = False
        self.arabic_is_var = False

        # --- Window Setup ---
        self.detect_language()
        self.title("SyrianSegoe")
        self.geometry("700x700") 

        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SyrianSegoe.App.1.1")

        if not is_admin():
            messagebox.showwarning("Admin", self.t("admin_warn", is_popup=True))

        self.run_backup()
        self.ensure_fonttools()

        # --- 1. Top Bar & Language ---
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(10, 0))
        
        self.lang_menu = ctk.CTkOptionMenu(top_bar, values=["System Language", "English", "Türkçe", "العربية"], 
                                           command=self.change_lang_event, font=self.font_base, dropdown_font=self.font_base)
        self.lang_menu.pack(side="right")

        # --- 2. THE BANNER ---
        banner_file = resource_path("SyrianSegoe_Banner.png")
        if os.path.exists(banner_file):
            raw_img = Image.open(banner_file)
            self.banner_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(500, 189))
            self.banner_label = ctk.CTkLabel(self, image=self.banner_img, text="")
            self.banner_label.pack(pady=(5, 5))
        else:
            self.title_label = ctk.CTkLabel(self, text=self.t("title"), font=self.font_title)
            self.title_label.pack(pady=(10, 5))

        self.sub_label = ctk.CTkLabel(self, text=self.t("sub_text"), font=self.font_sub)
        self.sub_label.pack(pady=(0, 5))
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # --- 3. Font Selection Sections ---
        self.setup_section("latin", self.t("latin_sec"), self.scroll_frame)
        self.setup_section("arabic", self.t("arab_sec"), self.scroll_frame)

        # --- 4. Action Buttons ---
        self.apply_btn = ctk.CTkButton(self, text=self.t("build"), fg_color="green", hover_color="darkgreen", height=50, 
                                       command=self.build_and_apply, font=self.font_bold)
        self.apply_btn.pack(pady=(10, 10))

        self.revert_btn = ctk.CTkButton(self, text=self.t("restore"), fg_color="#444", height=40, 
                                        command=self.restore_system, font=self.font_base)
        self.revert_btn.pack(pady=(0, 15))

        self.refresh_ui_text()

    def ensure_fonttools(self):
        """Silently try to install fonttools if missing"""
        try:
            import fontTools
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "fonttools"], creationflags=0x08000000)

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
            if hasattr(self, f"{lang}_bold_btn"):
                getattr(self, f"{lang}_bold_btn").configure(text=self.t("bold"))
                getattr(self, f"{lang}_black_btn").configure(text=self.t("black"))
            if getattr(self, f"{lang}_reg") is None:
                getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"))

    def setup_section(self, lang, title, parent_frame):
        section_frame = ctk.CTkFrame(parent_frame, fg_color="transparent"); section_frame.pack(pady=5, fill="x", padx=10)
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
        
        # 5 Extra Weights Layout
        weights = [
            ("light", "Light", 0, 0), 
            ("semilight", "SemiLight", 0, 1), 
            ("semibold", "SemiBold", 0, 2),
            ("bold", self.t("bold"), 2, 0), 
            ("black", self.t("black"), 2, 1)
        ]
        
        for w_val, w_txt, r, c in weights:
            btn = ctk.CTkButton(frame, text=w_txt, width=100, command=lambda l=lang, w=w_val: self.select_weight(l, w), font=self.font_base)
            btn.grid(row=r, column=c, padx=5, pady=2); setattr(self, f"{lang}_{w_val}_btn", btn)
            w_lbl = ctk.CTkLabel(frame, text="None", text_color="gray", font=self.font_small)
            w_lbl.grid(row=r+1, column=c); setattr(self, f"{lang}_{w_val}_lbl", w_lbl)

    def unload_section(self, lang):
        for w in ["light", "semilight", "reg", "semibold", "bold", "black"]:
            setattr(self, f"{lang}_{w}", None)
            if w != "reg":
                getattr(self, f"{lang}_{w}_lbl").configure(text="None", text_color="gray")
                getattr(self, f"{lang}_{w}_btn").configure(state="normal")
                
        setattr(self, f"{lang}_is_var", False)
        getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"), text_color="gray")
        getattr(self, f"{lang}_frame").pack_forget()

    def run_backup(self):
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Original_Segoe_Backups")
        if not os.path.exists(backup_dir): os.makedirs(backup_dir)
        s_path = os.path.join(os.environ['WINDIR'], 'Fonts')
        for f in ["segoeui.ttf", "segoeuib.ttf", "seguibl.ttf", "segoeuil.ttf", "segoeuisl.ttf", "seguisb.ttf", "SegUIVar.ttf"]:
            src = os.path.join(s_path, f)
            if os.path.exists(src): shutil.copy(src, backup_dir)

    def is_variable_font(self, path):
        try:
            from fontTools.ttLib import TTFont
            font = TTFont(path)
            return 'fvar' in font
        except Exception:
            return False

    def select_regular(self, lang):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            setattr(self, f"{lang}_reg", path)
            getattr(self, f"{lang}_frame").pack(pady=5)
            
            if self.is_variable_font(path):
                setattr(self, f"{lang}_is_var", True)
                getattr(self, f"{lang}_lbl").configure(text=f"⭐ [VARIABLE] {os.path.basename(path)}", text_color="#FFA500")
                
                # Lock buttons and show Auto-Sliced tag
                for w in ["light", "semilight", "semibold", "bold", "black"]:
                    getattr(self, f"{lang}_{w}_btn").configure(state="disabled")
                    getattr(self, f"{lang}_{w}_lbl").configure(text="Auto-Sliced", text_color="#FFA500")
            else:
                setattr(self, f"{lang}_is_var", False)
                getattr(self, f"{lang}_lbl").configure(text=os.path.basename(path), text_color="white")
                
                # Unlock buttons and auto-detect
                for w in ["light", "semilight", "semibold", "bold", "black"]:
                    getattr(self, f"{lang}_{w}_btn").configure(state="normal")
                    getattr(self, f"{lang}_{w}_lbl").configure(text="None", text_color="gray")
                self.auto_detect(path, lang)

    def auto_detect(self, path, lang):
        dir_p = os.path.dirname(path); prefix = os.path.basename(path).split("-")[0].split(" ")[0].lower()
        for f in os.listdir(dir_p):
            f_l = f.lower()
            if prefix in f_l and "italic" not in f_l:
                full = os.path.join(dir_p, f)
                if "light" in f_l and "semi" not in f_l:
                    setattr(self, f"{lang}_light", full)
                    getattr(self, f"{lang}_light_lbl").configure(text=self.t("auto_tag") + f, text_color="#00FFCC")
                elif "semilight" in f_l or ("semi" in f_l and "light" in f_l):
                    setattr(self, f"{lang}_semilight", full)
                    getattr(self, f"{lang}_semilight_lbl").configure(text=self.t("auto_tag") + f, text_color="#00FFCC")
                elif "semibold" in f_l or ("semi" in f_l and "bold" in f_l):
                    setattr(self, f"{lang}_semibold", full)
                    getattr(self, f"{lang}_semibold_lbl").configure(text=self.t("auto_tag") + f, text_color="#00FFCC")
                elif "bold" in f_l and "semi" not in f_l:
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
            fonts_to_restore = [
                ('Segoe UI (TrueType)', 'segoeui.ttf'),
                ('Segoe UI Bold (TrueType)', 'segoeuib.ttf'),
                ('Segoe UI Black (TrueType)', 'seguibl.ttf'),
                ('Segoe UI Light (TrueType)', 'segoeuil.ttf'),
                ('Segoe UI Semilight (TrueType)', 'segoeuisl.ttf'),
                ('Segoe UI Semibold (TrueType)', 'seguisb.ttf'),
                ('Segoe UI Variable (TrueType)', 'SegUIVar.ttf')
            ]
            for name, file in fonts_to_restore:
                subprocess.run(['reg', 'add', reg, '/v', name, '/t', 'REG_SZ', '/d', file, '/f'], check=True)
            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
        except: pass

    def get_fontforge_path(self):
        paths = [
            r"C:\Program Files\FontForgeBuilds\bin\ffpython.exe",
            r"C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe"
        ]
        for path in paths:
            if os.path.exists(path): return path
        return None

    def install_fontforge(self):
        try:
            messagebox.showinfo("Installing", "Downloading and installing FontForge...\n\nThis may take a minute or two. The app will freeze during installation. Please wait.", parent=self)
            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(
                ["winget", "install", "-e", "--id", "FontForge.FontForge", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
                check=True, creationflags=CREATE_NO_WINDOW
            )
            if self.get_fontforge_path():
                messagebox.showinfo("Success", "FontForge was installed successfully!", parent=self)
                return True
            else:
                messagebox.showerror("Error", "Installation seemed to finish, but the path wasn't found.", parent=self)
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install FontForge via winget.\n\nDetails: {str(e)}", parent=self)
            return False
            
    # --- FontTools Processors ---
    def slice_variable_font(self, var_path, weight_val, out_path):
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        font = TTFont(var_path)
        static_font = instantiateVariableFont(font, {"wght": weight_val})
        static_font.save(out_path)

    def create_variable_spoof(self, input_path, output_path):
        from fontTools.ttLib import TTFont
        font = TTFont(input_path)
        target_family = "Segoe UI Variable"
        target_ps_name = "SegoeUI-Variable"
        
        for record in font['name'].names:
            if record.nameID in [1, 4, 16, 21]: 
                if record.platformID == 3: record.string = target_family.encode('utf-16-be')
                else: record.string = target_family.encode('utf-8')
            elif record.nameID == 6: 
                if record.platformID == 3: record.string = target_ps_name.encode('utf-16-be')
                else: record.string = target_ps_name.encode('utf-8')
                
        font.save(output_path)

    def resolve_weights(self, base_path, is_var, reg_path, light_path, semilight_path, semibold_path, bold_path, black_path, lang_prefix):
        paths = []
        if is_var:
            weights = [300, 350, 400, 600, 700, 900] # Light, Semilight, Reg, Semibold, Bold, Black
            for w in weights:
                out = os.path.join(base_path, f"temp_{lang_prefix}_{w}.ttf")
                self.slice_variable_font(reg_path, w, out)
                paths.append(out)
        else:
            r = reg_path if reg_path else "NONE"
            lt = light_path if light_path else r
            sl = semilight_path if semilight_path else r
            b = bold_path if bold_path else r
            sb = semibold_path if semibold_path else b
            blk = black_path if black_path else b
            
            paths = [lt, sl, r, sb, b, blk]
        return paths

    def build_and_apply(self):
        if not self.latin_reg: 
            messagebox.showerror("Error", self.t("sel_err", is_popup=True))
            return
        if not is_admin():
            messagebox.showerror("Error", self.t("admin_err", is_popup=True))
            return
            
        ff_exe = self.get_fontforge_path()
        if not ff_exe:
            if messagebox.askyesno("Dependency Missing", "FontForge is required. Install automatically?", parent=self):
                if not self.install_fontforge(): return  
                ff_exe = self.get_fontforge_path() 
            else: return 

        self.apply_btn.configure(text="Processing...", state="disabled"); self.update()
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        temp_files_to_clean = []
        
        try:
            # 1. Resolve Latin & Arabic 6 Weights
            l_paths = self.resolve_weights(curr_dir, self.latin_is_var, self.latin_reg, self.latin_light, self.latin_semilight, self.latin_semibold, self.latin_bold, self.latin_black, "lat")
            a_paths = self.resolve_weights(curr_dir, self.arabic_is_var, self.arabic_reg, self.arabic_light, self.arabic_semilight, self.arabic_semibold, self.arabic_bold, self.arabic_black, "ara")
            
            if self.latin_is_var: temp_files_to_clean.extend(l_paths)
            if self.arabic_is_var: temp_files_to_clean.extend(a_paths)

            # 2. Generate SegUIVar Spoof (Variable Override)
            var_spoof_path = os.path.join(curr_dir, "SegUIVar_system_mod.ttf")
            self.create_variable_spoof(self.latin_reg, var_spoof_path)

            # 3. Call FontForge Engine
            args = [ff_exe, resource_path("engine.py")] + l_paths + a_paths
            subprocess.run(args, cwd=curr_dir, check=True)
            
            # 4. Copy to Windows Fonts
            f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
            reg = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            
            generated_fonts = [
                ("segoeuil_system_mod.ttf", "Segoe UI Light (TrueType)"),
                ("segoeuisl_system_mod.ttf", "Segoe UI Semilight (TrueType)"),
                ("segoeui_system_mod.ttf", "Segoe UI (TrueType)"),
                ("seguisb_system_mod.ttf", "Segoe UI Semibold (TrueType)"),
                ("segoeuib_system_mod.ttf", "Segoe UI Bold (TrueType)"),
                ("seguibl_system_mod.ttf", "Segoe UI Black (TrueType)"),
                ("SegUIVar_system_mod.ttf", "Segoe UI Variable (TrueType)")
            ]
            
            for file_name, reg_key in generated_fonts:
                src = os.path.join(curr_dir, file_name)
                if os.path.exists(src):
                    subprocess.run(['cmd', '/c', 'copy', '/y', src, os.path.join(f_dir, file_name)], check=True)
                    subprocess.run(['reg', 'add', reg, '/v', reg_key, '/t', 'REG_SZ', '/d', file_name, '/f'], check=True)

            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
            
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: 
            self.apply_btn.configure(text=self.t("build"), state="normal")
            for f in temp_files_to_clean:
                if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    app = SyrianSegoeApp()
    app.mainloop()
