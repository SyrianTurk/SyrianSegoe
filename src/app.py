import customtkinter as ctk
from tkinter import filedialog, messagebox
import os, shutil, subprocess, ctypes, sys, threading, json, tempfile, re, winreg
from PIL import Image 
import translations 
import segoe_cloner
import variable_slicer
import font_resizer

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

class SystemFontPicker(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Select System Font")
        self.geometry("400x500")
        self.callback = callback
        self.parent = parent
        self.fonts = self.get_system_fonts()
        self.font_names = sorted(list(self.fonts.keys()))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.update_list)
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Search font...", textvariable=self.search_var)
        self.search_entry.pack(fill="x", padx=20, pady=10)
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        self.buttons = []
        self.update_list()
        self.grab_set()

    def get_system_fonts(self):
        fonts = {}
        reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            for i in range(winreg.QueryInfoKey(reg_key)[1]):
                name, value, _ = winreg.EnumValue(reg_key, i)
                if not os.path.isabs(value):
                    value = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', value)
                if os.path.exists(value):
                    clean_name = re.sub(r'\s*\(.*?\)$', '', name)
                    fonts[clean_name] = value
            winreg.CloseKey(reg_key)
        except: pass
        return fonts

    def update_list(self, *args):
        for btn in self.buttons: btn.destroy()
        self.buttons = []
        search_term = self.search_var.get().lower()
        for name in self.font_names:
            if search_term in name.lower():
                btn = ctk.CTkButton(self.scroll, text=name, anchor="w", fg_color="transparent", 
                                   text_color=self.parent._theme_text_color(), hover_color=("gray70", "gray30"),
                                   command=lambda n=name: self.select_font(n))
                btn.pack(fill="x", pady=2)
                self.buttons.append(btn)

    def select_font(self, name):
        self.callback(self.fonts[name], name)
        self.destroy()

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
        self.font_side_btn = ctk.CTkFont(family="Segoe UI Symbol", size=16)
        self.version = "v0.5"
        app_id = f"SyrianSegoe.App.{self.version.lstrip('v')}"

        # --- Data Initialization ---
        self.latin_light = None; self.latin_semilight = None; self.latin_reg = None
        self.latin_semibold = None; self.latin_bold = None; self.latin_black = None
        self.latin_is_var = False

        self.arabic_light = None; self.arabic_semilight = None; self.arabic_reg = None
        self.arabic_semibold = None; self.arabic_bold = None; self.arabic_black = None
        self.arabic_is_var = False

        self.latin_italic_light = None; self.latin_italic_semilight = None; self.latin_italic_reg = None
        self.latin_italic_semibold = None; self.latin_italic_bold = None; self.latin_italic_black = None
        self.latin_italic_is_var = False

        self.arabic_italic_light = None; self.arabic_italic_semilight = None; self.arabic_italic_reg = None
        self.arabic_italic_semibold = None; self.arabic_italic_bold = None; self.arabic_italic_black = None
        self.arabic_italic_is_var = False

        # --- Window Setup ---
        self.follow_system_lang = True
        self.detect_language()
        self.title("SyrianSegoe")
        self.set_initial_geometry()

        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

        self.run_backup()
        self.ensure_fonttools()

        # --- Config Path ---
        self.config_dir = os.path.join(os.path.expanduser("~"), 'Documents', 'SyrianSegoe')
        self.config_path = os.path.join(self.config_dir, 'config.json')

        # --- Settings Variables ---
        self.show_log_var = ctk.BooleanVar(value=False)
        self.save_log_var = ctk.BooleanVar(value=False)
        self.save_font_var = ctk.BooleanVar(value=False)
        self.clone_segoe_var = ctk.BooleanVar(value=False)
        self.enable_italic_var = ctk.BooleanVar(value=False)
        self.merging_mode_var = ctk.StringVar(value="visual")
        self.current_appearance_mode = "System"

        # Listen for live OS theme changes so hardcoded text colors follow
        # (e.g. switching dark/light in Windows Settings while the app is open)
        try:
            from customtkinter.windows.widgets.appearance_mode.appearance_mode_tracker import AppearanceModeTracker
            AppearanceModeTracker.add(lambda _mode: self.refresh_ui_text(), self)
        except Exception:
            pass

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

        # Sidebar Buttons Ordered: Home -> Font Size -> Settings
        self.home_btn.grid(row=0, column=0, sticky="ew", pady=(20, 0))
        
        # Icons used: \uE10F (Home), \uE129 (Font/Aa), \uE115 (Settings)
        self.font_size_nav_btn = ctk.CTkButton(self.sidebar_frame, text=self.t("nav_font_size"), corner_radius=0, height=45, border_spacing=10, 
                                              fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                              anchor="w", command=lambda: self.select_frame("font_size"), font=self.font_side_btn)
        self.font_size_nav_btn.grid(row=1, column=0, sticky="ew")

        self.settings_btn = ctk.CTkButton(self.sidebar_frame, text=self.t("nav_settings"), corner_radius=0, height=45, border_spacing=10, 
                                          fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                          anchor="w", command=lambda: self.select_frame("settings"), font=self.font_side_btn)
        self.settings_btn.grid(row=2, column=0, sticky="ew")

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

        self.selection_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.selection_container.pack(fill="both", expand=True)
        self.selection_container.grid_columnconfigure(0, weight=1)
        self.selection_container.grid_columnconfigure(1, weight=1)

        self.regular_panel = ctk.CTkFrame(self.selection_container, fg_color="transparent")
        self.regular_panel.grid(row=0, column=0, columnspan=2, sticky="n", padx=(0, 8), pady=5)
        self.italic_panel = ctk.CTkFrame(self.selection_container, fg_color="transparent")
        self.italic_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=5)

        self.setup_section("latin", self.t("latin_sec"), self.regular_panel)
        self.setup_section("arabic", self.t("arab_sec"), self.regular_panel)
        self.setup_section("latin_italic", self.t("latin_italic_sec"), self.italic_panel, browse_key="browse_italic", weight_keys=["light", "semilight", "semibold", "bold", "black"])
        self.setup_section("arabic_italic", self.t("arabic_italic_sec"), self.italic_panel, browse_key="browse_italic", weight_keys=["light", "semilight", "semibold", "bold", "black"])
        self.italic_panel.grid_remove()

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

        # --- Advanced Font Size Frame ---
        self.font_size_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.fs_scroll = ctk.CTkScrollableFrame(self.font_size_frame, fg_color="transparent")
        self.fs_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.font_size_title_lbl = ctk.CTkLabel(self.fs_scroll, text=self.t("font_size_title"), font=self.font_title)
        self.font_size_title_lbl.pack(pady=(10, 20), padx=20, anchor="w")

        # 1. Entire Font Size Section
        entire_frame = ctk.CTkFrame(self.fs_scroll, fg_color=("gray85", "gray20"))
        entire_frame.pack(fill="x", padx=20, pady=10)
        self.entire_lbl = ctk.CTkLabel(entire_frame, text=self.t("font_size_entire"), font=self.font_bold)
        self.entire_lbl.pack(pady=10)
        
        self.entire_size_menu = ctk.CTkOptionMenu(entire_frame, values=[f"{i} pt" for i in [6,7,8,9,10,11,12,14,16,18,20,22,24]], font=self.font_base)
        self.entire_size_menu.set("9 pt")
        self.entire_size_menu.pack(pady=5)
        
        self.entire_apply_btn = ctk.CTkButton(entire_frame, text=self.t("apply"), command=self.apply_entire_size_ui)
        self.entire_apply_btn.pack(pady=15)

        ctk.CTkLabel(self.fs_scroll, text="─" * 40, text_color="gray").pack(pady=10)

        # 2. Individual Settings
        self.indiv_title_lbl = ctk.CTkLabel(self.fs_scroll, text=self.t("font_size_individual"), font=self.font_bold)
        self.indiv_title_lbl.pack(pady=10)
        
        self.fs_controls = {}
        self.fs_labels = {}
        metrics_map = [
            ("caption", "font_size_title_bar"), ("icon", "font_size_icons"),
            ("sm_caption", "font_size_palette"), ("status", "font_size_hint"),
            ("message", "font_size_message_box"), ("menu", "font_size_menu")
        ]
        
        for key, trans_key in metrics_map:
            row = ctk.CTkFrame(self.fs_scroll, fg_color="transparent")
            row.pack(fill="x", padx=40, pady=5)
            lbl = ctk.CTkLabel(row, text=self.t(trans_key), font=self.font_base, width=150, anchor="w")
            lbl.pack(side="left")
            self.fs_labels[key] = (lbl, trans_key)
            menu = ctk.CTkOptionMenu(row, values=[f"{i} pt" for i in [6,7,8,9,10,11,12,14,16,18,20,22,24]], width=80)
            menu.set("9 pt")
            menu.pack(side="right")
            self.fs_controls[key] = menu

        self.indiv_apply_btn = ctk.CTkButton(self.fs_scroll, text=self.t("apply"), fg_color="#2c3e50", 
                                            command=self.apply_individual_size_ui)
        self.indiv_apply_btn.pack(pady=30)

        # --- Settings Frame ---
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_title_lbl = ctk.CTkLabel(self.settings_frame, text=self.t("settings_title"), font=self.font_title)
        self.settings_title_lbl.pack(pady=20, padx=20, anchor="w")

        lang_container = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        lang_container.pack(fill="x", padx=20, pady=10)
        self.lang_lbl = ctk.CTkLabel(lang_container, text=self.t("lang_lbl"), font=self.font_bold)
        self.lang_lbl.pack(side="left", padx=10)
        
        self.lang_menu = ctk.CTkOptionMenu(lang_container, values=[self.t("system_lang"), "English", "Türkçe", "العربية", "中文"], 
                                           command=self.change_lang_event, font=self.font_base, dropdown_font=self.font_base)
        self.lang_menu.pack(side="left", padx=10)
        self.lang_menu.set(self._lang_menu_label())

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

        merge_container = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        merge_container.pack(fill="x", padx=20, pady=10)
        self.merging_mode_lbl = ctk.CTkLabel(merge_container, text=self.t("settings_merging_mode"), font=self.font_bold)
        self.merging_mode_lbl.pack(side="left", padx=10)

        self.merging_mode_menu = ctk.CTkOptionMenu(
            merge_container,
            values=[self.t("mode_visual"), self.t("mode_grid")],
            command=self.change_merging_mode_event,
            font=self.font_base, dropdown_font=self.font_base
        )
        self.merging_mode_menu.pack(side="left", padx=10)

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

        self.enable_italic_chk = ctk.CTkCheckBox(self.settings_options_frame, text=self.t("settings_enable_italic"), variable=self.enable_italic_var, font=self.font_base, command=self.toggle_italic_sections)
        self.enable_italic_chk.pack(pady=5, fill="x")

        # --- Log Display (TextBox) ---
        self.log_textbox = ctk.CTkTextbox(self.settings_frame, height=150, font=ctk.CTkFont(family="Consolas", size=11), state="disabled")
        self.log_textbox.pack(fill="x", padx=30, pady=10)
        self.log_textbox.pack_forget() # المخفي افتراضياً، يظهر عند تفعيل الخيار

        # --- Initialization & Loading ---
        self.load_config() # تحميل الإعدادات المحفوظة أولاً
        
        # التعامل مع الحالة المؤقتة (بعد رفع الصلاحيات)
        if len(sys.argv) > 2 and sys.argv[1] == "--state":
            self.load_state(sys.argv[2])

        self.select_frame("home")
        self.toggle_italic_sections()
        self.refresh_ui_text()

    def update_font_size_ui(self):
        """Fetches current system metrics and updates the UI menus."""
        try:
            current = font_resizer.get_current_metrics()
            for key, val in current.items():
                if key in self.fs_controls:
                    self.fs_controls[key].set(f"{val} pt")
            
            # Update Entire Font Size menu if all values match
            vals = list(current.values())
            if vals and all(v == vals[0] for v in vals):
                if f"{vals[0]} pt" in self.entire_size_menu.cget("values"):
                    self.entire_size_menu.set(f"{vals[0]} pt")
        except: pass

    def apply_entire_size_ui(self):
        val = int(self.entire_size_menu.get().split()[0])
        font_resizer.apply_entire_size(val)
        self.update_font_size_ui()

    def apply_individual_size_ui(self):
        metrics = {k: int(m.get().split()[0]) for k, m in self.fs_controls.items()}
        font_resizer.apply_system_metrics(metrics)
        self.update_font_size_ui()

    def get_current_state_dict(self):
        """Returns a dictionary representing the current UI state."""
        return {
            "lang": self.current_lang,
            "follow_system_lang": self.follow_system_lang,
            "theme": self.current_appearance_mode,
            "vars": {
                "show_log": self.show_log_var.get(),
                "save_log": self.save_log_var.get(),
                "save_font": self.save_font_var.get(),
                "clone_segoe": self.clone_segoe_var.get(),
                "enable_italic": self.enable_italic_var.get(),
                "merging_mode": self.merging_mode_var.get()
            },
            "paths": {
                "latin": {w: getattr(self, f"latin_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]},
                "arabic": {w: getattr(self, f"arabic_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]},
                "latin_italic": {w: getattr(self, f"latin_italic_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]},
                "arabic_italic": {w: getattr(self, f"arabic_italic_{w}") for w in ["reg", "light", "semilight", "semibold", "bold", "black"]}
            },
            "is_var": {
                "latin": self.latin_is_var,
                "arabic": self.arabic_is_var,
                "latin_italic": self.latin_italic_is_var,
                "arabic_italic": self.arabic_italic_is_var
            }
        }

    def save_config(self):
        """Saves current settings to the persistent config file."""
        try:
            if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
            state = self.get_current_state_dict()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
        except: pass

    def load_config(self):
        """Loads settings from the persistent config file on startup."""
        if os.path.exists(self.config_path):
            self._apply_state_from_file(self.config_path, cleanup=False)

    def save_state(self):
        """Saves current UI state to a temporary JSON file for admin elevation."""
        state = self.get_current_state_dict()
        fd, path = tempfile.mkstemp(suffix=".json", prefix="ss_state_")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        return path

    def load_state(self, path):
        self._apply_state_from_file(path, cleanup=True)

    def _apply_state_from_file(self, path, cleanup=False):
        """Shared logic for loading state from config or temporary files."""
        if not os.path.exists(path): return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.current_lang = state["lang"]
            self.follow_system_lang = state.get("follow_system_lang", True)
            self.current_appearance_mode = state["theme"]
            ctk.set_appearance_mode(self.current_appearance_mode)
            for key, val in state["vars"].items(): getattr(self, f"{key}_var").set(val)
            for lang in ["latin", "arabic", "latin_italic", "arabic_italic"]:
                setattr(self, f"{lang}_is_var", state["is_var"].get(lang, False))
                for w, p in state["paths"].get(lang, {}).items(): setattr(self, f"{lang}_{w}", p)
            if "merging_mode" in state["vars"]:
                self.merging_mode_var.set(state["vars"]["merging_mode"])
            if cleanup: os.remove(path)
        except: pass

    def update_log_visibility(self):
        self.save_config()
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

    def toggle_italic_sections(self):
        self.save_config()
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if self.enable_italic_var.get():
            self.regular_panel.grid_configure(column=0, columnspan=1, sticky="nsew")
            self.italic_panel.grid()
            self.selection_container.grid_columnconfigure(0, weight=1)
            self.selection_container.grid_columnconfigure(1, weight=1)
            width = min(980, max(820, int(screen_width * 0.65)))
            height = min(820, max(720, int(screen_height * 0.75)))
        else:
            self.italic_panel.grid_remove()
            self.regular_panel.grid_configure(column=0, columnspan=2, sticky="n")
            self.selection_container.grid_columnconfigure(0, weight=1)
            self.selection_container.grid_columnconfigure(1, weight=0)
            width = min(900, max(760, int(screen_width * 0.55)))
            height = min(760, max(700, int(screen_height * 0.72)))
        x = max(0, (screen_width - width) // 2)
        y = 20
        self.geometry(f"{width}x{height}+{x}+{y}")

    def change_merging_mode_event(self, choice):
        if choice == self.t("mode_grid"):
            self.merging_mode_var.set("grid")
        else:
            self.merging_mode_var.set("visual")
        self.save_config()

    def select_frame(self, name):
        is_rtl = self.current_lang == "ar"
        content_col = 0 if is_rtl else 1

        # Update button colors
        self.home_btn.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.font_size_nav_btn.configure(fg_color=("gray75", "gray25") if name == "font_size" else "transparent")
        self.settings_btn.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # Show/Hide frames
        if name == "home":
            self.home_frame.grid(row=0, column=content_col, sticky="nsew")
            self.font_size_frame.grid_forget()
            self.settings_frame.grid_forget()
        elif name == "font_size":
            self.update_font_size_ui()
            self.font_size_frame.grid(row=0, column=content_col, sticky="nsew")
            self.home_frame.grid_forget()
            self.settings_frame.grid_forget()
        else:
            self.settings_frame.grid(row=0, column=content_col, sticky="nsew")
            self.home_frame.grid_forget()
            self.font_size_frame.grid_forget()

    def change_appearance_mode_event(self, choice):
        if choice == self.t("mode_light"): mode = "Light"
        elif choice == self.t("mode_dark"): mode = "Dark"
        else: mode = "System"
        
        self.current_appearance_mode = mode
        ctk.set_appearance_mode(mode)
        self.save_config()
        self.refresh_ui_text()

    def _effective_mode(self):
        """Resolve the actually applied appearance: 'light' or 'dark'.
        When set to 'System', query the OS theme directly because
        ctk.get_appearance_mode() lags until its tracker loop updates."""
        mode = getattr(self, "current_appearance_mode", "System")
        if mode != "System":
            return mode.lower()
        try:
            import darkdetect
            return "dark" if darkdetect.theme() == "Dark" else "light"
        except Exception:
            return ctk.get_appearance_mode().lower()

    def _theme_text_color(self):
        return "black" if self._effective_mode() == "light" else "white"

    def _theme_secondary_text_color(self):
        return "gray20" if self._effective_mode() == "light" else "gray"

    def _theme_auto_tag_color(self):
        return "#0066cc" if self._effective_mode() == "light" else "#00FFCC"

    def ensure_fonttools(self):
        """Silently try to install fonttools if missing"""
        try:
            import fontTools
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "fonttools"], creationflags=0x08000000)

    def t(self, key, is_popup=False):
        return translations.get_text(key, self.current_lang, is_popup=is_popup)

    def set_initial_geometry(self):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(900, max(720, int(screen_width * 0.52)))
        height = min(780, max(700, int(screen_height * 0.72)))
        x = max(0, (screen_width - width) // 2)
        y = 20
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(720, 700)

    def detect_language(self):
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            lang_map = {1055: "tr", 1025: "ar", 1033: "en", 2057: "en", 2052: "zh", 1028: "zh"}
            self.current_lang = lang_map.get(lang_id, "en")
        except: self.current_lang = "en"
        self.follow_system_lang = True

    def _lang_menu_label(self):
        if getattr(self, "follow_system_lang", True):
            return self.t("system_lang")
        return {"en": "English", "tr": "Türkçe", "ar": "العربية", "zh": "中文"}.get(self.current_lang, "English")

    def change_lang_event(self, choice):
        mapping = {"English": "en", "Türkçe": "tr", "العربية": "ar", "中文": "zh"}
        if choice == self.t("system_lang"): self.detect_language()
        else:
            self.current_lang = mapping[choice]
            self.follow_system_lang = False
        self.save_config()
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
        self.font_size_nav_btn.configure(text=self.t("nav_font_size"), anchor=anchor)
        self.settings_btn.configure(text=self.t("nav_settings"), anchor=anchor)
        
        self.font_size_title_lbl.configure(text=self.t("font_size_title"), text_color=theme_text)
        self.entire_lbl.configure(text=self.t("font_size_entire"))
        self.entire_apply_btn.configure(text=self.t("apply"))
        self.indiv_title_lbl.configure(text=self.t("font_size_individual"))
        self.indiv_apply_btn.configure(text=self.t("apply"))

        for key, (lbl, trans_key) in self.fs_labels.items():
            lbl.configure(text=self.t(trans_key), anchor=anchor)
            lbl.pack_forget()
            self.fs_controls[key].pack_forget()
            lbl.pack(side=side)
            self.fs_controls[key].pack(side=opp_side)

        self.update_font_size_ui()

        # تحديث عنوان الإعدادات
        self.settings_title_lbl.configure(text=self.t("settings_title"), anchor=anchor, text_color=theme_text)
        self.settings_title_lbl.pack_configure(anchor=anchor)

        # تحديث رقم الإصدار (دائماً LTR)
        self.version_label.configure(text=self.version, text_color=theme_secondary)
        
        self.lang_lbl.configure(text=self.t("lang_lbl"), text_color=theme_text)
        self.appearance_mode_lbl.configure(text=self.t("appearance_mode"), text_color=theme_text)
        self.merging_mode_lbl.configure(text=self.t("settings_merging_mode"), text_color=theme_text)
        
        self.merging_mode_menu.configure(values=[self.t("mode_visual"), self.t("mode_grid")])
        current_m = self.merging_mode_var.get()
        self.merging_mode_menu.set(self.t("mode_visual" if current_m == "visual" else "mode_grid"))
        
        # Update OptionMenu values and selection
        self.appearance_mode_menu.configure(values=[self.t("mode_system"), self.t("mode_light"), self.t("mode_dark")])
        mode_key_map = {"System": "mode_system", "Light": "mode_light", "Dark": "mode_dark"}
        self.appearance_mode_menu.set(self.t(mode_key_map.get(self.current_appearance_mode, "mode_system")))

        # Language menu follows the current UI language
        self.lang_menu.configure(values=[self.t("system_lang"), "English", "Türkçe", "العربية", "中文"])
        self.lang_menu.set(self._lang_menu_label())

        # تحديث محاذاة صناديق الاختيار (RTL Support)
        self.show_log_chk.configure(text=self.t("settings_show_log"))
        self.show_log_chk.pack_configure(anchor=anchor, fill="none")
        self.save_log_chk.configure(text=self.t("settings_save_log"))
        self.save_log_chk.pack_configure(anchor=anchor, fill="none")
        self.save_font_chk.configure(text=self.t("settings_save_font"))
        self.save_font_chk.pack_configure(anchor=anchor, fill="none")
        self.clone_segoe_chk.configure(text=self.t("settings_clone_segoe"))
        self.clone_segoe_chk.pack_configure(anchor=anchor, fill="none")
        self.enable_italic_chk.configure(text=self.t("settings_enable_italic"))
        self.enable_italic_chk.pack_configure(anchor=anchor, fill="none")

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

        merge_container = self.merging_mode_lbl.master
        merge_container.pack_forget()
        merge_container.pack(fill="x", padx=20, pady=10)
        self.merging_mode_lbl.pack_forget()
        self.merging_mode_menu.pack_forget()
        self.merging_mode_lbl.pack(side=side, padx=10)
        self.merging_mode_menu.pack(side=side, padx=10)

        for lang in ["latin", "arabic", "latin_italic", "arabic_italic"]:
            # تحديث العناوين والأزرار في الأقسام (RTL Support)
            lbl = getattr(self, f"{lang}_sec_lbl")
            btn = getattr(self, f"{lang}_clear_btn")
            section_key = f"{lang}_sec" if lang in ["latin", "arabic"] else f"{lang.split('_')[0]}_italic_sec"
            lbl.configure(text=self.t(section_key))
            btn.configure(text=self.t("clear"))
            lbl.pack_forget()
            btn.pack_forget()
            lbl.pack(side=side)
            btn.pack(side=opp_side)

            getattr(self, f"{lang}_sys_btn").configure(text=self.t("browse_system"))
            getattr(self, f"{lang}_local_btn").configure(text=self.t("browse_file"))
            getattr(self, f"{lang}_sys_btn").pack_forget()
            getattr(self, f"{lang}_local_btn").pack_forget()
            getattr(self, f"{lang}_sys_btn").pack(side=side, padx=5, expand=True)
            getattr(self, f"{lang}_local_btn").pack(side=side, padx=5, expand=True)

            weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
            getattr(self, f"{lang}_weight_toggle").configure(text=self.t("weights_toggle"))
            self.update_weight_menu(lang)
            self.update_weight_labels(lang)

            # Update Labels based on current paths (for state recovery)
            reg_p = getattr(self, f"{lang}_reg")
            if reg_p:
                txt = self.t("variable_tag") + os.path.basename(reg_p) if getattr(self, f"{lang}_is_var") else os.path.basename(reg_p)
                text_color = "#FFA500" if getattr(self, f"{lang}_is_var") else theme_text
                getattr(self, f"{lang}_lbl").configure(text=txt, text_color=text_color)
                getattr(self, f"{lang}_frame").pack(pady=5)
                self.update_weight_labels(lang)
            else:
                getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"), text_color="gray")

    def setup_section(self, lang, title, parent_frame, browse_key="browse", weight_keys=None):
        section_frame = ctk.CTkFrame(parent_frame, fg_color="transparent"); section_frame.pack(pady=5, fill="x", padx=10)
        header_frame = ctk.CTkFrame(section_frame, fg_color="transparent"); header_frame.pack(fill="x")
        title_lbl = ctk.CTkLabel(header_frame, text=title, font=self.font_bold); title_lbl.pack(side="left")
        setattr(self, f"{lang}_sec_lbl", title_lbl)
        
        clear_btn = ctk.CTkButton(header_frame, text=self.t("clear"), width=60, height=20, fg_color="#882222", 
                                  command=lambda l=lang: self.unload_section(l), font=self.font_base)
        clear_btn.pack(side="right"); setattr(self, f"{lang}_clear_btn", clear_btn)
        
        btns_container = ctk.CTkFrame(section_frame, fg_color="transparent"); btns_container.pack(pady=5, fill="x")
        sys_btn = ctk.CTkButton(btns_container, text=self.t("browse_system"), command=lambda l=lang: self.show_system_font_picker(l), font=self.font_base)
        sys_btn.pack(side="left", padx=5, expand=True); setattr(self, f"{lang}_sys_btn", sys_btn)
        local_btn = ctk.CTkButton(btns_container, text=self.t("browse_file"), command=lambda l=lang: self.select_regular_file(l), font=self.font_base)
        local_btn.pack(side="left", padx=5, expand=True); setattr(self, f"{lang}_local_btn", local_btn)
        
        lbl = ctk.CTkLabel(section_frame, text=self.t("no_file"), text_color="gray", font=self.font_base); lbl.pack()
        setattr(self, f"{lang}_lbl", lbl)
        
        frame = ctk.CTkFrame(section_frame, fg_color="transparent"); setattr(self, f"{lang}_frame", frame)
        
        # 5 Extra Weights Layout (Windows-style dropdown, hidden unless toggled on)
        if weight_keys is None:
            weight_keys = ["light", "semilight", "semibold", "bold", "black"]
        setattr(self, f"{lang}_weight_keys", weight_keys)
        
        weight_toggle = ctk.CTkSwitch(frame, text=self.t("weights_toggle"),
                                      command=lambda l=lang: self.toggle_weight_control(l),
                                      font=self.font_small)
        weight_toggle.grid(row=0, column=0, columnspan=3, padx=5, pady=(5, 0))
        setattr(self, f"{lang}_weight_toggle", weight_toggle)
        
        weight_menu = ctk.CTkOptionMenu(frame, width=170,
                                        command=lambda choice, l=lang: self.on_weight_menu(choice, l),
                                        font=self.font_base, dropdown_font=self.font_base)
        weight_menu.grid(row=1, column=0, columnspan=3, padx=5, pady=(5, 0))
        setattr(self, f"{lang}_weight_menu", weight_menu)
        
        weights_container = ctk.CTkFrame(frame, fg_color="transparent")
        setattr(self, f"{lang}_weights_container", weights_container)
        weights_container.grid(row=2, column=0, columnspan=3)
        
        for idx, w_val in enumerate(weight_keys):
            w_lbl = ctk.CTkLabel(weights_container, text="", text_color="gray", font=self.font_small, anchor="w")
            w_lbl.grid(row=idx, column=0, sticky="w", padx=8)
            setattr(self, f"{lang}_{w_val}_lbl", w_lbl)
        
        # Hidden by default; only shown when the user enables independent weight control
        weight_menu.grid_remove()
        weights_container.grid_remove()
        
        self.update_weight_menu(lang)
        self.update_weight_labels(lang)

    def toggle_weight_control(self, lang):
        """Show/hide the weight dropdown and status rows based on the switch."""
        on = getattr(self, f"{lang}_weight_toggle").get()
        menu = getattr(self, f"{lang}_weight_menu")
        container = getattr(self, f"{lang}_weights_container")
        if on:
            menu.grid()
            container.grid()
        else:
            menu.grid_remove()
            container.grid_remove()

    def update_weight_menu(self, lang):
        """Fill the weight dropdown options (rebuilt on language switch)."""
        weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
        menu = getattr(self, f"{lang}_weight_menu")
        menu.configure(values=[self.t(w) for w in weight_keys])
        menu.set(self.t("weights_prompt"))

    def on_weight_menu(self, choice, lang):
        """Dropdown picked a weight -> open file dialog, then reset the prompt."""
        weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
        for w in weight_keys:
            if choice == self.t(w):
                self.select_weight(lang, w)
                break
        self.update_weight_menu(lang)

    def update_weight_labels(self, lang):
        """Refresh per-weight status labels: 'Weight: file / none / auto-sliced'."""
        weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
        for w in weight_keys:
            lbl = getattr(self, f"{lang}_{w}_lbl")
            path = getattr(self, f"{lang}_{w}")
            if getattr(self, f"{lang}_is_var", False):
                txt, color = f"{self.t(w)}: {self.t('auto_sliced')}", self._theme_auto_tag_color()
            elif path:
                shown = self.t("auto_tag") + os.path.basename(path) if "temp_" not in path else os.path.basename(path)
                txt, color = f"{self.t(w)}: {shown}", self._theme_auto_tag_color()
            else:
                txt, color = f"{self.t(w)}: {self.t('none_lbl')}", "gray"
            lbl.configure(text=txt, text_color=color)

    def unload_section(self, lang):
        weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
        for w in ["reg"] + weight_keys:
            setattr(self, f"{lang}_{w}", None)
        setattr(self, f"{lang}_is_var", False)
        getattr(self, f"{lang}_weight_menu").configure(state="normal")
        self.update_weight_labels(lang)
        getattr(self, f"{lang}_lbl").configure(text=self.t("no_file"), text_color="gray")
        getattr(self, f"{lang}_frame").pack_forget()
        self.save_config()

    def run_backup(self):
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Original_Segoe_Backups")
        if not os.path.exists(backup_dir): os.makedirs(backup_dir)
        s_path = os.path.join(os.environ['WINDIR'], 'Fonts')
        for f in ["segoeui.ttf", "segoeuib.ttf", "seguibl.ttf", "segoeuil.ttf", "segoeuisl.ttf", "seguisb.ttf", "SegUIVar.ttf",
                  "segoeuii.ttf", "segoeuiz.ttf", "seguili.ttf", "seguisli.ttf", "seguisbi.ttf", "seguibli.ttf"]:
            src = os.path.join(s_path, f)
            if os.path.exists(src): shutil.copy(src, backup_dir)

    def is_variable_font(self, path):
        try:
            from fontTools.ttLib import TTFont
            font = TTFont(path)
            return 'fvar' in font
        except Exception:
            return False

    def select_regular_file(self, lang):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path: self.apply_selected_font(path, lang)

    def show_system_font_picker(self, lang):
        SystemFontPicker(self, lambda p, n: self.apply_selected_font(p, lang, reg_name=n))

    def apply_selected_font(self, path, lang, reg_name=None):
        if path:
            setattr(self, f"{lang}_reg", path)
            getattr(self, f"{lang}_frame").pack(pady=5)
            
            weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
            if self.is_variable_font(path):
                setattr(self, f"{lang}_is_var", True)
                getattr(self, f"{lang}_lbl").configure(
                    text=self.t("variable_tag") + os.path.basename(path),
                    text_color="#FFA500"
                )
                # Lock weight dropdown and show Auto-Sliced tag
                getattr(self, f"{lang}_weight_menu").configure(state="disabled")
                self.update_weight_labels(lang)
            else:
                setattr(self, f"{lang}_is_var", False)
                getattr(self, f"{lang}_lbl").configure(text=os.path.basename(path), text_color=self._theme_text_color())
                
                # Unlock weight dropdown and auto-detect
                getattr(self, f"{lang}_weight_menu").configure(state="normal")
                self.update_weight_labels(lang)
                self.auto_detect(path, lang, reg_name=reg_name)
            self.save_config()

    def auto_detect(self, path, lang, reg_name=None):
        weight_keys = getattr(self, f"{lang}_weight_keys", ["light", "semilight", "semibold", "bold", "black"])
        
        # 1. الكشف بناءً على سجل النظام (Registry) - مخصص لخطوط النظام
        if reg_name:
            reg_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            try:
                reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                # استخراج اسم العائلة الأساسي (مثلاً Segoe UI من Segoe UI Regular)
                base_family = reg_name.split(" (")[0].split(" Regular")[0].strip().lower()
                
                for i in range(winreg.QueryInfoKey(reg_key)[1]):
                    name, value, _ = winreg.EnumValue(reg_key, i)
                    clean_reg_name = re.sub(r'\s*\(.*?\)$', '', name).lower()
                    
                    if clean_reg_name.startswith(base_family):
                        full_path = value if os.path.isabs(value) else os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', value)
                        if not os.path.exists(full_path): continue
                        
                        # التأكد من مطابقة نوع الخط (عادي أو مائل) للقسم الحالي
                        is_italic_section = "italic" in lang
                        if is_italic_section != ("italic" in clean_reg_name): continue

                        for w in weight_keys:
                            keywords = [w]
                            if w == "black": keywords.append("heavy")
                            
                            if any(k in clean_reg_name for k in keywords):
                                # تجنب الخلط بين الأوزان المتقاربة (مثل Light و Semilight)
                                if w == "light" and "semi" in clean_reg_name: continue
                                if w == "bold" and "semi" in clean_reg_name: continue
                                
                                if not getattr(self, f"{lang}_{w}"): # عدم استبدال اختيار يدوي
                                    setattr(self, f"{lang}_{w}", full_path)
                winreg.CloseKey(reg_key)
            except: pass

        # 2. الكشف بناءً على الملفات (Fallback) - للخطوط المحلية أو في حال فشل سجل النظام
        dir_p = os.path.dirname(path); prefix = os.path.basename(path).split("-")[0].split(" ")[0].lower()
        for f in os.listdir(dir_p):
            f_l = f.lower()
            if prefix in f_l and "italic" not in f_l:
                full = os.path.join(dir_p, f)
                if "light" in f_l and "semi" not in f_l and "light" in weight_keys:
                    setattr(self, f"{lang}_light", full)
                elif "semilight" in f_l or ("semi" in f_l and "light" in f_l):
                    if "semilight" in weight_keys:
                        setattr(self, f"{lang}_semilight", full)
                elif "semibold" in f_l or ("semi" in f_l and "bold" in f_l):
                    if "semibold" in weight_keys:
                        setattr(self, f"{lang}_semibold", full)
                elif "bold" in f_l and "semi" not in f_l and "bold" in weight_keys:
                    setattr(self, f"{lang}_bold", full)
                elif ("black" in f_l or "heavy" in f_l) and "black" in weight_keys:
                    setattr(self, f"{lang}_black", full)
        self.update_weight_labels(lang)

    def select_weight(self, lang, weight):
        path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if path:
            setattr(self, f"{lang}_{weight}", path)
            self.update_weight_labels(lang)
            self.save_config()

    def are_clones_installed(self):
        """Checks if Segoe UI Clone is registered in the Windows Registry or exists in Fonts."""
        reg = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        clone_values = [
            'Segoe UI Clone (TrueType)',
            'Segoe UI Clone Bold (TrueType)',
            'Segoe UI Clone Italic (TrueType)',
            'Segoe UI Clone Bold Italic (TrueType)',
            'Segoe UI Clone Light (TrueType)',
            'Segoe UI Clone Light Italic (TrueType)',
            'Segoe UI Clone Semilight (TrueType)',
            'Segoe UI Clone Semilight Italic (TrueType)',
            'Segoe UI Clone Semibold (TrueType)',
            'Segoe UI Clone Semibold Italic (TrueType)',
            'Segoe UI Clone Black (TrueType)',
            'Segoe UI Clone Black Italic (TrueType)'
        ]
        try:
            for value in clone_values:
                cmd = ['reg', 'query', reg, '/v', value]
                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                if result.returncode == 0:
                    return True
        except:
            pass

        try:
            f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
            for f in os.listdir(f_dir):
                if f.lower().startswith('clone_segoe'):
                    return True
        except:
            pass

        return False

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
                ('Segoe UI Variable (TrueType)', 'SegUIVar.ttf'),
                ('Segoe UI Italic (TrueType)', 'segoeuii.ttf'),
                ('Segoe UI Bold Italic (TrueType)', 'segoeuiz.ttf'),
                ('Segoe UI Light Italic (TrueType)', 'seguili.ttf'),
                ('Segoe UI Semilight Italic (TrueType)', 'seguisli.ttf'),
                ('Segoe UI Semibold Italic (TrueType)', 'seguisbi.ttf'),
                ('Segoe UI Black Italic (TrueType)', 'seguibli.ttf')
            ]
            for name, file in fonts_to_restore:
                subprocess.run(['reg', 'add', reg, '/v', name, '/t', 'REG_SZ', '/d', file, '/f'], check=True)
            
            if delete_clones:
                f_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
                clone_keys = [
                    "Segoe UI Clone", "Segoe UI Clone Bold", "Segoe UI Clone Italic", "Segoe UI Clone Bold Italic",
                    "Segoe UI Clone Light", "Segoe UI Clone Light Italic", "Segoe UI Clone Semilight",
                    "Segoe UI Clone Semilight Italic", "Segoe UI Clone Semibold", "Segoe UI Clone Semibold Italic", "Segoe UI Clone Black", "Segoe UI Clone Black Italic"
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

            italic_enabled = self.enable_italic_var.get() and bool(self.latin_italic_reg)
            italic_output_exists = False
            italic_l_paths = []
            italic_a_paths = []
            if italic_enabled:
                italic_l_paths = variable_slicer.resolve_weights(curr_dir, self.latin_italic_is_var, self.latin_italic_reg,
                    self.latin_italic_light, self.latin_italic_semilight, self.latin_italic_semibold, self.latin_italic_bold,
                    self.latin_italic_black, "lati", weights=[300, 350, 400, 600, 700, 900])
                italic_a_paths = variable_slicer.resolve_weights(curr_dir, self.arabic_italic_is_var, self.arabic_italic_reg,
                    self.arabic_italic_light, self.arabic_italic_semilight, self.arabic_italic_semibold, self.arabic_italic_bold,
                    self.arabic_italic_black, "arai", weights=[300, 350, 400, 600, 700, 900])
                italic_output_exists = any(path != "NONE" for path in italic_l_paths)

            if self.latin_is_var: temp_files_to_clean.extend(l_paths)
            if self.arabic_is_var: temp_files_to_clean.extend(a_paths)
            if self.latin_italic_is_var: temp_files_to_clean.extend(italic_l_paths)
            if self.arabic_italic_is_var: temp_files_to_clean.extend(italic_a_paths)

            self.progress_bar.set(0.3)
            self.status_lbl.configure(text=self.t("prog_building").format("..."))
            var_spoof_path = os.path.join(curr_dir, "SegUIVar_system_mod.ttf")
            variable_slicer.create_variable_spoof(self.latin_reg, var_spoof_path)
            m_mode = self.merging_mode_var.get()

            # 3. Select engine based on merging mode and call with progress tracking
            m_mode = self.merging_mode_var.get()
            engine_file = "engine.py" if m_mode == "visual" else "grid_sync_engine.py"
            
            args = [ff_exe, resource_path(engine_file)] + l_paths + a_paths
            
            # engine.py expects the mode as an extra argument, grid_sync_engine.py doesn't
            if engine_file == "engine.py":
                args.append(m_mode)

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

            if italic_enabled and italic_output_exists:
                self.after(0, lambda: self.progress_bar.set(0.92))
                self.after(0, lambda: self.status_lbl.configure(text=self.t("prog_building").format(self.t("italic_fonts"))))
                ital_engine = "engine_italic.py" if m_mode == "visual" else "grid_sync_engine_italic.py"
                ital_args = [ff_exe, resource_path(ital_engine)] + italic_l_paths + italic_a_paths
                if ital_engine == "engine_italic.py":
                    ital_args.append(m_mode)
                ital_process = subprocess.Popen(ital_args, cwd=curr_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=0x08000000)
                while True:
                    line = ital_process.stdout.readline()
                    if not line:
                        break
                    full_log += line
                    if self.show_log_var.get():
                        print(line, end="")
                ital_process.wait()
                if ital_process.returncode != 0:
                    raise Exception("FontForge Italic Engine failed.")

            self.after(0, lambda: self.progress_bar.set(0.95))
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
            if italic_enabled and italic_output_exists:
                generated_fonts.extend([
                    ("seguili_system_mod.ttf", "Segoe UI Light Italic (TrueType)"),
                    ("seguisli_system_mod.ttf", "Segoe UI Semilight Italic (TrueType)"),
                    ("segoeuii_system_mod.ttf", "Segoe UI Italic (TrueType)"),
                    ("seguisbi_system_mod.ttf", "Segoe UI Semibold Italic (TrueType)"),
                    ("segoeuiz_system_mod.ttf", "Segoe UI Bold Italic (TrueType)"),
                    ("seguibli_system_mod.ttf", "Segoe UI Black Italic (TrueType)")
                ])
            
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
