import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import requests
import socket
import psutil
import speedtest
import dns.resolver
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import io
import time
import threading
import uuid
import webbrowser
import os
import platform
import subprocess
import ipaddress
import queue
import re
import concurrent.futures
from collections import deque
from datetime import datetime
import csv
import json
import sys


def glass_surface(width, height, panel=False):
    """Antialiased glass rim, reflected light and an inset soft shadow."""
    width, height = max(24, width), max(24, height)
    scale = 2
    w, h = width*scale, height*scale
    image = Image.new('RGBA', (w, h), '#091540')
    shadow = Image.new('RGBA', (w, h))
    ImageDraw.Draw(shadow).rounded_rectangle((10, 18, w-10, h-4), radius=32,
                                             fill=(0, 3, 20, 210))
    image = Image.alpha_composite(image, shadow.filter(ImageFilter.GaussianBlur(9)))
    surface = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(surface)
    for y in range(h):
        # The reflection fades before the content, avoiding a rectangular inset.
        light = max(0, 1-y/112)**2 if panel else max(0, 1-y/h)
        color = (int(16+24*light), int(36+29*light), int(90+43*light), 255)
        draw.line((0, y, w, y), fill=color)
    mask = Image.new('L', (w, h))
    ImageDraw.Draw(mask).rounded_rectangle((8, 6, w-9, h-15), radius=30, fill=255)
    surface.putalpha(mask)
    image = Image.alpha_composite(image, surface)
    edge = ImageDraw.Draw(image)
    edge.rounded_rectangle((8, 6, w-9, h-15), radius=30, outline=(92, 121, 190, 255), width=2)
    edge.arc((8, 6, 68, 66), 180, 270, fill='#ABD2FA', width=2)
    edge.line((38, 6, w-39, 6), fill='#7692FF', width=2)
    edge.arc((w-69, 6, w-9, 66), 270, 350, fill='#ABD2FA', width=2)
    return image.resize((width, height), Image.Resampling.LANCZOS)


class GlassNavigation(tk.Canvas):
    """Keyboard-accessible rounded navigation with a reflected active edge."""
    def __init__(self, parent, text, command, style=None):
        super().__init__(parent, height=37, bg='#091540', bd=0,
                         highlightthickness=0, takefocus=True, cursor='hand2')
        self.command, self.label, self.selected = command, text, False
        self.bind('<Configure>', self.redraw)
        self.bind('<Button-1>', lambda _: command())
        self.bind('<Return>', lambda _: command())
        self.bind('<space>', lambda _: command())
        self.bind('<FocusIn>', self.redraw)
        self.bind('<FocusOut>', self.redraw)

    def configure(self, cnf=None, **kwargs):
        style = kwargs.pop('style', None)
        if style:
            self.selected = style == 'NavActive.TButton'
            self.redraw()
        if cnf or kwargs:
            super().configure(cnf, **kwargs)

    def redraw(self, event=None):
        self.delete('all')
        if self.selected or self.focus_get() == self:
            self.surface = ImageTk.PhotoImage(glass_surface(self.winfo_width(), 37))
            self.create_image(0, 0, image=self.surface, anchor=tk.NW)
            self.create_line(self.winfo_width()-8, 12, self.winfo_width()-8, 29,
                             fill='#ABD2FA', width=3)
        self.create_text(17, 18, text=self.label, anchor=tk.W,
                         fill='#F5F8FF' if self.selected else '#B8C9EB',
                         font=('Segoe UI', 10, 'bold' if self.selected else 'normal'))


class CanvasValue:
    """Small label adapter for text drawn inside a glass metric card."""
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.item = item

    def config(self, **options):
        if 'text' in options:
            self.canvas.itemconfigure(self.item, text=options['text'])
        if 'font' in options:
            self.canvas.itemconfigure(self.item, font=options['font'])

    def cget(self, key):
        return self.canvas.itemcget(self.item, key)


class GlassStatCard(tk.Canvas):
    """Gradient metric card with rounded corners and a soft highlight."""
    def __init__(self, parent, title, glyph, caption, accent, base, **kwargs):
        super().__init__(parent, width=1, height=132, bg=base, highlightthickness=0,
                         bd=0, **kwargs)
        self.accent = accent
        self.base = base
        self.background_item = self.create_image(0, 0, anchor=tk.NW)
        self.image = None
        self.icon_box = self.create_rectangle(18, 17, 53, 52, fill='#1B2CC1',
                                               outline='#7692FF', width=1)
        self.glyph_item = self.create_text(35, 35, text=glyph, fill='#ABD2FA',
                                           font=('Segoe UI', 11, 'bold'))
        self.create_text(65, 27, text=title, anchor=tk.W, fill='#F5F8FF',
                         font=('Segoe UI', 10))
        value = self.create_text(24, 80, text='—', anchor=tk.W, fill='#FFFFFF',
                                 font=('Segoe UI', 19, 'bold'))
        self.value = CanvasValue(self, value)
        caption_item = self.create_text(24, 112, text=caption, anchor=tk.W, fill='#B8C9EB',
                         font=('Segoe UI', 9))
        self.caption = CanvasValue(self, caption_item)
        self.bind('<Configure>', self._resize)

    def _resize(self, event):
        self.image = ImageTk.PhotoImage(glass_surface(event.width, event.height))
        self.itemconfigure(self.background_item, image=self.image)
        self.tag_lower(self.background_item)

    def set_flag(self, photo):
        self.itemconfigure(self.glyph_item, state='hidden')
        if hasattr(self, 'flag_item'):
            self.delete(self.flag_item)
        self.flag_item = self.create_image(35, 35, image=photo)

    def set_country_code(self, code):
        if hasattr(self, 'flag_item'):
            self.delete(self.flag_item)
            del self.flag_item
        self.itemconfigure(self.glyph_item, state='normal', text=code)


class GlassPanel(tk.Canvas):
    """Rounded gradient panel with a content frame for controls and charts."""
    def __init__(self, parent, title, subtitle, height=150):
        super().__init__(parent, width=1, height=height, bg='#091540', highlightthickness=0, bd=0)
        self.background_item = self.create_image(0, 0, anchor=tk.NW)
        self.image = None
        self.create_text(24, 25, text=title, anchor=tk.W, fill='#F5F8FF',
                         font=('Segoe UI', 12, 'bold'))
        self.create_text(24, 48, text=subtitle, anchor=tk.W, fill='#B8C9EB',
                         font=('Segoe UI', 9))
        self.body = tk.Frame(self, bg='#10245A')
        self.body_item = self.create_window(24, 65, window=self.body, anchor=tk.NW)
        self.bind('<Configure>', self._resize)

    def _resize(self, event):
        width, height = max(20, event.width), max(20, event.height)
        self.image = ImageTk.PhotoImage(glass_surface(width, height, panel=True))
        self.itemconfigure(self.background_item, image=self.image)
        self.tag_lower(self.background_item)
        self.itemconfigure(self.body_item, width=max(1, width-48), height=max(1, height-88))

