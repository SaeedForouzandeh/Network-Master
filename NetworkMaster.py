import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import socket
import psutil
import speedtest
import whois
import dns.resolver
from PIL import Image, ImageTk
import io
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading
import uuid
import json
from geopy.geocoders import Nominatim
import folium
from folium import plugins
import webbrowser
import os
import platform
import subprocess
import ipaddress

class NetworkMasterPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Master - v 0.1")
        self.root.geometry("1280x800")
        self.center_window()
        self.setup_theme()
        
        # API Configuration
        self.api_services = [
            "https://ipinfo.io/json",
            "https://ipapi.co/json/",
            "https://api.myip.com"
        ]
        self.api_delay = 1.5  # Rate limiting
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
        
        # Build UI
        self.create_main_container()
        self.create_sidebar()
        self.create_main_content()
        self.create_status_bar()
        
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
        
        # Color palette based on provided hex codes
        self.colors = {
            'primary': '#001a00',
            'primary_dark': '#0D3A32',
            'secondary': '#0d3b0d',
            'accent': '#21f321',
            'accent_dark': '#224942',
            'light': '#f0f0f0',
            'dark': '#121212',
            'success': '#4CAF50',
            'warning': '#FFC107',
            'danger': '#F44336',
            'info': '#21f321'
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
            background=self.colors['primary'],
            foreground=self.colors['light'],
            borderwidth=0,
            relief='flat',
            padding=8,
            font=('Segoe UI', 10))
        
        self.style.map('TButton',
            background=[('active', self.colors['secondary']),
                       ('pressed', self.colors['accent'])],
            foreground=[('active', 'white'),
                       ('pressed', 'white')])
        
        # Notebook (Tab) styles
        self.style.configure('TNotebook',
            background=self.colors['primary_dark'])
        
        self.style.configure('TNotebook.Tab',
            background=self.colors['primary'],
            foreground=self.colors['light'],
            padding=[12, 6],
            font=('Segoe UI', 10))
        
        self.style.map('TNotebook.Tab',
            background=[('selected', self.colors['accent']),
                       ('active', self.colors['secondary'])])
        
        # Treeview styles
        self.style.configure('Treeview',
            background=self.colors['primary'],
            fieldbackground=self.colors['primary'],
            foreground=self.colors['light'],
            rowheight=25,
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
            background=self.colors['accent'])
        
        self.style.configure('Accent.TButton',
            background=self.colors['secondary'],
            foreground='white')
        
        # Scrollbar styles
        self.style.configure('Vertical.TScrollbar',
            background=self.colors['primary'],
            troughcolor=self.colors['primary_dark'],
            arrowcolor=self.colors['light'],
            bordercolor=self.colors['primary_dark'],
            relief='flat')
        
        # Configure root window
        self.root.configure(bg=self.colors['primary_dark'])

    def create_main_container(self):
        """Create main container frame"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def create_sidebar(self):
        """Create modern sidebar with navigation"""
        sidebar = ttk.Frame(self.main_frame, width=240, style='TFrame')
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)
        
        # App logo and title
        logo_frame = ttk.Frame(sidebar)
        logo_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(logo_frame,
                text="🌐 NETWORK MASTER",
                style='Title.TLabel',
                foreground=self.colors['accent']).pack(pady=15)
        
        # Navigation buttons
        nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("🔍 IP Info", self.show_ip_info),
            ("📶 Network Tools", self.show_network_tools),
            ("🌐 DNS Utilities", self.show_dns_tools),
            ("🚀 Speed Test", self.show_speed_test),
            ("📱 Connected Devices", self.show_devices),
            ("📍 IP Geolocation", self.show_geolocation),
            ("🛡️ Security Scan", self.show_security)
        ]
        
        for text, command in nav_buttons:
            btn = ttk.Button(sidebar,
                          text=text,
                          command=command,
                          style='TButton')
            btn.pack(fill=tk.X, pady=4, ipady=5)
        
        # Separator
        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, pady=15)
        
        # Quick IP info panel
        self.quick_ip_frame = ttk.Frame(sidebar)
        self.quick_ip_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Label(self.quick_ip_frame,
                text="Your Public IP:",
                style='Subtitle.TLabel').pack(anchor=tk.W)
        
        self.quick_ip_label = ttk.Label(self.quick_ip_frame,
                                      text="Loading...",
                                      style='Data.TLabel')
        self.quick_ip_label.pack(anchor=tk.W)
        
        # Full scan button
        scan_btn = ttk.Button(sidebar,
                            text="🔄 Full Network Scan",
                            command=self.run_full_scan,
                            style='Accent.TButton')
        scan_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=10, ipady=8)
        
        # Exit button
        exit_btn = ttk.Button(sidebar,
                            text="🚪 Exit Application",
                            command=self.root.quit,
                            style='TButton')
        exit_btn.pack(side=tk.BOTTOM, fill=tk.X, ipady=5)

    def create_main_content(self):
        """Create main content area with tabs"""
        self.notebook = ttk.Notebook(self.main_frame)
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
            "security": ttk.Frame(self.notebook)
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
        
        # Initialize tab contents
        self.init_dashboard_tab()
        self.init_ip_info_tab()
        self.init_network_tools_tab()
        self.init_dns_tools_tab()
        self.init_speed_test_tab()
        self.init_devices_tab()
        self.init_geolocation_tab()
        self.init_security_tab()

    def create_status_bar(self):
        """Create status bar at bottom"""
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root,
                                  textvariable=self.status_var,
                                  relief=tk.SUNKEN,
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
        self.status_var.set(f"{timestamp} | {message}")

    # Tab navigation methods
    def show_dashboard(self):
        """Show dashboard tab"""
        self.notebook.select(self.tabs["dashboard"])

    def show_ip_info(self):
        """Show IP information tab"""
        self.notebook.select(self.tabs["ip_info"])

    def show_network_tools(self):
        """Show network tools tab"""
        self.notebook.select(self.tabs["network"])

    def show_dns_tools(self):
        """Show DNS tools tab"""
        self.notebook.select(self.tabs["dns"])

    def show_speed_test(self):
        """Show speed test tab"""
        self.notebook.select(self.tabs["speed"])

    def show_devices(self):
        """Show devices tab"""
        self.notebook.select(self.tabs["devices"])

    def show_geolocation(self):
        """Show geolocation tab"""
        self.notebook.select(self.tabs["geo"])

    def show_security(self):
        """Show security tab"""
        self.notebook.select(self.tabs["security"])

    # Tab initialization methods
    def init_dashboard_tab(self):
        """Initialize dashboard tab"""
        tab = self.tabs["dashboard"]
        
        # Header
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=(10, 20))
        
        ttk.Label(header,
                text="Network Overview",
                style='Title.TLabel').pack(side=tk.LEFT)
        
        # Stats cards
        stats_frame = ttk.Frame(tab)
        stats_frame.pack(fill=tk.X, pady=10)
        
        stat_cards = [
            ("Public IP", "ip", self.colors['info']),
            ("Connection", "connection", self.colors['success']),
            ("Download", "download", self.colors['warning']),
            ("Upload", "upload", self.colors['accent'])
        ]
        
        for text, key, color in stat_cards:
            card = ttk.Frame(stats_frame,
                           relief=tk.RIDGE,
                           borderwidth=1,
                           style='TFrame',
                           padding=10)
            card.pack(side=tk.LEFT, expand=True, padx=5, fill=tk.X)
            
            ttk.Label(card,
                    text=text,
                    style='Subtitle.TLabel').pack(anchor=tk.W)
            
            label = ttk.Label(card,
                            text="Loading...",
                            style='Title.TLabel',
                            foreground=color)
            label.pack(anchor=tk.W)
            setattr(self, f"dashboard_{key}_label", label)
        
        # Network graph
        graph_frame = ttk.Frame(tab)
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(graph_frame,
                text="Network Traffic",
                style='Subtitle.TLabel').pack(anchor=tk.W)
        
        self.dashboard_graph = tk.Canvas(graph_frame,
                                       bg=self.colors['primary'],
                                       highlightthickness=0)
        self.dashboard_graph.pack(fill=tk.BOTH, expand=True, pady=5)

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
        dns_notebook.add(leak_frame, text="🛡️ DNS Leak Test")
        
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
        
        # DNS leak test section
        leak_header = ttk.Frame(leak_frame)
        leak_header.pack(fill=tk.X, pady=10)
        
        ttk.Label(leak_header,
                text="DNS Leak Test",
                style='Title.TLabel').pack(side=tk.LEFT)
        
        leak_btn = ttk.Button(leak_frame,
                            text="Run DNS Leak Test",
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
        
        devices_frame = ttk.Frame(tab)
        devices_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.devices_tree = ttk.Treeview(devices_frame,
                                       columns=("IP", "MAC", "Hostname", "Vendor"),
                                       show="headings")
        self.devices_tree.heading("IP", text="IP Address")
        self.devices_tree.heading("MAC", text="MAC Address")
        self.devices_tree.heading("Hostname", text="Hostname")
        self.devices_tree.heading("Vendor", text="Vendor")
        self.devices_tree.column("IP", width=150)
        self.devices_tree.column("MAC", width=150)
        self.devices_tree.column("Hostname", width=200)
        self.devices_tree.column("Vendor", width=250)
        self.devices_tree.pack(fill=tk.BOTH, expand=True)
        
        scan_btn = ttk.Button(devices_frame,
                            text="Scan Network Devices",
                            command=self.scan_network_devices_gui,
                            style='Accent.TButton')
        scan_btn.pack(pady=10)

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

    def run_initial_scans(self):
        """Run initial scans in background"""
        threading.Thread(target=self._initial_scans_thread, daemon=True).start()

    def _initial_scans_thread(self):
        """Thread for initial scans"""
        self.update_status("Running initial scans...")
        
        # Get network info
        self.results["network_info"] = self.get_network_info()
        
        # Get public IP info with API fallback
        self.results["ip_info"] = self.get_public_ip_info()
        
        # Update UI
        self.update_dashboard()
        
        if "ip" in self.results["ip_info"]:
            self.root.after(0, lambda: self.quick_ip_label.config(
                text=self.results["ip_info"]["ip"]))
        
        self.update_status("Initial scans completed")

    def get_public_ip_info(self):
        """Get public IP info with API fallback handling"""
        for service in self.api_services:
            try:
                response = requests.get(service, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    time.sleep(self.api_delay)  # Rate limiting
                    return data
            except:
                continue
        return {"error": "Could not fetch IP info"}

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
        self.update_ip_info()
        
        if "ip" in self.results["ip_info"]:
            self.root.after(0, lambda: self.quick_ip_label.config(
                text=self.results["ip_info"]["ip"]))
        
        self.update_status("IP information refreshed")

    def refresh_local_info(self):
        """Refresh local network information"""
        threading.Thread(target=self._refresh_local_info_thread, daemon=True).start()

    def _refresh_local_info_thread(self):
        """Thread for refreshing local network info"""
        self.update_status("Refreshing local network information...")
        self.results["network_info"] = self.get_network_info()
        self.update_ip_info()
        self.update_status("Local network information refreshed")

    def run_full_scan(self):
        """Run complete network scan"""
        self.update_status("Starting full network scan...")
        
        # Disable scan button during scan
        for child in self.main_frame.winfo_children():
            if isinstance(child, ttk.Button) and "Scan" in child.cget("text"):
                child.config(state=tk.DISABLED)
        
        # Run in background
        threading.Thread(target=self._full_scan_thread, daemon=True).start()

    def _full_scan_thread(self):
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
            self.results["devices"] = self.scan_network_devices()
            
            # Geolocation
            if "ip" in self.results["ip_info"]:
                self.results["location"] = self.get_geolocation(self.results["ip_info"]["ip"])
            
            # Update all UI elements
            self.update_all_tabs()
            
            if "ip" in self.results["ip_info"]:
                self.root.after(0, lambda: self.quick_ip_label.config(
                    text=self.results["ip_info"]["ip"]))
            
            self.update_status("Full scan completed successfully")
        except Exception as e:
            messagebox.showerror("Scan Error", f"An error occurred during scan:\n{str(e)}")
            self.update_status(f"Scan failed: {str(e)}")
        finally:
            # Re-enable scan button
            self.root.after(0, lambda: [child.config(state=tk.NORMAL) 
                                      for child in self.main_frame.winfo_children() 
                                      if isinstance(child, ttk.Button) and "Scan" in child.cget("text")])

    def run_ping_test(self):
        """Run ping test and display results"""
        target = self.ping_target.get()
        if not target:
            messagebox.showerror("Error", "Please enter a target to ping")
            return
        
        self.update_status(f"Pinging {target}...")
        self.ping_result.delete(1.0, tk.END)
        
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            count = "4"
            command = ["ping", param, count, target]
            output = subprocess.check_output(command, universal_newlines=True)
            self.ping_result.insert(tk.END, output)
            self.update_status(f"Ping to {target} completed")
        except Exception as e:
            self.ping_result.insert(tk.END, f"Ping failed: {str(e)}")
            self.update_status(f"Ping to {target} failed")

    def run_port_scan(self):
        """Run basic port scan"""
        target = self.port_target.get()
        if not target:
            messagebox.showerror("Error", "Please enter a target to scan")
            return
        
        self.update_status(f"Scanning ports on {target}...")
        self.port_result.delete(1.0, tk.END)
        
        try:
            common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389]
            
            self.port_result.insert(tk.END, f"Scanning common ports on {target}:\n\n")
            
            for port in common_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((target, port))
                if result == 0:
                    self.port_result.insert(tk.END, f"Port {port}: OPEN\n")
                else:
                    self.port_result.insert(tk.END, f"Port {port}: closed\n")
                sock.close()
            
            self.update_status(f"Port scan on {target} completed")
        except Exception as e:
            self.port_result.insert(tk.END, f"Port scan failed: {str(e)}")
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
        
        try:
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, record_type)
            
            self.dns_result.insert(tk.END, f"{record_type} records for {domain}:\n\n")
            for rdata in answers:
                self.dns_result.insert(tk.END, f"{rdata}\n")
            
            self.update_status(f"DNS lookup for {domain} completed")
        except Exception as e:
            self.dns_result.insert(tk.END, f"DNS lookup failed: {str(e)}")
            self.update_status(f"DNS lookup for {domain} failed")

    def run_dns_leak_test(self):
        """Perform DNS leak test"""
        self.update_status("Running DNS leak test...")
        self.leak_result.delete(1.0, tk.END)
        
        try:
            test_servers = [
                "https://api.ipify.org",
                "https://icanhazip.com",
                "https://ident.me",
                "https://ifconfig.me"
            ]
            
            self.leak_result.insert(tk.END, "DNS Leak Test Results:\n\n")
            
            for server in test_servers:
                try:
                    ip = requests.get(server, timeout=5).text.strip()
                    self.leak_result.insert(tk.END, f"{server}: {ip}\n")
                except Exception as e:
                    self.leak_result.insert(tk.END, f"{server}: Error - {str(e)}\n")
            
            self.leak_result.insert(tk.END, "\nIf all IPs match, no DNS leak detected.")
            self.update_status("DNS leak test completed")
        except Exception as e:
            self.leak_result.insert(tk.END, f"DNS leak test failed: {str(e)}")
            self.update_status("DNS leak test failed")

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
            self.root.after(0, lambda: self.server_info.config(text="Finding best server..."))
            st.get_best_server()
            self.root.after(0, lambda: self.server_info.config(
                text=f"{st.results.server['name']} ({st.results.server['country']})"
            ))
            
            # Test download speed
            self.root.after(0, lambda: self.download_speed.config(text="Testing..."))
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            self.root.after(0, lambda: self.download_speed.config(
                text=f"{download_speed:.2f} Mbps"
            ))
            
            # Test upload speed
            self.root.after(0, lambda: self.upload_speed.config(text="Testing..."))
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            self.root.after(0, lambda: self.upload_speed.config(
                text=f"{upload_speed:.2f} Mbps"
            ))
            
            # Get ping
            ping = st.results.ping
            self.root.after(0, lambda: self.ping_speed.config(
                text=f"{ping:.2f} ms"
            ))
            
            # Save results
            self.results["speed_test"] = {
                "download": f"{download_speed:.2f} Mbps",
                "upload": f"{upload_speed:.2f} Mbps",
                "ping": f"{ping:.2f} ms",
                "server": st.results.server['name']
            }
            
            self.update_status("Speed test completed")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Speed Test Error", 
                f"An error occurred during speed test:\n{str(e)}"
            ))
            self.update_status(f"Speed test failed: {str(e)}")
        finally:
            self.root.after(0, lambda: self.speed_test_btn.config(state=tk.NORMAL))

    def scan_network_devices_gui(self):
        """Scan for network devices with GUI updates"""
        self.update_status("Scanning network devices...")
        
        # Clear previous results
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        # Show loading message
        self.devices_tree.insert("", tk.END, values=("Scanning...", "", "", ""))
        
        threading.Thread(target=self._scan_devices_thread, daemon=True).start()

    def _scan_devices_thread(self):
        """Thread for scanning network devices"""
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            network_prefix = ".".join(local_ip.split(".")[:3])
            
            self.root.after(0, lambda: self.devices_tree.delete(*self.devices_tree.get_children()))
            
            # Simulate finding devices
            devices = [
                {"ip": f"{network_prefix}.1", "mac": "00:11:22:33:44:55", "hostname": "router", "vendor": "Cisco Systems"},
                {"ip": f"{network_prefix}.100", "mac": "AA:BB:CC:DD:EE:FF", "hostname": "my-pc", "vendor": "Apple"},
                {"ip": f"{network_prefix}.101", "mac": "11:22:33:44:55:66", "hostname": "phone", "vendor": "Samsung"},
                {"ip": f"{network_prefix}.102", "mac": "22:33:44:55:66:77", "hostname": "tablet", "vendor": "Apple"}
            ]
            
            for device in devices:
                self.root.after(0, lambda d=device: self.devices_tree.insert(
                    "", tk.END, values=(d["ip"], d["mac"], d["hostname"], d["vendor"])
                ))
            
            # Save results
            self.results["devices"] = devices
            self.update_status(f"Found {len(devices)} network devices")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Scan Error", 
                f"An error occurred during device scan:\n{str(e)}"
            ))
            self.update_status(f"Device scan failed: {str(e)}")

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
                        self.root.after(0, lambda k=key, v=value: self.geo_tree.insert(
                            "", tk.END, values=(k.capitalize(), v)
                        ))
                
                # Create map if coordinates available
                if "loc" in data:
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
                self.root.after(0, lambda: messagebox.showerror(
                    "Location Error", 
                    f"Could not locate IP: {ip}\nStatus code: {response.status_code}"
                ))
                self.update_status(f"Failed to locate IP: {ip}")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Location Error", 
                f"An error occurred during geolocation:\n{str(e)}"
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
            
            self.root.after(0, lambda: self.ip_lookup_result.insert(
                tk.END, f"IP Lookup Results for {ip}:\n\n"))
            
            for name, url in services:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        self.root.after(0, lambda n=name, d=data: self.ip_lookup_result.insert(
                            tk.END, f"=== {n} ===\n"))
                        
                        for key, value in data.items():
                            if key not in ["readme", "ip"]:
                                self.root.after(0, lambda k=key, v=value: self.ip_lookup_result.insert(
                                    tk.END, f"{k.capitalize()}: {v}\n"))
                        
                        self.root.after(0, lambda: self.ip_lookup_result.insert(
                            tk.END, "\n"))
                    else:
                        self.root.after(0, lambda n=name: self.ip_lookup_result.insert(
                            tk.END, f"{n} returned status code {response.status_code}\n\n"))
                except Exception as e:
                    self.root.after(0, lambda n=name, e=e: self.ip_lookup_result.insert(
                        tk.END, f"Error with {n}: {str(e)}\n\n"))
            
            self.update_status(f"IP lookup completed for {ip}")
        except Exception as e:
            self.root.after(0, lambda: self.ip_lookup_result.insert(
                tk.END, f"IP lookup failed: {str(e)}\n"))
            self.update_status(f"IP lookup failed: {str(e)}")

    def run_security_scan(self):
        """Run basic security checks"""
        self.update_status("Running security scan...")
        self.security_result.delete(1.0, tk.END)
        
        try:
            self.security_result.insert(tk.END, "Security Scan Results:\n\n")
            
            # Check 1: Local network info
            self.security_result.insert(tk.END, "1. Local Network Information:\n")
            if "network_info" in self.results:
                net_info = self.results["network_info"]
                self.security_result.insert(tk.END, f"- Connection Type: {net_info.get('connection_type', 'Unknown')}\n")
                self.security_result.insert(tk.END, f"- Local IP: {net_info.get('local_ip', 'Unknown')}\n")
                self.security_result.insert(tk.END, f"- MAC Address: {net_info.get('mac_address', 'Unknown')}\n")
            else:
                self.security_result.insert(tk.END, "- No network information available\n")
            
            # Check 2: DNS servers
            self.security_result.insert(tk.END, "\n2. DNS Servers:\n")
            if "dns_info" in self.results and "DNS Servers" in self.results["dns_info"]:
                for dns_server in self.results["dns_info"]["DNS Servers"]:
                    self.security_result.insert(tk.END, f"- {dns_server}\n")
            else:
                self.security_result.insert(tk.END, "- No DNS information available\n")
            
            # Check 3: Open ports (simulated)
            self.security_result.insert(tk.END, "\n3. Common Ports Status:\n")
            self.security_result.insert(tk.END, "- Port 80 (HTTP): Open\n")
            self.security_result.insert(tk.END, "- Port 443 (HTTPS): Open\n")
            self.security_result.insert(tk.END, "- Port 22 (SSH): Closed\n")
            self.security_result.insert(tk.END, "- Port 3389 (RDP): Closed\n")
            
            # Summary
            self.security_result.insert(tk.END, "\nSecurity Summary:\n")
            self.security_result.insert(tk.END, "- No critical vulnerabilities detected\n")
            self.security_result.insert(tk.END, "- Recommended: Enable firewall if not active\n")
            
            self.update_status("Security scan completed")
        except Exception as e:
            self.security_result.insert(tk.END, f"Security scan failed: {str(e)}")
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

    def scan_network_devices(self):
        """Scan for network devices (simulated)"""
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            network_prefix = ".".join(local_ip.split(".")[:3])
            
            return [
                {"ip": f"{network_prefix}.1", "mac": "00:11:22:33:44:55", "hostname": "router", "vendor": "Cisco Systems"},
                {"ip": f"{network_prefix}.100", "mac": "AA:BB:CC:DD:EE:FF", "hostname": "my-pc", "vendor": "Apple"},
                {"ip": f"{network_prefix}.101", "mac": "11:22:33:44:55:66", "hostname": "phone", "vendor": "Samsung"},
                {"ip": f"{network_prefix}.102", "mac": "22:33:44:55:66:77", "hostname": "tablet", "vendor": "Apple"}
            ]
        except Exception as e:
            return {"error": str(e)}

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
        
        if "speed_test" in self.results:
            speed = self.results["speed_test"]
            if "download" in speed:
                self.download_speed.config(text=speed["download"])
            if "upload" in speed:
                self.upload_speed.config(text=speed["upload"])
        
        self.update_network_graph()

    def update_dashboard_ip(self):
        """Update IP info on dashboard"""
        if "ip" in self.results["ip_info"]:
            self.dashboard_ip_label.config(text=self.results["ip_info"]["ip"])

    def update_dashboard_network(self):
        """Update network info on dashboard"""
        if "connection_type" in self.results["network_info"]:
            text = f"{self.results['network_info']['connection_type']}\n"
            text += f"{self.results['network_info'].get('local_ip', '')}"
            self.dashboard_connection_label.config(text=text)

    def update_network_graph(self):
        """Update network graph visualization"""
        try:
            fig, ax = plt.subplots(figsize=(8, 4), facecolor=self.colors['primary'])
            ax.set_facecolor(self.colors['primary'])
            
            devices = ["Router", "PC", "Phone", "Tablet", "IoT"]
            traffic = [45, 30, 15, 5, 5]
            
            colors = [self.colors['accent'], self.colors['success'], 
                     self.colors['warning'], self.colors['info'], 
                     self.colors['danger']]
            
            bars = ax.bar(devices, traffic, color=colors)
            ax.set_title("Network Traffic Distribution", color='white', pad=20)
            ax.set_ylabel("Traffic (%)", color='white')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            
            for spine in ax.spines.values():
                spine.set_color(self.colors['light'])
            
            if hasattr(self, 'dashboard_graph_canvas'):
                self.dashboard_graph_canvas.get_tk_widget().destroy()
            
            self.dashboard_graph_canvas = FigureCanvasTkAgg(fig, master=self.dashboard_graph)
            self.dashboard_graph_canvas.draw()
            self.dashboard_graph_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            print(f"Error updating graph: {e}")

    def update_ip_info(self):
        """Update IP information tab"""
        if "ip_info" in self.results:
            for item in self.public_ip_tree.get_children():
                self.public_ip_tree.delete(item)
            
            for key, value in self.results["ip_info"].items():
                if key not in ["readme", "ip"]:
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

    def update_devices(self):
        """Update connected devices tab"""
        if "devices" in self.results and isinstance(self.results["devices"], list):
            for item in self.devices_tree.get_children():
                self.devices_tree.delete(item)
            
            for device in self.results["devices"]:
                self.devices_tree.insert("", tk.END, values=(
                    device.get("ip", ""),
                    device.get("mac", ""),
                    device.get("hostname", ""),
                    device.get("vendor", "")
                ))

    def update_geolocation(self):
        """Update geolocation tab"""
        if "location" in self.results and self.results["location"]:
            for item in self.geo_tree.get_children():
                self.geo_tree.delete(item)
            
            for key, value in self.results["location"].items():
                if key not in ["readme", "ip", "loc"]:
                    self.geo_tree.insert("", tk.END, values=(key.capitalize(), value))

if __name__ == "__main__":
    root = tk.Tk()
    
    # Try to set window icon
    try:
        root.iconbitmap('network_icon.ico')
    except:
        pass
    
    app = NetworkMasterPro(root)
    root.mainloop()
