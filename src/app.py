import customtkinter as ctk
from tkinter import filedialog, messagebox
import os, shutil, subprocess, ctypes, sys, threading, json, tempfile, re
from PIL import Image 
import translations 
import segoe_cloner
import variable_slicer

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
        self.font_side_btn = ctk.CTkFont(family="Segoe UI Symbol", size=14)
        self.version = "v0.4"
        app_id = f"SyrianSegoe.App.{self.version.lstrip('v')}"

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
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

        self.run_backup()
        self.ensure_fonttools()

        # --- Settings Variables ---
        self.show_log_var = ctk.BooleanVar(value=False)
        self.save_log_var = ctk.BooleanVar(value=False)
        self.save_font_var = ctk.BooleanVar(value=False)
        self.clone_segoe_var = ctk.BooleanVar(value=False)
        self.current_appearance_mode = "System"

        # --- Layout Configuration ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1) # Spacer

        self.home_btn = ctk.CTkButton(self.sidebar_frame, text=self.t("nav_home"), corner_radius=0, height=40, border_spacing=10, 
                                      fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                      anchor="w", command=lambda: self.select_frame("home"), font=self.font_side_btn)
        self.home_btn.grid(row=0, column=0, sticky="ew", pady=(20, 0))

        self.settings_btn = ctk.CTkButton(self.sidebar_frame, text=self.t("nav_settings"), corner_radius=0, height=40, border_spacing=10, 
                                          fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                          anchor="w", command=lambda: self.select_frame("settings"), font=self.font_side_btn)
        self.settings_btn.grid(row=1, column=0, sticky="ew")

        # Version Label at Bottom of Sidebar
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text=self.version, font=self.font_small, text_color="gray")
        self.version_label.grid(row=3, column=0, pady=10)

        # --- Home Frame ---
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.home_frame.grid(row=0, column=1, sticky="nsew")

        banner_dark = resource_path("SyrianSegoe_Banner.png")
        banner_light = resource_path("SyrianSegoe_Banner_Light.png")
        
        if os.path.exists(banner_dark):
            dark_img = Image.open(banner_dark)
            # Use Light banner if it exists, otherwise fallback to Dark for both modes
            light_img = Image.open(banner_light) if os.path.exists(banner_light) else dark_img
            self.banner_img = ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=(500, 189))
            self.banner_label = ctk.CTkLabel(self.home_frame, image=self.banner_img, text="")
            self.banner_label.pack(pady=(5, 5))

        self.sub_label = ctk.CTkLabel(self.home_frame, text=self.t("sub_text"), font=self.font_sub)
        self.sub_label.pack(pady=(0, 5))

        self.scroll_frame = ctk.CTkScrollableFrame(self.home_frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.setup_section("latin", self.t("latin_sec"), self.scroll_frame)
        self.setup_section("arabic", self.t("arab_sec"), self.scroll_frame)

        self.progress_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=40, pady=5)
        self.status_lbl = ctk.CTkLabel(self.progress_frame, text=self.t("status_ready"), font=self.font_small)
        self.status_lbl.pack()
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)

        self.apply_btn = ctk.CTkButton(self.home_frame, text=self.t("build"), fg_color="green", hover_color="darkgreen", height=50, 
                                       command=self.build_and_apply, font=self.font_bold)
        self.apply_btn.pack(pady=(10, 10))

        self.revert_btn = ctk.CTkButton(self.home_frame, text=self.t("restore"), fg_color="#444", height=40, 
                                        command=self.restore_system, font=self.font_base)
        self.revert_btn.pack(pady=(0, 15))

        # --- Settings Frame ---
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_title_lbl = ctk.CTkLabel(self.settings_frame, text=self.t("settings_title"), font=self.font_title)
        self.settings_title_lbl.pack(pady=20, padx=20, anchor="w")

        lang_container = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        lang_container.pack(fill="x", padx=20, pady=10)
        self.lang_lbl = ctk.CTkLabel(lang_container, text=self.t("lang_lbl"), font=self.font_bold)
        self.lang_lbl.pack(side="left", padx=10)
        
        self.lang_menu = ctk.CTkOptionMenu(lang_container, values=["System Language", "English", "Türkçe", "العربية"], 
                                           command=self.change_lang_event, font=self.font_base, dropdown_font=self.font_base)
        self.lang_menu.pack(side="left", padx=10)

        appearance_container = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        appearance_container.pack(fill="x", padx=20, pady=10)
        self.appearance_mode_lbl = ctk.CTkLabel(appearance_container, text=self.t("appearance_mode"), font=self.font_bold)
        self.appearance_mode_lbl.pack(side="left", padx=10)
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            appearance_container, 
            values=[self.t("mode_system"), self.t("mode_light"), self.t("mode_dark")],
            command=self.change_appearance_mode_event, 
            font=self.font_base, 
            dropdown_font=self.font_base
        )
        self.appearance_mode_menu.pack(side="left", padx=10)

        self.settings_options_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.settings_options_frame.pack(fill="x", padx=30, pady=10)

        self.show_log_chk = ctk.CTkCheckBox(self.settings_options_frame, text=self.t("settings_show_log"), variable=self.show_log_var, font=self.font_base, command=self.update_log_visibility)
        self.show_log_chk.pack(pady=5, fill="x")

        self.save_log_chk = ctk.CTkCheckBox(self.settings_options_frame, text=self.t("settings_save_log"), variable=self.save_log_var, font=self.font_base)
        self.save_log_chk.pack(pady=5, fill="x")

        self.save_font_chk = ctk.CTkCheckBox(self.settings_options_frame, text=self.t("settings_save_font"), variable=self.save_font_var, font=self.font_base)
        self.save_font_chk.pack(pady=5, fill="x")

        self.clone_segoe_chk = ctk.CTkCheckBox(self.settings_options_frame, text=self.t("settings_clone_segoe"), variable=self.clone_segoe_var, font=self.font_base)
        self.clone_segoe_chk.pack(pady=5, fill="x")

        # --- Log Display (TextBox) ---
        self.log_textbox = ctk.CTkTextbox(self.settings_frame, height=150, font=ctk.CTkFont(family="Consolas", size=11), state="disabled")
        self.log_textbox.pack(fill="x", padx=30, pady=10)
        self.log_textbox.pack_forget() # المخفي افتراضياً، يظهر عند تفعيل الخيار

        # --- Handle State Loading (after admin elevation) ---
        if len(sys.argv) > 2 and sys.argv[1] == "--state":
            self.load_state(sys.argv[2])

        # --- Initialization ---
        self.select_frame("home")
        self.refresh_ui_text()

    def save_state(self):
        """Saves current UI state to a temporary JSON file for admin elevation."""
        state = {
            "lang": self.current_lang,
            "theme": self.current_appearance_mode,
            "vars": {
                "show_log": self.show_log_var.get(),
                "save_log": self.save_log_var.get(),
                "save_font": self.save_font_var.get(),
                "clone_segoe": self.clone_segoe_var.get()
            },
            "paths": {
                "latin": {w: getattr(self, f"latin_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]},
                "arabic": {w: getattr(self, f"arabic_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]}
            },
            "is_var": {"latin": self.latin_is_var, "arabic": self.arabic_is_var}
        }
        fd, path = tempfile.mkstemp(suffix=".json", prefix="ss_state_")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        return path

    def load_state(self, path):
        """Loads UI state from the temporary JSON file."""
        if not os.path.exists(path): return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.current_lang = state["lang"]
            self.current_appearance_mode = state["theme"]
            ctk.set_appearance_mode(self.current_appearance_mode)
            for key, val in state["vars"].items(): getattr(self, f"{key}_var").set(val)
            for lang in ["latin", "arabic"]:
                setattr(self, f"{lang}_is_var", state["is_var"][lang])
                for w, p in state["paths"][lang].items(): setattr(self, f"{lang}_{w}", p)
            os.remove(path) # Cleanup
        except: pass

    def update_log_visibility(self):
        # تشغيل في خيط منفصل لمنع تجمد الواجهة
        threading.Thread(target=self._toggle_console, daemon=True).start()

    def _toggle_console(self):
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if self.show_log_var.get():
            # افتح التيرمينال فقط إذا لم يكن مفتوحاً بالفعل لمنع التجمد
            if hwnd == 0:
                ctypes.windll.kernel32.AllocConsole()
                sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                ctypes.windll.kernel32.SetConsoleTitleW(f"SyrianSegoe.Console.{self.version.lstrip('v')}")
                print("[SyrianSegoe] Debugging Terminal Started...")
        else:
            # أغلق التيرمينال إذا كان مفتوحاً
            if hwnd != 0:
                # إرسال أمر إغلاق للنافذة (WM_CLOSE = 0x10)
                ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
                ctypes.windll.kernel32.FreeConsole()
                # إعادة توجيه المخرجات لملف فارغ لمنع حدوث أخطاء برمجية بعد الإغلاق
                sys.stdout = open(os.devnull, 'w')
                sys.stderr = open(os.devnull, 'w')

    def select_frame(self, name):
        is_rtl = self.current_lang == "ar"
        content_col = 0 if is_rtl else 1

        # Update button colors
        self.home_btn.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.settings_btn.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # Show/Hide frames
        if name == "home":
            self.home_frame.grid(row=0, column=content_col, sticky="nsew")
            self.settings_frame.grid_forget()
        else:
            self.settings_frame.grid(row=0, column=content_col, sticky="nsew")
            self.home_frame.grid_forget()

    def change_appearance_mode_event(self, choice):
        if choice == self.t("mode_light"): mode = "Light"
        elif choice == self.t("mode_dark"): mode = "Dark"
        else: mode = "System"
        
        self.current_appearance_mode = mode
        ctk.set_appearance_mode(mode)
        self.refresh_ui_text()

    def _theme_text_color(self):
        return "black" if ctk.get_appearance_mode().lower() == "light" else "white"

    def _theme_secondary_text_color(self):
        return "gray20" if ctk.get_appearance_mode().lower() == "light" else "gray"

    def _theme_auto_tag_color(self):
        return "#0066cc" if ctk.get_appearance_mode().lower() == "light" else "#00FFCC"

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
        is_rtl = self.current_lang == "ar"
        anchor = "e" if is_rtl else "w"
        side = "right" if is_rtl else "left"
        opp_side = "left" if is_rtl else "right"

        # 1. تحديث توزيع الأعمدة ومكان الشريط الجانبي
        if is_rtl:
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            self.sidebar_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # تحديث مكان الإطار الحالي المعروض
        if self.home_frame.winfo_manager(): # إذا كان معروضاً حالياً
            self.home_frame.grid_configure(column=0 if is_rtl else 1)
        if self.settings_frame.winfo_manager():
            self.settings_frame.grid_configure(column=0 if is_rtl else 1)

        theme_text = self._theme_text_color()
        theme_secondary = self._theme_secondary_text_color()

        self.sub_label.configure(text=self.t("sub_text"), text_color=theme_text)
        self.apply_btn.configure(text=self.t("build"))
        self.revert_btn.configure(text=self.t("restore"))
        self.status_lbl.configure(text=self.t("status_ready"), text_color=theme_text)

        # Sidebar & Settings
        self.home_btn.configure(text=self.t("nav_home"), anchor=anchor)
        self.settings_btn.configure(text=self.t("nav_settings"), anchor=anchor)
        
        # تحديث عنوان الإعدادات
        self.settings_title_lbl.configure(text=self.t("settings_title"), anchor=anchor, text_color=theme_text)
        self.settings_title_lbl.pack_configure(anchor=anchor)

        # تحديث رقم الإصدار (دائماً LTR)
        self.version_label.configure(text=self.version, text_color=theme_secondary)
        
        self.lang_lbl.configure(text=self.t("lang_lbl"), text_color=theme_text)
        self.appearance_mode_lbl.configure(text=self.t("appearance_mode"), text_color=theme_text)
        
        # Update OptionMenu values and selection
        self.appearance_mode_menu.configure(values=[self.t("mode_system"), self.t("mode_light"), self.t("mode_dark")])
        mode_key_map = {"System": "mode_system", "Light": "mode_light", "Dark": "mode_dark"}
        self.appearance_mode_menu.set(self.t(mode_key_map.get(self.current_appearance_mode, "mode_system")))

        # تحديث محاذاة صناديق الاختيار (RTL Support)
        self.show_log_chk.configure(text=self.t("settings_show_log"))
        self.show_log_chk.pack_configure(anchor=anchor, fill="none")
        self.save_log_chk.configure(text=self.t("settings_save_log"))
        self.save_log_chk.pack_configure(anchor=anchor, fill="none")
        self.save_font_chk.configure(text=self.t("settings_save_font"))
        self.save_font_chk.pack_configure(anchor=anchor, fill="none")
        self.clone_segoe_chk.configure(text=self.t("settings_clone_segoe"))
        self.clone_segoe_chk.pack_configure(anchor=anchor, fill="none")

        # إعادة توزيع عناصر قائمة اللغة في الإعدادات
        self.lang_lbl.pack_forget()
        self.lang_menu.pack_forget()
        self.lang_lbl.pack(side=side, padx=10)
        self.lang_menu.pack(side=side, padx=10)

        # إعادة توزيع عناصر وضع المظهر
        appearance_container = self.appearance_mode_lbl.master
        appearance_container.pack_forget()
        appearance_container.pack(fill="x", padx=20, pady=10)
        self.appearance_mode_lbl.pack_forget()
        self.appearance_mode_menu.pack_forget()
        self.appearance_mode_lbl.pack(side=side, padx=10)
        self.appearance_mode_menu.pack(side=side, padx=10)

        for lang in ["latin", "arabic"]:
            # تحديث العناوين والأزرار في الأقسام (RTL Support)
            lbl = getattr(self, f"{lang}_sec_lbl")
            btn = getattr(self, f"{lang}_clear_btn")
            lbl.configure(text=self.t(f"{lang}_sec"))
            btn.configure(text=self.t("clear"))
            lbl.pack_forget()
            btn.pack_forget()
            lbl.pack(side=side)
            btn.pack(side=opp_side)

            getattr(self, f"{lang}_browse_btn").configure(text=self.t("browse").format(lang.capitalize()))
            for weight_key in ["light", "semilight", "semibold", "bold", "black"]:
                getattr(self, f"{lang}_{weight_key}_btn").configure(text=self.t(weight_key))

            # Update Labels based on current paths (for state recovery)
            reg_p = getattr(self, f"{lang}_reg")
            if reg_p:
                txt = self.t("variable_tag") + os.path.basename(reg_p) if getattr(self, f"{lang}_is_var") else os.path.basename(reg_p)
                text_color = "#FFA500" if getattr(self, f"{lang}_is_var") else theme_text
                getattr(self, f"{lang}_lbl").configure(text=txt, text_color=text_color)
                getattr(self, f"{lang}_frame").pack(pady=5)
                for w in ["light", "semilight", "semibold", "bold", "black"]:
                    w_lbl = getattr(self, f"{lang}_{w}_lbl")
                    w_path = getattr(self, f"{lang}_{w}")
                    if getattr(self, f"{lang}_is_var"):
                        w_lbl.configure(text=self.t("auto_sliced"), text_color=self._theme_auto_tag_color())
                    elif w_path:
                        w_lbl.configure(text=self.t("auto_tag") + os.path.basename(w_path) if "temp_" not in w_path else os.path.basename(w_path), text_color=self._theme_auto_tag_color())
                    else:
                        w_lbl.configure(text=self.t("none_lbl"), text_color="gray")
            else:
                getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"), text_color="gray")

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
            ("light", self.t("light"), 0, 0), 
            ("semilight", self.t("semilight"), 0, 1), 
            ("semibold", self.t("semibold"), 0, 2),
            ("bold", self.t("bold"), 2, 0), 
            ("black", self.t("black"), 2, 1)
        ]
        
        for w_val, w_txt, r, c in weights:
            btn = ctk.CTkButton(frame, text=w_txt, width=100, command=lambda l=lang, w=w_val: self.select_weight(l, w), font=self.font_base)
            btn.grid(row=r, column=c, padx=5, pady=2); setattr(self, f"{lang}_{w_val}_btn", btn)
            w_lbl = ctk.CTkLabel(frame, text=self.t("none_lbl"), text_color="gray", font=self.font_small)
            w_lbl.grid(row=r+1, column=c); setattr(self, f"{lang}_{w_val}_lbl", w_lbl)

    def unload_section(self, lang):
        for w in ["light", "semilight", "reg", "semibold", "bold", "black"]:
            setattr(self, f"{lang}_{w}", None)
            if w != "reg":
                getattr(self, f"{lang}_{w}_lbl").configure(text=self.t("none_lbl"), text_color="gray")
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
                getattr(self, f"{lang}_lbl").configure(
                    text=self.t("variable_tag") + os.path.basename(path),
                    text_color="#FFA500"
                )
                # Lock buttons and show Auto-Sliced tag
                for w in ["light", "semilight", "semibold", "bold", "black"]:
                    getattr(self, f"{lang}_{w}_btn").configure(state="disabled")
                    getattr(self, f"{lang}_{w}_lbl").configure(text=self.t("auto_sliced"), text_color=self._theme_auto_tag_color())
            else:
                setattr(self, f"{lang}_is_var", False)
                getattr(self, f"{lang}_lbl").configure(text=os.path.basename(path), text_color=self._theme_text_color())
                
                # Unlock buttons and auto-detect
                for w in ["light", "semilight", "semibold", "bold", "black"]:
                    getattr(self, f"{lang}_{w}_btn").configure(state="normal")
                    getattr(self, f"{lang}_{w}_lbl").configure(text=self.t("none_lbl"), text_color="gray")
                self.auto_detect(path, lang)

    def auto_detect(self, path, lang):
        dir_p = os.path.dirname(path); prefix = os.path.basename(path).split("-")[0].split(" ")[0].lower()
        for f in os.listdir(dir_p):
            f_l = f.lower()
            if prefix in f_l and "italic" not in f_l:
                full = os.path.join(dir_p, f)
                if "light" in f_l and "semi" not in f_l:
                    setattr(self, f"{lang}_light", full)
                    getattr(self, f"{lang}_light_lbl").configure(text=self.t("auto_tag") + f, text_color=self._theme_auto_tag_color())
                elif "semilight" in f_l or ("semi" in f_l and "light" in f_l):
                    setattr(self, f"{lang}_semilight", full)
                    getattr(self, f"{lang}_semilight_lbl").configure(text=self.t("auto_tag") + f, text_color=self._theme_auto_tag_color())
                elif "semibold" in f_l or ("semi" in f_l and "bold" in f_l):
                    setattr(self, f"{lang}_semibold", full)
                    getattr(self, f"{lang}_semibold_lbl").configure(text=self.t("auto_tag") + f, text_color=self._theme_auto_tag_color())
                elif "bold" in f_l and "semi" not in f_l:
                    setattr(self, f"{lang}_bold", full)
                    getattr(self, f"{lang}_bold_lbl").configure(text=self.t("auto_tag") + f, text_color=self._theme_auto_tag_color())
                elif "black" in f_l or "heavy" in f_l:
                    setattr(self, f"{lang}_black", full)
                    getattr(self, f"{lang}_black_lbl").configure(text=self.t("auto_tag") + f, text_color=self._theme_auto_tag_color())

    def select_weight(self, lang, weight):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            setattr(self, f"{lang}_{weight}", path)
            getattr(self, f"{lang}_{weight}_lbl").configure(text=os.path.basename(path), text_color=self._theme_text_color())

    def are_clones_installed(self):
        """Checks if Segoe UI Clone is registered in the Windows Registry."""
        reg = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        try:
            cmd = ['reg', 'query', reg, '/v', 'Segoe UI Clone (TrueType)']
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
            return result.returncode == 0
        except: return False

    def restore_system(self):
        if not is_admin():
            if messagebox.askyesno("Admin", self.t("admin_confirm", is_popup=True)):
                state_f = self.save_state()
                params = f'"{sys.argv[0]}" --state "{state_f}"' if not getattr(sys, 'frozen', False) else f'--state "{state_f}"'
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                if int(ret) > 32: # تم قبول طلب الصلاحيات بنجاح
                    self.destroy()
            return

        if not messagebox.askyesno("Confirm", self.t("confirm_restore", is_popup=True)): return

        # التحقق من وجود الخط المستنسخ قبل السؤال
        delete_clones = False
        if self.are_clones_installed():
            delete_clones = messagebox.askyesno("Confirm", self.t("confirm_delete_clones", is_popup=True))

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
            
            if delete_clones:
                f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
                clone_keys = [
                    "Segoe UI Clone", "Segoe UI Clone Bold", "Segoe UI Clone Italic", "Segoe UI Clone Bold Italic",
                    "Segoe UI Clone Light", "Segoe UI Clone Light Italic", "Segoe UI Clone Semilight",
                    "Segoe UI Clone Semilight Italic", "Segoe UI Clone Semibold", "Segoe UI Clone Semibold Italic", "Segoe UI Clone Black"
                ]
                for k in clone_keys:
                    subprocess.run(['reg', 'delete', reg, '/v', f"{k} (TrueType)", '/f'], capture_output=True, creationflags=0x08000000)
                
                for f in os.listdir(f_dir):
                    if f.startswith("clone_segoe"):
                        try: os.remove(os.path.join(f_dir, f))
                        except: pass

            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
        except Exception as e: messagebox.showerror("Error", str(e))

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
    def check_system_state(self):
        """Checks if modded fonts are active in registry or need cleanup"""
        reg_path = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        try:
            # Check if Segoe UI is pointing to a modded file
            cmd = ['reg', 'query', reg_path, '/v', 'Segoe UI (TrueType)']
            result = subprocess.run(cmd, capture_output=True, text=True)
            is_modded = "_system_mod.ttf" in result.stdout
            
            f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
            mod_exists = any("_system_mod.ttf" in f for f in os.listdir(f_dir))

            if is_modded:
                messagebox.showerror("Error", self.t("err_restore_first", is_popup=True))
                return False
            
            if mod_exists:
                # Registry is original, but files exist. Safe to delete and proceed.
                self.status_lbl.configure(text=self.t("prog_cleaning"))
                for f in os.listdir(f_dir):
                    if "_system_mod.ttf" in f:
                        try: os.remove(os.path.join(f_dir, f))
                        except: pass
            return True
        except: return True

    def build_and_apply(self):
        if not self.latin_reg: 
            messagebox.showerror("Error", self.t("sel_err", is_popup=True))
            return
        if not is_admin():
            if messagebox.askyesno("Admin", self.t("admin_confirm", is_popup=True)):
                state_f = self.save_state()
                params = f'"{sys.argv[0]}" --state "{state_f}"' if not getattr(sys, 'frozen', False) else f'--state "{state_f}"'
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
                if int(ret) > 32: # تم قبول طلب الصلاحيات بنجاح
                    self.destroy()
            return

        ff_exe = self.get_fontforge_path()
        if not ff_exe:
            if messagebox.askyesno("Dependency Missing", "FontForge is required. Install automatically?", parent=self):
                if not self.install_fontforge(): return  
                ff_exe = self.get_fontforge_path() 
            else: return 

        if not self.check_system_state(): return

        self.apply_btn.configure(state="disabled")
        self.revert_btn.configure(state="disabled")
        threading.Thread(target=self._threaded_build, args=(ff_exe,), daemon=True).start()

    def _threaded_build(self, ff_exe):
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        temp_files_to_clean = []
        full_log = ""
        
        try:
            self.progress_bar.set(0.1)
            # 1. Resolve Latin & Arabic 6 Weights
            self.status_lbl.configure(text=self.t("prog_slicing"))
            l_paths = variable_slicer.resolve_weights(curr_dir, self.latin_is_var, self.latin_reg, self.latin_light, self.latin_semilight, self.latin_semibold, self.latin_bold, self.latin_black, "lat")
            a_paths = variable_slicer.resolve_weights(curr_dir, self.arabic_is_var, self.arabic_reg, self.arabic_light, self.arabic_semilight, self.arabic_semibold, self.arabic_bold, self.arabic_black, "ara")
            arabic_enabled = any(path != "NONE" for path in a_paths)
            
            if self.latin_is_var: temp_files_to_clean.extend(l_paths)
            if self.arabic_is_var: temp_files_to_clean.extend(a_paths)

            self.progress_bar.set(0.3)
            self.status_lbl.configure(text=self.t("prog_building").format("..."))
            var_spoof_path = os.path.join(curr_dir, "SegUIVar_system_mod.ttf")
            variable_slicer.create_variable_spoof(self.latin_reg, var_spoof_path)

            # 3. Call FontForge Engine with progress tracking
            # If show_log is enabled, the output will automatically go to the allocated console via sys.stdout/print
            # but we still pipe it to capture full_log for saving to file.
            args = [ff_exe, resource_path("engine.py")] + l_paths + a_paths
            process = subprocess.Popen(args, cwd=curr_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=0x08000000)

            weight_progress_positions = {
                "Light": 0.35,
                "Semilight": 0.45,
                "Regular": 0.55,
                "Semibold": 0.65,
                "Bold": 0.75,
                "Black": 0.85,
            }
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break

                full_log += line
                if self.show_log_var.get():
                    print(line, end="")

                # Update UI based on engine output
                processing_match = re.search(r"Processing\s+(.+?)\s+weight", line, re.IGNORECASE)
                if processing_match:
                    weight = processing_match.group(1).strip()
                    if not weight:
                        weight = "..."
                    self.after(0, lambda w=weight: self.status_lbl.configure(text=self.t("prog_building").format(w)))
                    if weight in weight_progress_positions:
                        self.after(0, lambda v=weight_progress_positions[weight]: self.progress_bar.set(v))
                    else:
                        self.after(0, lambda: self.progress_bar.set(min(self.progress_bar.get() + 0.08, 0.89)))
                elif "Assembling" in line:
                    if arabic_enabled:
                        self.after(0, lambda: self.status_lbl.configure(text=self.t("prog_merging")))
                    else:
                        self.after(0, lambda: self.status_lbl.configure(text=self.t("prog_assembling")))
                    self.after(0, lambda: self.progress_bar.set(0.88))
                elif "All system replacement fonts built successfully" in line:
                    self.after(0, lambda: self.progress_bar.set(0.92))
                
            process.wait()
            if process.returncode != 0: raise Exception("FontForge Engine failed.")

            self.after(0, lambda: self.progress_bar.set(0.9))
            self.after(0, lambda: self.status_lbl.configure(text=self.t("prog_applying")))
            
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

            # 5. Handle Extra Settings (Save Log & Save Font)
            app_docs_path = os.path.join(os.path.expanduser("~"), 'Documents', 'SyrianSegoe')
            if not os.path.exists(app_docs_path): os.makedirs(app_docs_path)
            
            if self.save_log_var.get():
                log_file = os.path.join(app_docs_path, "SyrianSegoe_Build_Log.txt")
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(full_log)

            if self.save_font_var.get():
                export_dir = os.path.join(app_docs_path, "Outputs")
                if not os.path.exists(export_dir): os.makedirs(export_dir)
                for file_name, _ in generated_fonts:
                    src = os.path.join(curr_dir, file_name)
                    if os.path.exists(src): shutil.copy(src, export_dir)

            # 5. Optional: Clone Original Segoe UI
            if self.clone_segoe_var.get():
                backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Original_Segoe_Backups")
                segoe_cloner.clone_original_segoe(backup_dir)

            self.after(0, lambda: self.progress_bar.set(1.0))
            messagebox.showinfo("Success", self.t("reboot_msg", is_popup=True))
            
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: 
            self.after(0, lambda: self.apply_btn.configure(state="normal"))
            self.after(0, lambda: self.revert_btn.configure(state="normal"))
            self.after(0, lambda: self.status_lbl.configure(text=self.t("status_ready")))
            for f in temp_files_to_clean:
                if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    app = SyrianSegoeApp()
    app.mainloop()