class NetworkMasterPro:
    def __init__(self, root):
        self.root = root
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NetworkMaster.Desktop.App')
        self.ui_queue = queue.Queue()
        self.closed = False
        self.ui_after_id = self.root.after(50, self._drain_ui_queue)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.title("Network Master")
        width = min(1360, self.root.winfo_screenwidth() - 60)
        height = min(850, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{width}x{height}")
        self.center_window()
        self.setup_theme()
        self.setup_soft_controls()
        self.create_app_icon()

        # API Configuration
        self.api_services = [
            "https://api64.ipify.org?format=json",
            "https://ipinfo.io/json",
            "https://ipapi.co/json/",
            "https://api.myip.com"
        ]
        #https://github.com/SaeedForouzandeh/Network-Master
        # Initialize results storage
        self.results = {
            "ip_info": {},
            "network_info": {},
            "dns_info": {},
            "speed_test": {},
            "devices": [],
            "location": {}
        }
        self.history = []
        self.traffic_samples = deque(maxlen=60)
        self.last_counters = None
        self.last_sample_time = None
        self.monitoring = False
        self.monitor_busy = False
        self.monitor_generation = 0
        self.monitor_after_ids = []
        self.known_devices = None

        # Build UI
        self.create_status_bar()
        self.create_main_container()
        self.create_sidebar()
        self.create_main_content()
        self.traffic_after_id = self.root.after(2000, self.sample_traffic)

        # Start initial scans
        self.run_initial_scans()

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_theme(self):
        """Configure custom dark theme with hex colors"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Blue palette from the supplied dashboard reference.
        self.colors = {
            'primary': '#10245A',
            'primary_dark': '#091540',
            'secondary': '#1B2CC1',
            'accent': '#7692FF',
            'accent_dark': '#142665',
            'light': '#F5F8FF',
            'dark': '#091540',
            'success': '#ABD2FA',
            'warning': '#ABD2FA',
            'danger': '#FF8DAA',
            'info': '#ABD2FA',
            'muted': '#B8C9EB',
            'border': '#7692FF',
            'canvas': '#0D2052'
        }

        # Main style configurations
        self.style.configure('.',
            background=self.colors['primary_dark'],
            foreground=self.colors['light'],
            font=('Segoe UI', 10))

        # Frame styles
        self.style.configure('TFrame',
            background=self.colors['primary_dark'])

        # Label styles
        self.style.configure('TLabel',
            background=self.colors['primary_dark'],
            foreground=self.colors['light'])

        # Button styles with smooth hover effects
        self.style.configure('TButton',
            background=self.colors['secondary'],
            foreground=self.colors['light'],
            borderwidth=0,
            relief='flat',
            padding=8,
            font=('Segoe UI', 10))

        self.style.map('TButton',
            background=[('active', self.colors['accent']),
                       ('pressed', self.colors['accent'])],
            foreground=[('active', 'white'),
                       ('pressed', 'white')])

        # Notebook (Tab) styles
        self.style.configure('TNotebook',
            background=self.colors['primary_dark'])
        self.style.configure('Main.TNotebook', background=self.colors['primary_dark'],
                             borderwidth=0, bordercolor=self.colors['primary_dark'],
                             lightcolor=self.colors['primary_dark'],
                             darkcolor=self.colors['primary_dark'])
        self.style.layout('Main.TNotebook.Tab', [])

        self.style.configure('TNotebook.Tab',
            background=self.colors['primary'],
            foreground=self.colors['light'],
            padding=[12, 6],
            font=('Segoe UI', 10))

        self.style.map('TNotebook.Tab',
            background=[('selected', self.colors['accent']),
                       ('active', self.colors['secondary'])],
            foreground=[('selected', self.colors['dark']),
                       ('active', self.colors['light'])])

        # Treeview styles
        self.style.configure('Treeview',
            background=self.colors['primary'],
            fieldbackground=self.colors['primary'],
            foreground=self.colors['light'],
            rowheight=30,
            borderwidth=0)

        self.style.configure('Treeview.Heading',
            background=self.colors['accent_dark'],
            foreground=self.colors['light'],
            font=('Segoe UI', 10, 'bold'),
            borderwidth=0)

        self.style.map('Treeview',
            background=[('selected', self.colors['secondary'])])

        # Custom widget styles
        self.style.configure('Title.TLabel',
            font=('Segoe UI', 14, 'bold'),
            foreground=self.colors['light'])

        self.style.configure('Subtitle.TLabel',
            font=('Segoe UI', 12),
            foreground=self.colors['light'])

        self.style.configure('Data.TLabel',
            font=('Consolas', 10),
            foreground=self.colors['light'])

        self.style.configure('Big.TButton',
            font=('Segoe UI', 12, 'bold'),
            padding=12,
            background=self.colors['accent'], foreground=self.colors['dark'])

        self.style.configure('Accent.TButton',
            background=self.colors['accent'],
            foreground=self.colors['dark'])
        self.style.configure('Card.TFrame', background=self.colors['primary'])
        self.style.configure('Card.TLabel', background=self.colors['primary'], foreground=self.colors['light'])
        self.style.configure('CardValue.TLabel', background=self.colors['primary'],
                             foreground=self.colors['accent'], font=('Segoe UI', 18, 'bold'))
        self.style.configure('Sidebar.TFrame', background=self.colors['primary_dark'])
        self.style.configure('Sidebar.TLabel', background=self.colors['primary_dark'],
                             foreground=self.colors['light'])
        self.style.configure('SidebarTitle.TLabel', background=self.colors['primary_dark'],
                             foreground=self.colors['light'], font=('Segoe UI', 10, 'bold'))
        self.style.configure('Nav.TButton', background=self.colors['primary_dark'],
                             foreground=self.colors['muted'], anchor=tk.W,
                             padding=(12, 9), font=('Segoe UI', 10))
        self.style.map('Nav.TButton', background=[('active', self.colors['primary'])],
                       foreground=[('active', self.colors['light'])])
        self.style.configure('NavActive.TButton', background=self.colors['secondary'],
                             foreground=self.colors['light'], anchor=tk.W,
                             padding=(12, 9), font=('Segoe UI', 10, 'bold'))
        self.style.map('NavActive.TButton', background=[('active', self.colors['secondary'])],
                       foreground=[('active', self.colors['light'])])
        self.style.configure('TEntry', fieldbackground=self.colors['primary'],
                             foreground=self.colors['light'], insertcolor=self.colors['light'])
        self.style.configure('TCombobox', fieldbackground=self.colors['primary'],
                             foreground=self.colors['light'])
        self.style.map('TCombobox', fieldbackground=[('readonly', self.colors['secondary'])],
                       foreground=[('readonly', self.colors['light'])])
        self.style.configure('TCheckbutton', background=self.colors['primary_dark'],
                             foreground=self.colors['light'])

        # Scrollbar styles
        self.style.configure('Vertical.TScrollbar',
            background=self.colors['primary'],
            troughcolor=self.colors['primary_dark'],
            arrowcolor=self.colors['light'],
            bordercolor=self.colors['primary_dark'],
            relief='flat')

        # Configure root window
        self.root.configure(bg=self.colors['primary_dark'])

    def setup_soft_controls(self):
        """Use antialiased, rounded ttk surfaces while retaining native keyboard behavior."""
        self.control_images = []
        def surface(color, edge='#7692FF'):
            im = Image.new('RGBA', (144, 144))
            ImageDraw.Draw(im).rounded_rectangle((3, 3, 140, 140), radius=43,
                                                 fill=color, outline=edge, width=3)
            photo = ImageTk.PhotoImage(im.resize((36, 36), Image.Resampling.LANCZOS))
            self.control_images.append(photo)
            return photo
        hover = surface('#263E82')
        for style, prefix, fill, over, text in [
                ('TButton', 'Outline', '#10245A', '#263E82', '#ABD2FA'),
                ('Accent.TButton', 'Primary', '#1B2CC1', '#3049DB', '#FFFFFF'),
                ('Big.TButton', 'Large', '#1B2CC1', '#3049DB', '#FFFFFF')]:
            normal = surface(fill)
            active = surface(over, '#ABD2FA')
            pressed = surface('#142665', '#ABD2FA')
            disabled = surface('#172447', '#344B87')
            focus = surface(fill, '#ABD2FA')
            element = prefix + '.SoftButton'
            self.style.element_create(element, 'image', normal,
                                      ('disabled', disabled), ('pressed', pressed),
                                      ('active', active), ('focus', focus), border=13, sticky='nswe')
            self.style.layout(style, [(element, {'sticky': 'nswe', 'children': [
                ('Button.padding', {'sticky': 'nswe', 'children': [
                    ('Button.label', {'sticky': 'nswe'})]})]})])
            self.style.configure(style, padding=(18, 8), background='#091540', font=('Segoe UI', 10, 'bold'),
                                 foreground=text, anchor=tk.CENTER)
            self.style.map(style, background=[('active', '#091540'), ('pressed', '#091540'), ('disabled', '#091540')], foreground=[('disabled', '#7D8BAC'), ('active', '#FFFFFF'),
                                              ('pressed', '#FFFFFF')])
        self.style.element_create('Soft.Field', 'image', surface('#10245A'),
                                  ('focus', hover), border=13, sticky='nswe')
        self.style.layout('TCombobox', [('Soft.Field', {'sticky': 'nswe', 'children': [
            ('Combobox.downarrow', {'side': 'right', 'sticky': 'ns'}),
            ('Combobox.padding', {'sticky': 'nswe', 'children': [
                ('Combobox.textarea', {'sticky': 'nswe'})]})]})])
        self.style.configure('TCombobox', background='#10245A', padding=(10, 5), arrowsize=17,
                             arrowcolor='#ABD2FA', borderwidth=0)
        self.style.map('TCombobox', fieldbackground=[('readonly', '#10245A')],
                       selectbackground=[('readonly', '#10245A')],
                       selectforeground=[('readonly', '#F5F8FF')])
        self.root.option_add('*TCombobox*Listbox.background', '#10245A')
        self.root.option_add('*TCombobox*Listbox.foreground', '#F5F8FF')
        self.root.option_add('*TCombobox*Listbox.selectBackground', '#1B2CC1')
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#F5F8FF')
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 11))
        self.root.option_add('*TCombobox*Listbox.relief', 'flat')

    def create_app_icon(self):
        """Use the bundled NM icon for the window and Windows taskbar."""
        base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'assets', 'nm.ico')
        if os.path.isfile(path):
            source = Image.open(path).convert('RGBA')
            self.app_icon = ImageTk.PhotoImage(source.resize((64, 64)))
            self.sidebar_icon = ImageTk.PhotoImage(source.resize((42, 42)))
            self.root.iconphoto(True, self.app_icon)
            if platform.system() == 'Windows':
                self.root.iconbitmap(default=path)
                self.root.after(100, lambda: self.apply_windows_identity(path))
        else:
            self.app_icon = tk.PhotoImage(width=1, height=1)
            self.sidebar_icon = self.app_icon

    def apply_windows_identity(self, path):
        """Set icons on Tk's native wrapper as well as its client window."""
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR,
                                     wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]
        user32.SendMessageW.restype = ctypes.c_ssize_t
        client = self.root.winfo_id()
        wrapper = user32.GetParent(client) or client
        self.native_icon_handles = []
        for kind, size in ((0, 16), (1, 48)):
            icon = user32.LoadImageW(None, path, 1, size, size, 0x10)
            if icon:
                self.native_icon_handles.append(icon)
                for window in {client, wrapper}:
                    user32.SendMessageW(window, 0x80, kind, icon)  # WM_SETICON
        # Match the system title bar to the dashboard on Windows 10/11.
        try:
            dwm = ctypes.WinDLL('dwmapi')
            for attribute, value in ((20, 1), (35, 0x401509), (36, 0xFAD2AB)):
                setting = ctypes.c_int(value)
                dwm.DwmSetWindowAttribute(wintypes.HWND(wrapper), attribute,
                                          ctypes.byref(setting), ctypes.sizeof(setting))
        except OSError:
            pass

    def create_main_container(self):
        """Create main container frame"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

    def create_sidebar(self):
        """Create modern sidebar with navigation"""
        sidebar = ttk.Frame(self.main_frame, width=230, style='Sidebar.TFrame', padding=12)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        # App logo and title
        logo_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        logo_frame.pack(fill=tk.X, pady=(12, 25), padx=4)
        ttk.Label(logo_frame, image=self.sidebar_icon, style='Sidebar.TLabel').pack(side=tk.LEFT)
        brand_text = ttk.Frame(logo_frame, style='Sidebar.TFrame')
        brand_text.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(brand_text, text="NETWORK MASTER",
                  style='SidebarTitle.TLabel').pack(anchor=tk.W)
        ttk.Label(brand_text, text="Network diagnostics", style='Sidebar.TLabel').pack(anchor=tk.W)

        # Navigation buttons
        nav_buttons = [
            ("▣  Dashboard", "dashboard"),
            ("◉  IP information", "ip_info"),
            ("⌁  Network tools", "network"),
            ("◈  DNS utilities", "dns"),
            ("↗  Speed test", "speed"),
            ("▤  Connected devices", "devices"),
            ("⌖  Geolocation", "geo"),
            ("◇  Security checks", "security"),
            ("◷  Monitor & history", "monitor")
        ]
        self.nav_buttons = {}
        for text, key in nav_buttons:
            btn = GlassNavigation(sidebar,
                          text=text,
                          command=lambda page=key: self.select_page(page),
                          style='Nav.TButton')
            btn.pack(fill=tk.X, pady=2)
            self.nav_buttons[key] = btn

        # Separator
        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, pady=8)

        # Quick IP info panel
        self.quick_ip_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        self.quick_ip_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.quick_ip_frame,
                text="Your Public IP:",
                style='Sidebar.TLabel').pack(anchor=tk.W)

        self.quick_ip_label = ttk.Label(self.quick_ip_frame,
                                      text="Checking...",
                                      style='Sidebar.TLabel')
        self.quick_ip_label.pack(anchor=tk.W)
        #https://github.com/SaeedForouzandeh/Network-Master
        # Full scan button
        scan_btn = ttk.Button(sidebar,
                            text="🔄 Full Network Scan",
                            command=self.run_full_scan,
                            style='Accent.TButton')
        scan_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        self.full_scan_btn = scan_btn

        # Exit button
        exit_btn = ttk.Button(sidebar,
                            text="🚪 Exit Application",
                            command=self.on_close,
                            style='TButton')
        exit_btn.pack(side=tk.BOTTOM, fill=tk.X)

    def create_main_content(self):
        """Create main content area with tabs"""
        self.notebook = ttk.Notebook(self.main_frame, style='Main.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create all tabs
        self.tabs = {
            "dashboard": ttk.Frame(self.notebook),
            "ip_info": ttk.Frame(self.notebook),
            "network": ttk.Frame(self.notebook),
            "dns": ttk.Frame(self.notebook),
            "speed": ttk.Frame(self.notebook),
            "devices": ttk.Frame(self.notebook),
            "geo": ttk.Frame(self.notebook),
            "security": ttk.Frame(self.notebook),
            "monitor": ttk.Frame(self.notebook)
        }

        # Add tabs to notebook
        self.notebook.add(self.tabs["dashboard"], text="📊 Dashboard")
        self.notebook.add(self.tabs["ip_info"], text="🔍 IP Info")
        self.notebook.add(self.tabs["network"], text="📶 Network Tools")
        self.notebook.add(self.tabs["dns"], text="🌐 DNS Utilities")
        self.notebook.add(self.tabs["speed"], text="🚀 Speed Test")
        self.notebook.add(self.tabs["devices"], text="📱 Devices")
        self.notebook.add(self.tabs["geo"], text="📍 Geolocation")
        self.notebook.add(self.tabs["security"], text="🛡️ Security")
        self.notebook.add(self.tabs["monitor"], text="◉ Monitor")

        # Initialize tab contents
        self.init_dashboard_tab()
        self.init_ip_info_tab()
        self.init_network_tools_tab()
        self.init_dns_tools_tab()
        self.init_speed_test_tab()
        self.init_devices_tab()
        self.init_geolocation_tab()
        self.init_security_tab()
        self.init_monitor_tab()
        self.select_page('dashboard')

    def create_status_bar(self):
        """Create status bar at bottom"""
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root,
                                  textvariable=self.status_var,
                                  relief=tk.FLAT,
                                  style='TLabel',
                                  background=self.colors['accent_dark'],
                                  foreground='white',
                                  padding=8,
                                  font=('Segoe UI', 9))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.update_status("Ready")

    def update_status(self, message):
        """Update status bar with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.ui(lambda: self.status_var.set(f"{timestamp} | {message}"))

    def ui(self, callback):
        """Schedule widget work on Tk's main thread."""
        if self.closed:
            return
        if threading.current_thread() is threading.main_thread():
            callback()
        else:
            self.ui_queue.put(callback)

    def _drain_ui_queue(self):
        if self.closed:
            return
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                try:
                    callback()
                except tk.TclError:
                    pass  # A window may have closed before queued work ran.
        except queue.Empty:
            pass
        try:
            self.ui_after_id = self.root.after(50, self._drain_ui_queue)
        except tk.TclError:
            pass

    def on_close(self):
        self.closed = True
        self.monitoring = False
        after_ids = [getattr(self, 'ui_after_id', None),
                     getattr(self, 'traffic_after_id', None)]
        after_ids.extend(self.monitor_after_ids)
        for after_id in after_ids:
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
        self.root.destroy()

    # Tab navigation methods
    def select_page(self, key):
        self.notebook.select(self.tabs[key])
        for name, button in self.nav_buttons.items():
            button.configure(style='NavActive.TButton' if name == key else 'Nav.TButton')
        if key == 'dashboard' and hasattr(self, 'traffic_samples'):
            self.update_network_graph()

    def search_tools(self, _event=None):
        query = self.search_entry.get().strip().lower()
        matches = {
            'ip': 'ip_info', 'dns': 'dns', 'speed': 'speed',
            'device': 'devices', 'scan': 'devices', 'network': 'network',
            'geo': 'geo', 'security': 'security', 'monitor': 'monitor',
            'history': 'monitor', 'dashboard': 'dashboard',
        }
        for word, page in matches.items():
            if word in query:
                self.select_page(page)
                return
        self.update_status('No matching tool found')

    def show_dashboard(self):
        """Show dashboard tab"""
        self.select_page("dashboard")

    def show_ip_info(self):
        """Show IP information tab"""
        self.select_page("ip_info")

    def show_network_tools(self):
        """Show network tools tab"""
        self.select_page("network")

    def show_dns_tools(self):
        """Show DNS tools tab"""
        self.select_page("dns")

    def show_speed_test(self):
        """Show speed test tab"""
        self.select_page("speed")

    def show_devices(self):
        """Show devices tab"""
        self.select_page("devices")

    def show_geolocation(self):
        """Show geolocation tab"""
        self.select_page("geo")

    def show_security(self):
        """Show security tab"""
        self.select_page("security")

    def show_monitor(self):
        self.select_page("monitor")

    # Tab initialization methods
    def init_dashboard_tab(self):
        """Build a card-based dashboard inspired by the supplied reference."""
        c = self.colors
        page = tk.Frame(self.tabs['dashboard'], bg=c['primary_dark'])
        page.pack(fill=tk.BOTH, expand=True, padx=18, pady=(18, 12))

        header = tk.Frame(page, bg=c['primary_dark'])
        header.pack(fill=tk.X, pady=(0, 17))
        heading = tk.Frame(header, bg=c['primary_dark'])
        heading.pack(side=tk.LEFT)
        tk.Label(heading, text='Network Overview', bg=c['primary_dark'], fg=c['light'],
                 font=('Segoe UI', 21, 'bold')).pack(anchor=tk.W)
        tk.Label(heading, text='A live view of your connection and local network',
                 bg=c['primary_dark'], fg=c['muted'], font=('Segoe UI', 10)).pack(anchor=tk.W)
        self.live_badge = tk.Label(header, text='●  LIVE MONITORING', bg=c['secondary'],
                                   fg=c['light'], font=('Segoe UI', 9, 'bold'), padx=13, pady=9)
        self.live_badge.pack(side=tk.RIGHT)
        tk.Button(header, text='◉', command=self.show_monitor, bg=c['primary'], fg=c['light'],
                  activebackground=c['secondary'], activeforeground=c['light'], bd=0,
                  font=('Segoe UI', 14), padx=8).pack(side=tk.RIGHT, padx=(0, 10))
        self.search_entry = tk.Entry(header, width=24, bg=c['primary'], fg=c['muted'],
                                     insertbackground=c['light'], relief=tk.FLAT,
                                     highlightbackground=c['border'], highlightthickness=1,
                                     font=('Segoe UI', 10))
        self.search_entry.insert(0, 'Search tools...')
        self.search_entry.pack(side=tk.RIGHT, ipady=9, padx=(0, 10))
        self.search_entry.bind('<FocusIn>', lambda _: self.search_entry.delete(0, tk.END)
                               if self.search_entry.get() == 'Search tools...' else None)
        self.search_entry.bind('<Return>', self.search_tools)

        cards = tk.Frame(page, bg=c['primary_dark'])
        cards.pack(fill=tk.X, pady=(0, 14))
        stat_cards = [
            ('Public IP', 'ip', 'IP', c['info'], 'External address'),
            ('Connection', 'connection', 'NET', c['success'], 'Active interface'),
            ('Download now', 'download', '↓', c['success'], 'Current transfer rate'),
            ('Upload now', 'upload', '↑', c['warning'], 'Current transfer rate'),
        ]
        for index, (title, key, glyph, color, caption) in enumerate(stat_cards):
            cards.grid_columnconfigure(index, weight=1, uniform='stats')
            card = GlassStatCard(cards, title, glyph, caption, color, c['primary_dark'])
            card.grid(row=0, column=index, sticky='nsew', padx=(0 if index == 0 else 6,
                                                                0 if index == 3 else 6))
            setattr(self, f'dashboard_{key}_label', card.value)
            if key == 'connection':
                self.connection_card = card
            if key == 'ip':
                self.public_ip_card = card

        middle = tk.Frame(page, bg=c['primary_dark'])
        middle.pack(fill=tk.BOTH, expand=True, pady=(0, 14))
        middle.grid_columnconfigure(0, weight=7, uniform='middle')
        middle.grid_columnconfigure(1, weight=4, uniform='middle')
        middle.grid_rowconfigure(0, weight=1)
        chart_panel, chart_body = self.dashboard_panel(
            middle, 'Traffic performance', 'Live download and upload in Mbps')
        chart_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 7))
        selector = tk.Frame(chart_body, bg=c['primary'])
        selector.pack(fill=tk.X, pady=(0, 4))
        tk.Label(selector, text='INTERFACE', bg=c['primary'], fg=c['muted'],
                 font=('Segoe UI', 8, 'bold')).pack(side=tk.LEFT)
        self.traffic_interface = tk.StringVar(value='All interfaces')
        traffic_options = ['All interfaces'] + list(psutil.net_io_counters(pernic=True) or {})
        ttk.Combobox(selector, textvariable=self.traffic_interface, values=traffic_options,
                     state='readonly', width=22).pack(side=tk.RIGHT)
        self.traffic_interface.trace_add('write', self.reset_traffic_samples)
        self.dashboard_graph = tk.Frame(chart_body, bg=c['primary'])
        self.dashboard_graph.pack(fill=tk.BOTH, expand=True)

        share_panel, share_body = self.dashboard_panel(
            middle, 'Traffic distribution', 'Current download and upload share')
        share_panel.grid(row=0, column=1, sticky='nsew', padx=(7, 0))
        self.donut_canvas = tk.Canvas(share_body, width=160, height=132, bg=c['primary'],
                                      highlightthickness=0)
        self.donut_canvas.pack(expand=True, fill=tk.BOTH)
        self.donut_total_label = tk.Label(share_body, text='0.00 Mbps total', bg=c['primary'],
                                          fg=c['light'], font=('Segoe UI', 13, 'bold'))
        self.donut_total_label.pack()
        self.donut_legend = tk.Label(share_body, text='● Download  0%     ● Upload  0%',
                                     bg=c['primary'], fg=c['muted'], font=('Segoe UI', 9))
        self.donut_canvas.pack_forget()
        self.donut_total_label.pack_forget()
        self.donut_legend.pack(side=tk.BOTTOM, pady=(3, 0))
        self.donut_total_label.pack(side=tk.BOTTOM)
        self.donut_canvas.pack(expand=True, fill=tk.BOTH)
        self.donut_canvas.bind('<Configure>', lambda _: self.update_traffic_donut(*getattr(self, 'donut_rates', (0, 0))))
        self.update_traffic_donut(0, 0)

        bottom = tk.Frame(page, bg=c['primary_dark'])
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        middle.pack_forget()
        middle.pack(fill=tk.BOTH, expand=True, pady=(0, 14))
        for index in range(3):
            bottom.grid_columnconfigure(index, weight=1, uniform='bottom')
        activity_panel, activity_body = self.dashboard_panel(
            bottom, 'Recent activity', 'Latest network checks and events')
        activity_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        self.activity_labels = []
        for _ in range(3):
            item = tk.Label(activity_body, text='No recent activity', bg=c['primary'],
                            fg=c['muted'], anchor=tk.W, font=('Segoe UI', 9))
            item.pack(fill=tk.X, pady=2)
            self.activity_labels.append(item)
        insights_panel, insights_body = self.dashboard_panel(
            bottom, 'Network at a glance', 'Current local information')
        insights_panel.grid(row=0, column=1, sticky='nsew', padx=6)
        self.insight_labels = {}
        for title, key in [('Local IP', 'local_ip'), ('DNS servers', 'dns'), ('Devices found', 'devices')]:
            row = tk.Frame(insights_body, bg=c['primary'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=title, bg=c['primary'], fg=c['muted'],
                     anchor=tk.W, width=15, font=('Segoe UI', 9)).pack(side=tk.LEFT)
            value = tk.Label(row, text='—', bg=c['primary'], fg=c['light'],
                             anchor=tk.E, font=('Segoe UI', 9, 'bold'))
            value.pack(side=tk.RIGHT)
            self.insight_labels[key] = value
        interfaces_panel, interfaces_body = self.dashboard_panel(
            bottom, 'Interface activity', 'Traffic share since system start')
        interfaces_panel.grid(row=0, column=2, sticky='nsew', padx=(6, 0))
        self.interface_bar_canvas = tk.Canvas(interfaces_body, height=74, bg=c['primary'],
                                              highlightthickness=0)
        self.interface_bar_canvas.pack(fill=tk.BOTH, expand=True)
        self.interface_bar_canvas.bind('<Configure>', lambda _: self.update_interface_bars())
        self.update_interface_bars()

    def dashboard_panel(self, parent, title, subtitle):
        height = 250 if title in ('Traffic performance', 'Traffic distribution') else 170
        panel = GlassPanel(parent, title, subtitle, height=height)
        return panel, panel.body

    def init_ip_info_tab(self):
        """Initialize IP info tab"""
        tab = self.tabs["ip_info"]

        # Create notebook for IP details
        ip_notebook = ttk.Notebook(tab)
        ip_notebook.pack(fill=tk.BOTH, expand=True)

        # Public IP frame
        public_frame = ttk.Frame(ip_notebook)
        ip_notebook.add(public_frame, text="🌍 Public IP")

        # Local IP frame
        local_frame = ttk.Frame(ip_notebook)
        ip_notebook.add(local_frame, text="🏠 Local Network")

        # IP Tools frame
        tools_frame = ttk.Frame(ip_notebook)
        ip_notebook.add(tools_frame, text="🛠️ IP Tools")

        # Initialize public IP section
        public_header = ttk.Frame(public_frame)
        public_header.pack(fill=tk.X, pady=10)

        ttk.Label(public_header,
                text="Your Public IP Information",
                style='Title.TLabel').pack(side=tk.LEFT)

        refresh_btn = ttk.Button(public_header,
                               text="🔄 Refresh",
                               command=self.refresh_ip_info,
                               style='TButton')
        refresh_btn.pack(side=tk.RIGHT)

        self.public_ip_tree = ttk.Treeview(public_frame,
                                         columns=("Property", "Value"),
                                         show="headings",
                                         height=12)
        self.public_ip_tree.heading("Property", text="Property")
        self.public_ip_tree.heading("Value", text="Value")
        self.public_ip_tree.column("Property", width=200, anchor=tk.W)
        self.public_ip_tree.column("Value", width=400, anchor=tk.W)
        self.public_ip_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Initialize local IP section
        local_header = ttk.Frame(local_frame)
        local_header.pack(fill=tk.X, pady=10)

        ttk.Label(local_header,
                text="Your Local Network Information",
                style='Title.TLabel').pack(side=tk.LEFT)

        refresh_local_btn = ttk.Button(local_header,
                                     text="🔄 Refresh",
                                     command=self.refresh_local_info,
                                     style='TButton')
        refresh_local_btn.pack(side=tk.RIGHT)

        self.local_ip_tree = ttk.Treeview(local_frame,
                                        columns=("Property", "Value"),
                                        show="headings",
                                        height=12)
        self.local_ip_tree.heading("Property", text="Property")
        self.local_ip_tree.heading("Value", text="Value")
        self.local_ip_tree.column("Property", width=200, anchor=tk.W)
        self.local_ip_tree.column("Value", width=400, anchor=tk.W)
        self.local_ip_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Initialize IP Tools section
        tools_header = ttk.Frame(tools_frame)
        tools_header.pack(fill=tk.X, pady=10)

        ttk.Label(tools_header,
                text="IP Tools",
                style='Title.TLabel').pack(side=tk.LEFT)

        # IP Lookup tool
        lookup_frame = ttk.Frame(tools_frame)
        lookup_frame.pack(fill=tk.X, pady=10, padx=10)

        ttk.Label(lookup_frame,
                text="IP Lookup:",
                style='Subtitle.TLabel').pack(anchor=tk.W)

        lookup_input_frame = ttk.Frame(lookup_frame)
        lookup_input_frame.pack(fill=tk.X, pady=5)

        self.ip_lookup_entry = ttk.Entry(lookup_input_frame)
        self.ip_lookup_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        lookup_btn = ttk.Button(lookup_input_frame,
                              text="Lookup",
                              command=self.lookup_ip,
                              style='TButton')
        lookup_btn.pack(side=tk.LEFT, padx=5)

        self.ip_lookup_result = scrolledtext.ScrolledText(lookup_frame,
                                                        height=8,
                                                        bg=self.colors['primary'],
                                                        fg=self.colors['light'],
                                                        insertbackground=self.colors['light'])
        self.ip_lookup_result.pack(fill=tk.BOTH, expand=True, pady=5)

    def init_network_tools_tab(self):
        """Initialize network tools tab"""
        tab = self.tabs["network"]

        analysis_frame = ttk.Frame(tab)
        analysis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Ping test section
        ping_section = ttk.LabelFrame(analysis_frame,
                                    text=" Ping Test ",
                                    style='TFrame')
        ping_section.pack(fill=tk.X, pady=5)

        ping_frame = ttk.Frame(ping_section)
        ping_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(ping_frame,
                text="Target:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)

        self.ping_target = ttk.Entry(ping_frame)
        self.ping_target.insert(0, "8.8.8.8")
        self.ping_target.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ping_btn = ttk.Button(ping_frame,
                            text="Ping",
                            command=self.run_ping_test,
                            style='Accent.TButton')
        ping_btn.pack(side=tk.LEFT, padx=5)

        self.ping_result = scrolledtext.ScrolledText(ping_section,
                                                   height=5,
                                                   bg=self.colors['primary'],
                                                   fg=self.colors['light'],
                                                   insertbackground=self.colors['light'])
        self.ping_result.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        # Port scanner section
        port_section = ttk.LabelFrame(analysis_frame,
                                    text=" Port Scanner ",
                                    style='TFrame')
        port_section.pack(fill=tk.BOTH, expand=True, pady=5)

        port_frame = ttk.Frame(port_section)
        port_frame.pack(fill=tk.X, pady=5, padx=5)

        ttk.Label(port_frame,
                text="Target:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)

        self.port_target = ttk.Entry(port_frame)
        self.port_target.insert(0, "localhost")
        self.port_target.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        port_btn = ttk.Button(port_frame,
                            text="Scan Ports",
                            command=self.run_port_scan,
                            style='Accent.TButton')
        port_btn.pack(side=tk.LEFT, padx=5)

        self.port_result = scrolledtext.ScrolledText(port_section,
                                                   height=5,
                                                   bg=self.colors['primary'],
                                                   fg=self.colors['light'],
                                                   insertbackground=self.colors['light'])
        self.port_result.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

    def init_dns_tools_tab(self):
        """Initialize DNS tools tab"""
        tab = self.tabs["dns"]

        dns_notebook = ttk.Notebook(tab)
        dns_notebook.pack(fill=tk.BOTH, expand=True)

        # DNS lookup frame
        lookup_frame = ttk.Frame(dns_notebook)
        dns_notebook.add(lookup_frame, text="🔍 DNS Lookup")

        # DNS leak test frame
        leak_frame = ttk.Frame(dns_notebook)
        dns_notebook.add(leak_frame, text="🛡️ DNS Resolver Check")

        # DNS lookup section
        lookup_header = ttk.Frame(lookup_frame)
        lookup_header.pack(fill=tk.X, pady=10)

        ttk.Label(lookup_header,
                text="DNS Lookup",
                style='Title.TLabel').pack(side=tk.LEFT)

        lookup_input_frame = ttk.Frame(lookup_frame)
        lookup_input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(lookup_input_frame,
                text="Domain:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)

        self.dns_domain = ttk.Entry(lookup_input_frame)
        self.dns_domain.insert(0, "google.com")
        self.dns_domain.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(lookup_input_frame,
                text="Type:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)

        self.dns_type = ttk.Combobox(lookup_input_frame,
                                   values=["A", "AAAA", "MX", "NS", "TXT", "CNAME"])
        self.dns_type.current(0)
        self.dns_type.pack(side=tk.LEFT, padx=5)

        lookup_btn = ttk.Button(lookup_input_frame,
                              text="Lookup",
                              command=self.run_dns_lookup,
                              style='Accent.TButton')
        lookup_btn.pack(side=tk.LEFT, padx=5)

        self.dns_result = scrolledtext.ScrolledText(lookup_frame,
                                                  height=10,
                                                  bg=self.colors['primary'],
                                                  fg=self.colors['light'],
                                                  insertbackground=self.colors['light'])
        self.dns_result.pack(fill=tk.BOTH, expand=True, pady=5)

        extra = ttk.Frame(lookup_frame)
        extra.pack(fill=tk.X, pady=6)
        ttk.Button(extra, text="Compare resolvers", command=self.compare_dns_resolvers,
                   style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(extra, text="Reverse IP (PTR)", command=self.reverse_dns_lookup).pack(side=tk.LEFT, padx=5)
        ttk.Label(extra, text="Compare system, Cloudflare and Google DNS; or enter an IP above for PTR.",
                  style='Data.TLabel').pack(side=tk.LEFT, padx=8)

        # DNS leak test section
        leak_header = ttk.Frame(leak_frame)
        leak_header.pack(fill=tk.X, pady=10)

        ttk.Label(leak_header,
                text="DNS Resolver Check",
                style='Title.TLabel').pack(side=tk.LEFT)

        leak_btn = ttk.Button(leak_frame,
                            text="Check DNS Resolvers",
                            command=self.run_dns_leak_test,
                            style='Accent.TButton')
        leak_btn.pack(pady=10)

        self.leak_result = scrolledtext.ScrolledText(leak_frame,
                                                   height=10,
                                                   bg=self.colors['primary'],
                                                   fg=self.colors['light'],
                                                   insertbackground=self.colors['light'])
        self.leak_result.pack(fill=tk.BOTH, expand=True, pady=5)

    def init_speed_test_tab(self):
        """Initialize speed test tab"""
        tab = self.tabs["speed"]

        speed_frame = ttk.Frame(tab)
        speed_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        control_frame = ttk.Frame(speed_frame)
        control_frame.pack(fill=tk.X, pady=10)

        self.speed_test_btn = ttk.Button(control_frame,
                                       text="Start Speed Test",
                                       command=self.run_speed_test_gui,
                                       style='Big.TButton')
        self.speed_test_btn.pack(pady=10)

        results_frame = ttk.Frame(speed_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Download speed
        download_frame = ttk.Frame(results_frame)
        download_frame.pack(fill=tk.X, pady=5)

        ttk.Label(download_frame,
                text="Download Speed:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.download_speed = ttk.Label(download_frame,
                                      text="0 Mbps",
                                      style='Title.TLabel',
                                      foreground=self.colors['success'])
        self.download_speed.pack(side=tk.RIGHT)

        # Upload speed
        upload_frame = ttk.Frame(results_frame)
        upload_frame.pack(fill=tk.X, pady=5)

        ttk.Label(upload_frame,
                text="Upload Speed:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.upload_speed = ttk.Label(upload_frame,
                                    text="0 Mbps",
                                    style='Title.TLabel',
                                    foreground=self.colors['warning'])
        self.upload_speed.pack(side=tk.RIGHT)

        # Ping
        ping_frame = ttk.Frame(results_frame)
        ping_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ping_frame,
                text="Ping:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.ping_speed = ttk.Label(ping_frame,
                                  text="0 ms",
                                  style='Title.TLabel',
                                  foreground=self.colors['info'])
        self.ping_speed.pack(side=tk.RIGHT)

        # Server
        server_frame = ttk.Frame(results_frame)
        server_frame.pack(fill=tk.X, pady=5)

        ttk.Label(server_frame,
                text="Test Server:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)
        self.server_info = ttk.Label(server_frame,
                                   text="Not connected",
                                   style='Data.TLabel')
        self.server_info.pack(side=tk.RIGHT)

    def init_devices_tab(self):
        """Initialize devices tab"""
        tab = self.tabs["devices"]
        self.device_store = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'NetworkMaster')
        os.makedirs(self.device_store, exist_ok=True)
        try:
            with open(os.path.join(self.device_store, 'devices.json'), encoding='utf-8') as f:
                self.device_aliases = json.load(f)
        except (OSError, ValueError):
            self.device_aliases = {}


        devices_frame = ttk.Frame(tab)
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        controls = ttk.Frame(devices_frame)
        controls.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(controls, text="Interface:").pack(side=tk.LEFT, padx=5)
        self.scan_interface = tk.StringVar()
        self.scan_interface_box = ttk.Combobox(controls, textvariable=self.scan_interface,
                                                values=list(self.get_scan_interfaces()), state='readonly', width=22)
        self.scan_interface_box.pack(side=tk.LEFT, padx=5)
        if self.scan_interface_box['values']:
            self.scan_interface_box.current(0)
        ttk.Label(controls, text="CIDR:").pack(side=tk.LEFT, padx=5)
        self.scan_cidr = ttk.Entry(controls, width=20)
        self.scan_cidr.pack(side=tk.LEFT, padx=5)
        self.scan_interface_box.bind('<<ComboboxSelected>>', self.set_default_scan_cidr)
        self.set_default_scan_cidr()
        ttk.Label(devices_frame, text="Scans up to 256 addresses on the selected local network.",
                  style='Data.TLabel').pack(anchor=tk.W, pady=(0, 8))

        self.devices_tree = ttk.Treeview(devices_frame,
                                       columns=("IP", "MAC", "Hostname", "Vendor", "Model"),
                                       show="headings")
        self.devices_tree.heading("IP", text="IP Address")
        self.devices_tree.heading("MAC", text="MAC Address")
        self.devices_tree.heading("Hostname", text="Hostname")
        self.devices_tree.heading("Vendor", text="Manufacturer")
        self.devices_tree.heading("Model", text="Model / notes")
        self.devices_tree.column("Model", width=180)
        self.devices_tree.bind('<Double-1>', self.rename_device)

        self.devices_tree.column("IP", width=150)
        self.devices_tree.column("MAC", width=150)
        self.devices_tree.column("Hostname", width=200)
        self.devices_tree.column("Vendor", width=250)
        toolbar = ttk.Frame(devices_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        self.device_filter = tk.StringVar()
        ttk.Label(toolbar, text='Search devices').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(toolbar, textvariable=self.device_filter, width=24).pack(side=tk.LEFT)
        self.device_filter.trace_add('write', lambda *_: self.update_devices())
        ttk.Button(toolbar, text='Name / model', command=self.rename_device).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text='Copy IP', command=self.copy_device_ip).pack(side=tk.LEFT)
        ttk.Button(toolbar, text='Export CSV', command=self.export_devices).pack(side=tk.RIGHT)
        ttk.Button(toolbar, text='Identify devices', command=self.identify_devices).pack(side=tk.RIGHT, padx=8)
        scroll = ttk.Scrollbar(devices_frame, command=self.devices_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.devices_tree.configure(yscrollcommand=scroll.set)
        self.devices_tree.pack(fill=tk.BOTH, expand=True)
        self.devices_tree.tag_configure('alternate', background='#142C60')


        scan_btn = ttk.Button(devices_frame,
                            text="Scan Network Devices  ?",
                            command=self.scan_network_devices_gui,
                            style='Accent.TButton')
        scan_btn.pack(pady=10)
        self.devices_scan_btn = scan_btn

    def selected_device_values(self):
        selected = self.devices_tree.selection()
        return self.devices_tree.item(selected[0], 'values') if selected else None

    def rename_device(self, event=None):
        values = self.selected_device_values()
        if not values:
            self.update_status('Select a device first')
            return
        previous = self.device_aliases.get(values[1].lower(), {})
        name = simpledialog.askstring('Device name', 'Friendly name:',
                                       initialvalue=previous.get('name', ''), parent=self.root)
        if name is None:
            return
        model = simpledialog.askstring('Device model', 'Model or notes (optional):',
                                        initialvalue=previous.get('model', ''), parent=self.root)
        if model is None:
            return
        self.device_aliases[values[1].lower()] = {'name': name.strip(), 'model': model.strip()}
        try:
            path = os.path.join(self.device_store, 'devices.json')
            with open(path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(self.device_aliases, f, ensure_ascii=False, indent=2)
            os.replace(path + '.tmp', path)
        except OSError as error:
            messagebox.showerror('Save device', str(error), parent=self.root)
        self.update_devices()

    def copy_device_ip(self):
        values = self.selected_device_values()
        if values:
            self.root.clipboard_clear()
            self.root.clipboard_append(values[0])
            self.update_status('Device IP copied')

    def export_devices(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv',
                                           filetypes=[('CSV', '*.csv')], initialfile='devices.csv')
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['IP', 'MAC', 'Name', 'Manufacturer', 'Model / notes'])
                    for item in self.devices_tree.get_children():
                        writer.writerow(self.devices_tree.item(item, 'values'))
                self.update_status('Visible devices exported')
            except OSError as error:
                messagebox.showerror('Export devices', str(error), parent=self.root)

    def identify_devices(self):
        devices = self.results.get('devices', [])
        if devices:
            threading.Thread(target=self.enrich_devices, args=(devices,), daemon=True).start()
        else:
            self.update_status('Scan the local network first')

    def enrich_devices(self, devices):
        """Bounded local PTR/NetBIOS lookups; manufacturer data is cached locally."""
        if getattr(self, 'identifying_devices', False):
            return
        self.identifying_devices = True
        self.update_status('Identifying device names and manufacturers...')
        try:
            advertised = self.discover_device_models(devices)
            vendors = {}
            path = os.path.join(self.device_store, 'oui.csv')
            if not os.path.exists(path):
                try:
                    response = requests.get('https://standards-oui.ieee.org/oui/oui.csv', timeout=(3, 10))
                    response.raise_for_status()
                    if 'Assignment' in response.text[:256]:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                except (requests.RequestException, OSError):
                    pass
            if os.path.exists(path):
                with open(path, encoding='utf-8-sig') as f:
                    vendors = {r['Assignment']: r['Organization Name'] for r in csv.DictReader(f)}
            def identify(device):
                result = dict(device)
                result.update(advertised.get(device['ip'], {}))
                mac = re.sub('[^0-9A-F]', '', device['mac'].upper())
                result['vendor'] = ('Private / randomized MAC' if int(mac[:2], 16) & 2
                                    else vendors.get(mac[:6], 'Not in manufacturer database'))
                try:
                    resolver = dns.resolver.Resolver()
                    answer = resolver.resolve(ipaddress.ip_address(device['ip']).reverse_pointer,
                                              'PTR', lifetime=1.5)
                    result['hostname'] = str(answer[0]).rstrip('.')
                except Exception:
                    if platform.system() == 'Windows':
                        try:
                            reply = subprocess.run(['nbtstat', '-A', device['ip']], capture_output=True,
                                                    text=True, timeout=2, creationflags=0x08000000)
                            names = re.findall(r'^\s*(\S+)\s+<00>\s+UNIQUE', reply.stdout, re.M)
                            if names:
                                result['hostname'] = names[0]
                        except (OSError, subprocess.TimeoutExpired):
                            pass
                return result
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                for result in pool.map(identify, devices):
                    def apply(result=result):
                        if self.results.get('devices') is devices:
                            for device in devices:
                                if device['ip'] == result['ip'] and device['mac'] == result['mac']:
                                    device.update(result)
                            self.update_devices()
                    self.ui(apply)
            self.update_status('Identification complete; unadvertised names/models can be entered manually')
        except (OSError, ValueError, KeyError) as error:
            self.update_status(f'Device identification unavailable: {error}')
        finally:
            self.identifying_devices = False

    def discover_device_models(self, devices):
        """Read names/models advertised by UPnP devices on the selected network."""
        from urllib.parse import urlsplit
        import xml.etree.ElementTree as ET
        known = {d['ip'] for d in devices}
        locations, found = {}, {}
        request = (b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
                   b'MAN: "ssdp:discover"\r\nMX: 1\r\nST: upnp:rootdevice\r\n\r\n')
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.3)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.sendto(request, ('239.255.255.250', 1900))
                deadline = time.monotonic() + 1.8
                while time.monotonic() < deadline:
                    try:
                        data, sender = sock.recvfrom(8192)
                    except socket.timeout:
                        continue
                    if sender[0] not in known:
                        continue
                    match = re.search(r'^location:\s*(\S+)', data.decode('utf-8', 'replace'), re.I | re.M)
                    if match:
                        url = urlsplit(match[1])
                        if url.scheme == 'http' and url.hostname == sender[0] and not url.username:
                            locations[sender[0]] = match[1]
        except OSError:
            return found
        def read_description(item):
            ip, url = item
            try:
                with requests.Session() as session:
                    session.trust_env = False
                    with session.get(url, timeout=(1, 2), allow_redirects=False, stream=True) as response:
                        response.raise_for_status()
                        data = bytearray()
                        for chunk in response.iter_content(8192):
                            data.extend(chunk)
                            if len(data) > 262144:
                                return ip, {}
                    root = ET.fromstring(data)
                    device = root.find('.//{*}device')
                    if device is None:
                        return ip, {}
                    result = {}
                    for tag, key in [('friendlyName', 'hostname'), ('modelName', 'model')]:
                        value = device.findtext('{*}' + tag)
                        if value:
                            result[key] = value.strip()[:160]
                    return ip, result
            except (requests.RequestException, ET.ParseError, ValueError):
                return ip, {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            found.update(pool.map(read_description, locations.items()))
        return found

    def init_geolocation_tab(self):
        """Initialize geolocation tab"""
        tab = self.tabs["geo"]

        geo_frame = ttk.Frame(tab)
        geo_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        input_frame = ttk.Frame(geo_frame)
        input_frame.pack(fill=tk.X, pady=10)

        ttk.Label(input_frame,
                text="IP Address:",
                style='Subtitle.TLabel').pack(side=tk.LEFT)

        self.geo_ip_entry = ttk.Entry(input_frame)
        self.geo_ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        geo_btn = ttk.Button(input_frame,
                           text="Locate",
                           command=self.locate_ip,
                           style='Accent.TButton')
        geo_btn.pack(side=tk.LEFT)

        results_frame = ttk.Frame(geo_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.geo_tree = ttk.Treeview(results_frame,
                                    columns=("Property", "Value"),
                                    show="headings",
                                    height=8)
        self.geo_tree.heading("Property", text="Property")
        self.geo_tree.heading("Value", text="Value")
        self.geo_tree.column("Property", width=150)
        self.geo_tree.column("Value", width=300)
        self.geo_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.map_frame = ttk.Frame(results_frame)
        self.map_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        ttk.Label(self.map_frame,
                text="Map will appear here",
                style='Subtitle.TLabel').pack(expand=True)

    def init_security_tab(self):
        """Initialize security tab"""
        tab = self.tabs["security"]

        security_frame = ttk.Frame(tab)
        security_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(security_frame,
                text="Security Checks",
                style='Title.TLabel').pack(anchor=tk.W)

        security_btn = ttk.Button(security_frame,
                                text="Run Security Scan",
                                command=self.run_security_scan,
                                style='Accent.TButton')
        security_btn.pack(pady=10)

        self.security_result = scrolledtext.ScrolledText(security_frame,
                                                      height=15,
                                                      bg=self.colors['primary'],
                                                      fg=self.colors['light'],
                                                      insertbackground=self.colors['light'])
        self.security_result.pack(fill=tk.BOTH, expand=True)

    def init_monitor_tab(self):
        tab = self.tabs['monitor']
        frame = ttk.Frame(tab, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Monitor & History", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 12))
        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, pady=8)
        ttk.Label(controls, text="Host:").pack(side=tk.LEFT)
        self.monitor_host = ttk.Entry(controls, width=20)
        self.monitor_host.insert(0, '1.1.1.1')
        self.monitor_host.pack(side=tk.LEFT, padx=6)
        ttk.Label(controls, text="Alert above ms:").pack(side=tk.LEFT)
        self.monitor_threshold = ttk.Entry(controls, width=8)
        self.monitor_threshold.insert(0, '500')
        self.monitor_threshold.pack(side=tk.LEFT, padx=6)
        self.monitor_devices = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Watch new devices (every 60s)",
                        variable=self.monitor_devices).pack(side=tk.LEFT, padx=8)
        self.monitor_button = ttk.Button(controls, text="Start monitoring", command=self.toggle_monitor,
                                         style='Accent.TButton')
        self.monitor_button.pack(side=tk.RIGHT)
        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Save snapshot", command=self.save_snapshot).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Export JSON", command=lambda: self.export_history('json')).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Export CSV", command=lambda: self.export_history('csv')).pack(side=tk.LEFT, padx=4)
        self.monitor_log = scrolledtext.ScrolledText(frame, bg=self.colors['primary'],
                                                      fg=self.colors['light'], height=18)
        self.monitor_log.pack(fill=tk.BOTH, expand=True, pady=8)
        self.monitor_log.insert(tk.END, "Monitoring is off. Start it to record reachability and latency.\n")

    def add_history(self, event, details):
        record = {'time': datetime.now().astimezone().isoformat(timespec='seconds'),
                  'event': event, 'details': details}
        self.history.append(record)
        if len(self.history) > 1000:
            self.history.pop(0)
        self.ui(lambda item=record: self.monitor_log.insert(
            tk.END, f"{item['time']}  {item['event']}: {json.dumps(item['details'], ensure_ascii=False)}\n"))
        self.ui(self.refresh_dashboard_activity)

    def refresh_dashboard_activity(self):
        recent = list(reversed(self.history[-3:]))
        for index, label in enumerate(self.activity_labels):
            if index < len(recent):
                item = recent[index]
                stamp = item['time'][11:19]
                label.config(text=f"●  {stamp}   {item['event'].replace('_', ' ').title()}",
                             fg=self.colors['light'])
            else:
                label.config(text='No recent activity', fg=self.colors['muted'])

    def save_snapshot(self):
        self.add_history('snapshot', json.loads(json.dumps(self.results, default=str)))
        self.update_status('Snapshot added to history')

    def export_history(self, format_name):
        if not self.history:
            self.save_snapshot()
        filename = filedialog.asksaveasfilename(defaultextension=f'.{format_name}',
                    filetypes=[(format_name.upper(), f'*.{format_name}')])
        if not filename:
            return
        try:
            if format_name == 'json':
                with open(filename, 'w', encoding='utf-8') as handle:
                    json.dump(self.history, handle, ensure_ascii=False, indent=2)
            else:
                with open(filename, 'w', encoding='utf-8-sig', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=['time', 'event', 'details'])
                    writer.writeheader()
                    for item in self.history:
                        writer.writerow({**item, 'details': json.dumps(item['details'], ensure_ascii=False)})
            self.update_status(f'Exported {len(self.history)} records')
        except OSError as error:
            messagebox.showerror('Export failed', str(error))

    def toggle_monitor(self):
        if self.monitoring:
            self.monitoring = False
            self.monitor_generation += 1
            self.monitor_button.config(text='Start monitoring')
            self.update_status('Monitoring stopped')
            return
        try:
            host = self.monitor_host.get().strip()
            threshold = float(self.monitor_threshold.get())
            if not host or not (0 < threshold <= 60000):
                raise ValueError('Enter a host and a threshold between 1 and 60000 ms.')
        except ValueError as error:
            messagebox.showerror('Monitor settings', str(error))
            return
        self.monitoring = True
        self.monitor_host_value = host
        self.monitor_threshold_value = threshold
        self.monitor_generation += 1
        self.known_devices = None
        self.monitor_tick_count = 0
        self.monitor_button.config(text='Stop monitoring')
        self._monitor_tick(self.monitor_generation)

    def _monitor_tick(self, generation):
        if not self.monitoring or generation != self.monitor_generation:
            return
        if not self.monitor_busy:
            self.monitor_busy = True
            host = self.monitor_host_value
            threshold = self.monitor_threshold_value
            scan_devices = self.monitor_devices.get() and self.monitor_tick_count % 4 == 0
            interface = self.scan_interface.get()
            cidr = self.scan_cidr.get()
            threading.Thread(target=self._monitor_worker,
                             args=(host, threshold, scan_devices, interface, cidr), daemon=True).start()
        self.monitor_tick_count += 1
        holder = {}
        def scheduled_tick():
            self.monitor_after_ids.remove(holder['id'])
            self._monitor_tick(generation)
        holder['id'] = self.root.after(15000, scheduled_tick)
        self.monitor_after_ids.append(holder['id'])

    def _monitor_worker(self, host, threshold, scan_devices, interface, cidr):
        start = time.monotonic()
        try:
            with socket.create_connection((host, 443), timeout=4):
                pass
            latency = round((time.monotonic() - start) * 1000, 1)
            status = 'slow' if latency > threshold else 'online'
        except OSError:
            latency, status = None, 'offline'
        if not self.monitoring:
            self.monitor_busy = False
            return
        self.add_history('connectivity', {'host': host, 'status': status, 'tcp_ms': latency})
        if status != 'online':
            self.update_status(f'Alert: {host} is {status}')
        if scan_devices:
            try:
                devices = self.scan_network_devices(interface, cidr)
                current = {device['mac'] for device in devices}
                if self.known_devices is not None:
                    for mac in current - self.known_devices:
                        self.add_history('new_device', {'mac': mac, 'ip': next(
                            item['ip'] for item in devices if item['mac'] == mac)})
                        self.update_status(f'Alert: new device {mac}')
                self.known_devices = current
            except Exception as error:
                self.add_history('device_scan_error', {'error': str(error)})
        self.monitor_busy = False

    def run_initial_scans(self):
        """Run initial scans in background"""
        threading.Thread(target=self._initial_scans_thread, daemon=True).start()

    def _initial_scans_thread(self):
        """Thread for initial scans"""
        self.update_status("Running initial scans...")
        self.results["network_info"] = self.get_network_info()
        self.ui(self.update_dashboard)
        self.ui(self.update_ip_info)
        self.results["ip_info"] = self.get_public_ip_info()
        self.ui(self.update_dashboard_ip)
        self.ui(self.update_ip_info)
        self.load_public_ip_flag()
        self.update_status("Initial scans completed" if "ip" in self.results["ip_info"]
                           else "Public IP unavailable; local monitoring is ready")

    def get_public_ip_info(self):
        """Get public IP info with API fallback handling"""
        for service in self.api_services:
            try:
                response = requests.get(service, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if "ip" in data and ipaddress.ip_address(data["ip"]).is_global:
                        return data
            except (requests.RequestException, ValueError, KeyError):
                continue
        return {"error": "Public IP unavailable"}

    def load_public_ip_flag(self):
        data = self.results.get('ip_info', {})
        ip = data.get('ip')
        if ip:
            threading.Thread(target=self._country_flag_worker,
                             args=(ip, data.get('country') or data.get('country_code')),
                             daemon=True).start()

    def _country_flag_worker(self, ip, code):
        try:
            if not code:
                for url in (f'https://ipwho.is/{ip}', f'https://ipinfo.io/{ip}/json',
                            f'https://ipapi.co/{ip}/json/'):
                    try:
                        response = requests.get(url, timeout=3)
                        response.raise_for_status()
                        data = response.json()
                        code = data.get('country_code') or data.get('country')
                        if code and re.fullmatch(r'[A-Za-z]{2}', code):
                            if self.results.get('ip_info', {}).get('ip') == ip:
                                self.results['ip_info'].update(data)
                                self.ui(self.update_ip_info)
                            break
                    except (requests.RequestException, ValueError):
                        continue
            if not code or not re.fullmatch(r'[A-Za-z]{2}', code):
                return
            code = code.upper()
            response = requests.get(f'https://flagcdn.com/w80/{code.lower()}.png', timeout=4)
            response.raise_for_status()
            flag = Image.open(io.BytesIO(response.content)).convert('RGBA').resize((28, 20))
            self.ui(lambda image=flag, country=code: self._apply_country_flag(ip, country, image))
        except (requests.RequestException, OSError, ValueError):
            if code and re.fullmatch(r'[A-Za-z]{2}', code):
                self.ui(lambda country=code.upper(): self._apply_country_code(ip, country))

    def _apply_country_code(self, ip, code):
        if self.results.get('ip_info', {}).get('ip') == ip:
            self.public_ip_card.set_country_code(code)

    def _apply_country_flag(self, ip, code, image):
        if self.results.get('ip_info', {}).get('ip') != ip:
            return
        self.country_flag_photo = ImageTk.PhotoImage(image)
        self.public_ip_card.set_flag(self.country_flag_photo)

    def get_network_info(self):
        """Get detailed network information"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            mac = ":".join(["{:02x}".format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(5, -1, -1)])

            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            connection_type = "Wi-Fi" if "Wi-Fi" in interfaces else "Ethernet" if "Ethernet" in interfaces else "Unknown"
            speed = next((s.speed for s in stats.values() if s.speed > 0), 0)

            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "mac_address": mac,
                "connection_type": connection_type,
                "speed": f"{speed} Mbps",
                "interfaces": {iface: [addr._asdict() for addr in addrs]
                              for iface, addrs in interfaces.items()}
            }
        except Exception as e:
            return {"error": str(e)}

    def refresh_ip_info(self):
        """Refresh public IP information"""
        threading.Thread(target=self._refresh_ip_info_thread, daemon=True).start()

    def _refresh_ip_info_thread(self):
        """Thread for refreshing IP info"""
        self.update_status("Refreshing IP information...")
        self.results["ip_info"] = self.get_public_ip_info()
        self.ui(self.update_ip_info)
        self.ui(self.update_dashboard_ip)
        self.load_public_ip_flag()

        self.update_status("IP information refreshed")

    def refresh_local_info(self):
        """Refresh local network information"""
        threading.Thread(target=self._refresh_local_info_thread, daemon=True).start()

    def _refresh_local_info_thread(self):
        """Thread for refreshing local network info"""
        self.update_status("Refreshing local network information...")
        self.results["network_info"] = self.get_network_info()
        self.ui(self.update_ip_info)
        self.ui(self.update_dashboard_network)
        self.update_status("Local network information refreshed")

    def run_full_scan(self):
        """Run complete network scan"""
        interface = self.scan_interface.get()
        if interface:
            try:
                network = self.validate_scan_network(interface, self.scan_cidr.get())
            except ValueError as error:
                messagebox.showerror('Scan range', str(error))
                return
            cidr = str(network)
        else:
            cidr = None
        self.update_status("Starting full network scan...")

        # Disable scan button during scan
        self.full_scan_btn.config(state=tk.DISABLED)

        # Run in background
        threading.Thread(target=self._full_scan_thread,
                         args=(interface or None, cidr), daemon=True).start()

    def _full_scan_thread(self, interface, cidr):
        """Thread for full scan"""
        try:
            # IP and network info
            self.results["ip_info"] = self.get_public_ip_info()
            self.results["network_info"] = self.get_network_info()

            # DNS info
            self.results["dns_info"] = self.get_dns_info()

            # Speed test
            self.results["speed_test"] = self.run_speed_test()

            # Network devices
            self.results["devices"] = self.scan_network_devices(interface, cidr)

            # Geolocation
            if "ip" in self.results["ip_info"]:
                self.results["location"] = self.get_geolocation(self.results["ip_info"]["ip"])

            # Update all UI elements
            self.ui(self.update_all_tabs)
            self.add_history('full_scan', json.loads(json.dumps(self.results, default=str)))

            self.ui(self.update_dashboard_ip)
            self.load_public_ip_flag()
            self.update_status("Full scan completed successfully")
        except Exception as e:
            self.ui(lambda error=str(e): messagebox.showerror("Scan Error", f"An error occurred during scan:\n{error}"))
            self.update_status(f"Scan failed: {str(e)}")
        finally:
            # Re-enable scan button
            self.ui(lambda: self.full_scan_btn.config(state=tk.NORMAL))

    def run_ping_test(self):
        """Run ping test and display results"""
        target = self.ping_target.get()
        if not target:
            messagebox.showerror("Error", "Please enter a target to ping")
            return

        self.update_status(f"Pinging {target}...")
        self.ping_result.delete(1.0, tk.END)

        threading.Thread(target=self._ping_thread, args=(target,), daemon=True).start()

    def _ping_thread(self, target):
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            count = "4"
            command = ["ping", param, count, target]
            output = subprocess.check_output(command, universal_newlines=True, timeout=15)
            self.ui(lambda: self.ping_result.insert(tk.END, output))
            self.update_status(f"Ping to {target} completed")
        except Exception as e:
            self.ui(lambda error=str(e): self.ping_result.insert(tk.END, f"Ping failed: {error}"))
            self.update_status(f"Ping to {target} failed")

    def run_port_scan(self):
        """Run basic port scan"""
        target = self.port_target.get()
        if not target:
            messagebox.showerror("Error", "Please enter a target to scan")
            return

        self.update_status(f"Scanning ports on {target}...")
        self.port_result.delete(1.0, tk.END)

        threading.Thread(target=self._port_scan_thread, args=(target,), daemon=True).start()

    def _port_scan_thread(self, target):
        try:
            socket.getaddrinfo(target, None)
            common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389]
            lines = [f"Scanning common ports on {target}:\n"]
            for port in common_ports:
                try:
                    with socket.create_connection((target, port), timeout=1):
                        lines.append(f"Port {port}: OPEN")
                except (ConnectionRefusedError, TimeoutError, OSError):
                    lines.append(f"Port {port}: not reachable")
            self.ui(lambda output="\n".join(lines): self.port_result.insert(tk.END, output))
            self.update_status(f"Port scan on {target} completed")
        except Exception as e:
            self.ui(lambda error=str(e): self.port_result.insert(tk.END, f"Port scan failed: {error}"))
            self.update_status(f"Port scan on {target} failed")

    def run_dns_lookup(self):
        """Perform DNS lookup"""
        domain = self.dns_domain.get()
        record_type = self.dns_type.get()

        if not domain:
            messagebox.showerror("Error", "Please enter a domain name")
            return

        self.update_status(f"Performing {record_type} lookup for {domain}...")
        self.dns_result.delete(1.0, tk.END)

        threading.Thread(target=self._dns_lookup_thread, args=(domain, record_type), daemon=True).start()

    def _dns_lookup_thread(self, domain, record_type):
        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = 8
            answers = resolver.resolve(domain, record_type)
            output = f"{record_type} records for {domain}:\n\n" + "\n".join(str(rdata) for rdata in answers)
            self.ui(lambda: self.dns_result.insert(tk.END, output))

            self.update_status(f"DNS lookup for {domain} completed")
        except Exception as e:
            self.ui(lambda error=str(e): self.dns_result.insert(tk.END, f"DNS lookup failed: {error}"))
            self.update_status(f"DNS lookup for {domain} failed")

    def compare_dns_resolvers(self):
        domain = self.dns_domain.get().strip()
        if not domain:
            messagebox.showerror('DNS comparison', 'Enter a domain name.')
            return
        self.dns_result.delete(1.0, tk.END)
        threading.Thread(target=self._compare_dns_thread, args=(domain,), daemon=True).start()

    def _compare_dns_thread(self, domain):
        for label, server in [('System', None), ('Cloudflare', '1.1.1.1'), ('Google', '8.8.8.8')]:
            try:
                resolver = dns.resolver.Resolver(configure=server is None)
                if server:
                    resolver.nameservers = [server]
                resolver.lifetime = 5
                started = time.monotonic()
                answers = resolver.resolve(domain, 'A')
                elapsed = (time.monotonic() - started) * 1000
                line = f"{label}: {elapsed:.0f} ms | {', '.join(str(a) for a in answers)}\n"
            except Exception as error:
                line = f"{label}: {error}\n"
            self.ui(lambda value=line: self.dns_result.insert(tk.END, value))
        self.update_status('DNS comparison completed')

    def reverse_dns_lookup(self):
        value = self.dns_domain.get().strip()
        try:
            ipaddress.ip_address(value)
        except ValueError:
            messagebox.showerror('Reverse DNS', 'Enter a valid IP address in the Domain field.')
            return
        self.dns_result.delete(1.0, tk.END)
        threading.Thread(target=self._reverse_dns_thread, args=(value,), daemon=True).start()

    def _reverse_dns_thread(self, ip):
        try:
            answer = dns.resolver.resolve_address(ip, lifetime=8)
            output = '\n'.join(str(item) for item in answer)
        except Exception as error:
            output = f'Reverse lookup failed: {error}'
        self.ui(lambda: self.dns_result.insert(tk.END, output))

    def run_dns_leak_test(self):
        """Show configured resolvers; this cannot establish DNS leak status."""
        self.update_status("Checking DNS resolvers...")
        self.leak_result.delete(1.0, tk.END)
        threading.Thread(target=self._dns_resolver_thread, daemon=True).start()

    def _dns_resolver_thread(self):
        try:
            resolver = dns.resolver.Resolver(configure=True)
            resolver.lifetime = 8
            servers = ", ".join(str(server) for server in resolver.nameservers) or "Unknown"
            answer = resolver.resolve("example.com", "A")
            output = (f"Configured DNS servers: {servers}\n"
                      f"Example resolution: {', '.join(str(item) for item in answer)}\n\n"
                      "This checks local DNS configuration and resolution only. "
                      "A DNS leak test requires an external controlled DNS endpoint.")
            self.ui(lambda: self.leak_result.insert(tk.END, output))
            self.update_status("DNS resolver check completed")
        except Exception as e:
            self.ui(lambda error=str(e): self.leak_result.insert(tk.END, f"DNS check failed: {error}"))
            self.update_status("DNS resolver check failed")

    def run_speed_test_gui(self):
        """Run speed test with GUI updates"""
        self.update_status("Starting speed test...")
        self.speed_test_btn.config(state=tk.DISABLED)
        self.download_speed.config(text="Testing...")
        self.upload_speed.config(text="Testing...")
        self.ping_speed.config(text="Testing...")
        self.server_info.config(text="Connecting...")

        threading.Thread(target=self._speed_test_thread, daemon=True).start()

    def _speed_test_thread(self):
        """Thread for speed test"""
        try:
            st = speedtest.Speedtest()

            # Get best server
            self.ui(lambda: self.server_info.config(text="Finding best server..."))
            st.get_best_server()
            self.ui(lambda: self.server_info.config(
                text=f"{st.results.server['name']} ({st.results.server['country']})"
            ))

            # Test download speed
            self.ui(lambda: self.download_speed.config(text="Testing..."))
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            self.ui(lambda: self.download_speed.config(
                text=f"{download_speed:.2f} Mbps"
            ))

            # Test upload speed
            self.ui(lambda: self.upload_speed.config(text="Testing..."))
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            self.ui(lambda: self.upload_speed.config(
                text=f"{upload_speed:.2f} Mbps"
            ))

            # Get ping
            ping = st.results.ping
            self.ui(lambda: self.ping_speed.config(
                text=f"{ping:.2f} ms"
            ))

            # Save results
            self.results["speed_test"] = {
                "download": f"{download_speed:.2f} Mbps",
                "upload": f"{upload_speed:.2f} Mbps",
                "ping": f"{ping:.2f} ms",
                "server": st.results.server['name']
            }
            self.add_history('speed_test', dict(self.results["speed_test"]))

            self.update_status("Speed test completed")
        except Exception as e:
            self.ui(lambda error=str(e): messagebox.showerror(
                "Speed Test Error",
                f"An error occurred during speed test:\n{error}"
            ))
            self.update_status(f"Speed test failed: {str(e)}")
        finally:
            self.ui(lambda: self.speed_test_btn.config(state=tk.NORMAL))

    def scan_network_devices_gui(self):
        """Scan for network devices with GUI updates"""
        self.update_status("Scanning network devices...")

        # Clear previous results
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)

        # Show loading message
        self.devices_tree.insert("", tk.END, values=("Scanning...", "", "", ""))
        try:
            network = self.validate_scan_network(self.scan_interface.get(), self.scan_cidr.get())
        except ValueError as error:
            self.update_devices()
            messagebox.showerror("Scan range", str(error))
            return
        self.devices_scan_btn.config(state=tk.DISABLED)
        threading.Thread(target=self._scan_devices_thread,
                         args=(self.scan_interface.get(), str(network)), daemon=True).start()

    def _scan_devices_thread(self, interface, cidr):
        """Thread for scanning network devices"""
        try:
            devices = self.scan_network_devices(interface, cidr)
            self.results["devices"] = devices
            self.ui(self.update_devices)
            self.add_history('device_scan', {'cidr': cidr, 'interface': interface, 'devices': devices})
            self.update_status(f"Found {len(devices)} network devices")
            self.enrich_devices(devices)
        except Exception as e:
            self.ui(lambda error=str(e): messagebox.showerror(
                "Scan Error",
                f"An error occurred during device scan:\n{error}"
            ))
            self.update_status(f"Device scan failed: {str(e)}")
        finally:
            self.ui(lambda: self.devices_scan_btn.config(state=tk.NORMAL))

    def locate_ip(self):
        """Geolocate an IP address"""
        ip = self.geo_ip_entry.get()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return

        self.update_status(f"Locating IP: {ip}...")

        # Clear previous results
        for item in self.geo_tree.get_children():
            self.geo_tree.delete(item)

        threading.Thread(target=self._locate_ip_thread, args=(ip,), daemon=True).start()

    def _locate_ip_thread(self, ip):
        """Thread for geolocating IP"""
        try:
            response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
            if response.status_code == 200:
                data = response.json()

                # Display in treeview
                for key, value in data.items():
                    if key not in ["readme", "ip"]:
                        self.ui(lambda k=key, v=value: self.geo_tree.insert(
                            "", tk.END, values=(k.capitalize(), v)
                        ))

                # Create map if coordinates available
                if "loc" in data:
                    import folium
                    lat, lon = map(float, data["loc"].split(","))

                    m = folium.Map(location=[lat, lon], zoom_start=10)
                    folium.Marker([lat, lon], popup=ip).add_to(m)

                    map_file = os.path.join(os.getcwd(), "temp_map.html")
                    m.save(map_file)

                    webbrowser.open(f"file://{map_file}")

                # Save results
                self.results["location"] = data
                self.update_status(f"Location found for IP: {ip}")
            else:
                self.ui(lambda code=response.status_code: messagebox.showerror(
                    "Location Error",
                    f"Could not locate IP: {ip}\nStatus code: {code}"
                ))
                self.update_status(f"Failed to locate IP: {ip}")
        except Exception as e:
            self.ui(lambda error=str(e): messagebox.showerror(
                "Location Error",
                f"An error occurred during geolocation:\n{error}"
            ))
            self.update_status(f"Geolocation failed: {str(e)}")

    def lookup_ip(self):
        """Lookup IP information"""
        ip = self.ip_lookup_entry.get()
        if not ip:
            messagebox.showerror("Error", "Please enter an IP address")
            return

        self.update_status(f"Looking up IP: {ip}...")
        self.ip_lookup_result.delete(1.0, tk.END)

        threading.Thread(target=self._lookup_ip_thread, args=(ip,), daemon=True).start()

    def _lookup_ip_thread(self, ip):
        """Thread for IP lookup"""
        try:
            services = [
                ("ipinfo.io", f"https://ipinfo.io/{ip}/json"),
                ("ipapi.co", f"https://ipapi.co/{ip}/json/")
            ]

            self.ui(lambda: self.ip_lookup_result.insert(
                tk.END, f"IP Lookup Results for {ip}:\n\n"))

            for name, url in services:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()

                        self.ui(lambda n=name, d=data: self.ip_lookup_result.insert(
                            tk.END, f"=== {n} ===\n"))

                        for key, value in data.items():
                            if key not in ["readme", "ip"]:
                                self.ui(lambda k=key, v=value: self.ip_lookup_result.insert(
                                    tk.END, f"{k.capitalize()}: {v}\n"))

                        self.ui(lambda: self.ip_lookup_result.insert(
                            tk.END, "\n"))
                    else:
                        self.ui(lambda n=name, code=response.status_code: self.ip_lookup_result.insert(
                            tk.END, f"{n} returned status code {code}\n\n"))
                except Exception as e:
                    self.ui(lambda n=name, e=e: self.ip_lookup_result.insert(
                        tk.END, f"Error with {n}: {str(e)}\n\n"))

            self.update_status(f"IP lookup completed for {ip}")
        except Exception as e:
            self.ui(lambda error=str(e): self.ip_lookup_result.insert(
                tk.END, f"IP lookup failed: {error}\n"))
            self.update_status(f"IP lookup failed: {str(e)}")

    def run_security_scan(self):
        """Run basic, measured local security checks."""
        self.update_status("Running security scan...")
        self.security_result.delete(1.0, tk.END)
        threading.Thread(target=self._security_scan_thread, daemon=True).start()

    def _security_scan_thread(self):
        try:
            net_info = self.get_network_info()
            dns_info = self.get_dns_info()
            lines = ["Local network checks:",
                     f"Local IP: {net_info.get('local_ip', 'Unknown')}",
                     f"DNS servers: {', '.join(map(str, dns_info.get('DNS Servers', []))) or 'Unknown'}",
                     "\nTCP ports reachable on localhost:"]
            for port in (80, 443, 22, 3389):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        state = "reachable"
                except OSError:
                    state = "not reachable"
                lines.append(f"Port {port}: {state}")
            lines.append("\nThis is a limited local check, not a vulnerability assessment.")
            self.ui(lambda output="\n".join(lines): self.security_result.insert(tk.END, output))
            self.update_status("Security scan completed")
        except Exception as e:
            self.ui(lambda error=str(e): self.security_result.insert(tk.END, f"Security scan failed: {error}"))
            self.update_status(f"Security scan failed: {str(e)}")

    def get_dns_info(self):
        """Get DNS information"""
        try:
            resolver = dns.resolver.Resolver()
            nameservers = resolver.nameservers

            test_domain = "google.com"
            a_record = str(resolver.resolve(test_domain, "A")[0])

            return {
                "DNS Servers": nameservers,
                f"{test_domain} A Record": a_record
            }
        except Exception as e:
            return {"error": str(e)}

    def run_speed_test(self):
        """Run speed test and return results"""
        try:
            st = speedtest.Speedtest()
            st.get_best_server()

            return {
                "download": f"{st.download() / 1_000_000:.2f} Mbps",
                "upload": f"{st.upload() / 1_000_000:.2f} Mbps",
                "ping": f"{st.results.ping:.2f} ms",
                "server": st.results.server['name']
            }
        except Exception as e:
            return {"error": str(e)}

    def get_scan_interfaces(self):
        """Return active local IPv4 interfaces by name."""
        stats = psutil.net_if_stats()
        result = {}
        for name, addrs in psutil.net_if_addrs().items():
            if not stats.get(name) or not stats[name].isup:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = ipaddress.ip_address(addr.address)
                    if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                        result[name] = addr.address
                        break
        return result

    def set_default_scan_cidr(self, *_):
        local_ip = self.get_scan_interfaces().get(self.scan_interface.get())
        self.scan_cidr.delete(0, tk.END)
        if local_ip:
            self.scan_cidr.insert(0, str(ipaddress.ip_network(f"{local_ip}/24", strict=False)))

    def validate_scan_network(self, interface, cidr):
        local_ip = self.get_scan_interfaces().get(interface)
        if not local_ip:
            raise ValueError("Select an active private IPv4 interface.")
        try:
            network = ipaddress.ip_network(cidr.strip(), strict=False)
        except ValueError as error:
            raise ValueError(f"Invalid CIDR: {error}") from error
        if network.version != 4 or network.num_addresses > 256 or ipaddress.ip_address(local_ip) not in network:
            raise ValueError("Choose an IPv4 range of at most 256 addresses containing the interface IP.")
        return network

    def scan_network_devices(self, interface=None, cidr=None):
        """Probe the selected local IPv4 range and return observed ARP neighbors."""
        interfaces = self.get_scan_interfaces()
        interface = interface or next(iter(interfaces), None)
        if not interface:
            return []
        local_ip = interfaces[interface]
        network = self.validate_scan_network(interface, cidr or f"{local_ip}/24")
        def probe(ip):
            if str(ip) == local_ip:
                return
            param = "-n" if platform.system().lower() == "windows" else "-c"
            timeout_param = ["-w", "300"] if platform.system().lower() == "windows" else ["-W", "1"]
            try:
                subprocess.run(["ping", param, "1", *timeout_param, str(ip)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            except subprocess.TimeoutExpired:
                pass
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            list(pool.map(probe, network.hosts()))
        arp = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10)
        if arp.returncode != 0:
            raise RuntimeError("Could not read ARP table")
        devices = []
        for ip, mac in re.findall(r"(?m)^\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:-]{17})\b", arp.stdout):
            if ipaddress.ip_address(ip) in network and ip != local_ip and mac.lower() != "ff-ff-ff-ff-ff-ff":
                devices.append({"ip": ip, "mac": mac, "hostname": "", "vendor": ""})
        return devices

    def get_geolocation(self, ip):
        """Get geolocation for an IP address"""
        try:
            response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"error": f"Status code {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def update_dashboard(self):
        """Update dashboard tab"""
        self.update_dashboard_ip()
        self.update_dashboard_network()
        self.update_dashboard_insights()
        self.update_network_graph()

    def update_dashboard_ip(self):
        """Update IP info on dashboard"""
        ip = self.results["ip_info"].get("ip")
        label = ip or "Unavailable"
        if hasattr(self, 'public_ip_card') and getattr(self, 'displayed_flag_ip', None) != ip:
            self.public_ip_card.set_country_code('IP')
            self.displayed_flag_ip = ip
        size = 11 if len(label) > 25 else 14 if len(label) > 17 else 17
        self.dashboard_ip_label.config(text=label, font=('Segoe UI', size, 'bold'))
        self.quick_ip_label.config(text=label)

    def update_dashboard_network(self):
        """Update network info on dashboard"""
        info = self.results["network_info"]
        text = info.get("connection_type", "Unknown")
        self.connection_card.caption.config(text=info.get('local_ip', 'Active interface'))
        self.dashboard_connection_label.config(text=text)
        self.update_dashboard_insights()

    def update_dashboard_insights(self):
        network = self.results.get('network_info', {})
        dns_data = self.results.get('dns_info', {})
        nameservers = dns_data.get('DNS Servers', [])
        self.insight_labels['local_ip'].config(text=network.get('local_ip', '—'))
        self.insight_labels['dns'].config(text=str(nameservers[0]) if nameservers else '—')
        devices = self.results.get('devices', [])
        self.insight_labels['devices'].config(text=str(len(devices)) if isinstance(devices, list) else '—')

    def update_interface_bars(self, counters=None):
        if not hasattr(self, 'interface_bar_canvas'):
            return
        canvas = self.interface_bar_canvas
        canvas.delete('all')
        if counters is None:
            counters = psutil.net_io_counters(pernic=True) or {}
        items = sorted(((name, data.bytes_sent + data.bytes_recv)
                        for name, data in counters.items()), key=lambda item: item[1], reverse=True)[:3]
        width = max(220, canvas.winfo_width())
        maximum = max((value for _, value in items), default=1) or 1
        for index, (name, value) in enumerate(items):
            y = 12 + index * 24
            label = name if len(name) <= 15 else name[:12] + '…'
            canvas.create_text(4, y, text=label, anchor=tk.W, fill=self.colors['muted'],
                               font=('Segoe UI', 8))
            canvas.create_rectangle(125, y-5, width-12, y+3, fill='#20366B', outline='')
            length = max(2, (width-137) * value / maximum)
            canvas.create_rectangle(125, y-5, 125+length, y+3,
                                    fill=self.colors['accent'], outline='')

    def sample_traffic(self):
        """Sample interface counters each second for current transfer rates."""
        try:
            all_counters = psutil.net_io_counters(pernic=True) or {}
            counters = all_counters
            now = time.monotonic()
            selected = self.traffic_interface.get() if hasattr(self, 'traffic_interface') else 'All interfaces'
            if selected != 'All interfaces':
                counters = {selected: counters[selected]} if selected in counters else {}
            sent = sum(item.bytes_sent for item in counters.values())
            received = sum(item.bytes_recv for item in counters.values())
            if self.last_counters is not None and self.last_sample_time is not None:
                elapsed = max(now - self.last_sample_time, 0.001)
                upload = max(0, sent - self.last_counters[0]) * 8 / elapsed / 1_000_000
                download = max(0, received - self.last_counters[1]) * 8 / elapsed / 1_000_000
                self.traffic_samples.append((download, upload))
                self.dashboard_download_label.config(text=f"{download:.2f} Mbps")
                self.dashboard_upload_label.config(text=f"{upload:.2f} Mbps")
                if hasattr(self, 'donut_canvas'):
                    self.update_traffic_donut(download, upload)
                self.update_network_graph()
                self.update_interface_bars(all_counters)
            else:
                self.dashboard_download_label.config(text="0.00 Mbps")
                self.dashboard_upload_label.config(text="0.00 Mbps")
                if hasattr(self, 'donut_canvas'):
                    self.update_traffic_donut(0, 0)
                self.update_network_graph()
            self.last_counters = (sent, received)
            self.last_sample_time = now
        except Exception as error:
            self.update_status(f"Traffic monitoring unavailable: {error}")
        finally:
            if not self.closed:
                self.traffic_after_id = self.root.after(2000, self.sample_traffic)

    def reset_traffic_samples(self, *_):
        self.last_counters = None
        self.last_sample_time = None
        self.traffic_samples.clear()

    def update_traffic_donut(self, download, upload):
        self.donut_rates = (download, upload)
        canvas = self.donut_canvas
        canvas.delete('all')
        total = download + upload
        c = self.colors
        size = 152
        ring = Image.new('RGB', (size*3, size*3), c['primary'])
        draw = ImageDraw.Draw(ring)
        bounds = (42, 30, 414, 402)
        draw.arc((42, 45, 414, 417), 0, 360, fill='#091540', width=64)
        draw.arc(bounds, 0, 360, fill='#142665', width=57)
        if total > 0:
            angle = 360 * download / total
            draw.arc(bounds, -90, -90+angle, fill='#7692FF', width=57)
            draw.arc(bounds, -90+angle, 270, fill='#ABD2FA', width=57)
            draw.arc((40, 28, 416, 404), -90, -90+angle,
                     fill='#7692FF', width=3)
        self.donut_image = ImageTk.PhotoImage(ring.resize((size, size), Image.Resampling.LANCZOS))
        center = max(80, canvas.winfo_width()/2)
        canvas.create_image(center, 68, image=self.donut_image)
        canvas.create_text(center, 61, text=f"{total:.1f}", fill=c['light'],
                           font=('Segoe UI', 20, 'bold'))
        canvas.create_text(center, 84, text='Mbps', fill=c['muted'],
                           font=('Segoe UI', 9))
        self.donut_total_label.config(text=f'{total:.2f} Mbps total')
        down_pct = round(download / total * 100) if total else 0
        up_pct = 100 - down_pct if total else 0
        self.donut_legend.config(text=f'↓ Download  {down_pct}%     ↑ Upload  {up_pct}%')

    def update_network_graph(self):
        """Draw the last minute of rates with a lightweight Tk canvas."""
        if self.notebook.select() != str(self.tabs['dashboard']):
            return
        if not hasattr(self, 'traffic_canvas'):
            self.traffic_canvas = tk.Canvas(self.dashboard_graph, bg=self.colors['primary'],
                                            highlightthickness=0, bd=0)
            self.traffic_canvas.pack(fill=tk.BOTH, expand=True)
            self.traffic_canvas.bind('<Configure>', lambda _: self.update_network_graph())
        canvas = self.traffic_canvas
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 100 or height < 80:
            return
        canvas.delete('all')
        left, top, right, bottom = 42, 14, width-18, height-27
        samples = list(self.traffic_samples)
        maximum = max(1.0, max((max(pair) for pair in samples), default=0) * 1.2)
        for index in range(5):
            y = top + (bottom-top) * index / 4
            canvas.create_line(left, y, right, y, fill='#344B87', width=1)
            canvas.create_text(left-8, y, text=f'{maximum*(4-index)/4:.1f}',
                               anchor=tk.E, fill=self.colors['muted'], font=('Segoe UI', 8))
        for index in range(5):
            x = left + (right-left) * index / 4
            canvas.create_line(x, top, x, bottom, fill='#142665', width=1)
        for item, color, glow in [(0, '#7692FF', '#253EC5'), (1, '#ABD2FA', '#1B5D9F')]:
            points = []
            for index, pair in enumerate(samples):
                x = left + (right-left) * (59-len(samples)+1+index) / 59
                y = bottom - (bottom-top) * pair[item] / maximum
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=glow, width=8, smooth=True)
                canvas.create_line(*points, fill=color, width=2.5, smooth=True)
                x, y = points[-2:]
                canvas.create_oval(x-4, y-4, x+4, y+4, fill=color, outline=self.colors['light'])
        canvas.create_line(left, bottom, right, bottom, fill=self.colors['border'])
        canvas.create_text(left, height-8, text='2 minutes ago', anchor=tk.W,
                           fill=self.colors['muted'], font=('Segoe UI', 8))
        canvas.create_text(right, height-8, text='Now', anchor=tk.E,
                           fill=self.colors['muted'], font=('Segoe UI', 8))

    def update_ip_info(self):
        """Update IP information tab"""
        if "ip_info" in self.results:
            for item in self.public_ip_tree.get_children():
                self.public_ip_tree.delete(item)

            for key, value in self.results["ip_info"].items():
                if key != "readme":
                    self.public_ip_tree.insert("", tk.END, values=(key.capitalize(), value))

        if "network_info" in self.results:
            for item in self.local_ip_tree.get_children():
                self.local_ip_tree.delete(item)

            net_info = self.results["network_info"]
            for key, value in net_info.items():
                if key not in ["interfaces"]:
                    self.local_ip_tree.insert("", tk.END, values=(key.capitalize(), value))

    def update_all_tabs(self):
        """Update all tabs with latest data"""
        self.update_dashboard()
        self.update_ip_info()
        self.update_devices()
        self.update_geolocation()
        speed = self.results.get('speed_test', {})
        if 'download' in speed:
            self.download_speed.config(text=speed['download'])
        if 'upload' in speed:
            self.upload_speed.config(text=speed['upload'])
        if 'ping' in speed:
            self.ping_speed.config(text=speed['ping'])
        if 'server' in speed:
            self.server_info.config(text=speed['server'])

    def update_devices(self):
        """Update connected devices tab"""
        if "devices" in self.results and isinstance(self.results["devices"], list):
            for item in self.devices_tree.get_children():
                self.devices_tree.delete(item)

            query = self.device_filter.get().casefold()
            for index, device in enumerate(self.results["devices"]):
                alias = self.device_aliases.get(device.get('mac', '').lower(), {})
                values = (device.get('ip', ''), device.get('mac', ''),
                          alias.get('name') or device.get('hostname') or 'Not advertised',
                          device.get('vendor') or 'Not identified',
                          alias.get('model') or device.get('model') or 'Not advertised')
                if query and query not in ' '.join(values).casefold():
                    continue
                self.devices_tree.insert('', tk.END, values=values,
                                         tags=('alternate',) if index % 2 else ())
            self.update_dashboard_insights()

    def update_geolocation(self):
        """Update geolocation tab"""
        if "location" in self.results and self.results["location"]:
            for item in self.geo_tree.get_children():
                self.geo_tree.delete(item)

            for key, value in self.results["location"].items():
                if key not in ["readme", "ip", "loc"]:
                    self.geo_tree.insert("", tk.END, values=(key.capitalize(), value))

if __name__ == "__main__":
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NetworkMaster.Desktop.App')
    root = tk.Tk()
    app = NetworkMasterPro(root)
    root.mainloop()
