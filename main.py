#!/usr/bin/env python3
"""
Video Scraper Pro v2.0
Advanced scraping tool for video repositories
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox, END
import requests
import time
import json
import csv
import os
import threading
import webbrowser
from datetime import datetime
import math
import random
from collections import deque

try:
    import cv2
    from PIL import Image, ImageTk
    VIDEO_PREVIEW_AVAILABLE = True
except ImportError:
    VIDEO_PREVIEW_AVAILABLE = False

# Optional Selenium
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "scraper_config.json")
COLLECTION_FILE = os.path.join(APP_DIR, "collection.json")
UNAVAILABLE_FILE = os.path.join(APP_DIR, "unavailable_videos.json")
VIDEO_MAP_FILE = os.path.join(APP_DIR, "video_maps.json")


class VideoScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("College Video Scraper Pro v2.0")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.colors = {
            "bg": "#0b1120",
            "panel": "#111827",
            "panel_2": "#162033",
            "panel_3": "#0f172a",
            "line": "#263244",
            "text": "#e5edf7",
            "muted": "#8ea3b8",
            "soft": "#bfd7ea",
            "accent": "#38bdf8",
            "accent_2": "#22c55e",
            "warn": "#f59e0b",
            "danger": "#ef4444",
        }
        self.configure(fg_color=self.colors["bg"])
        
        self.base_url = ctk.StringVar(value="https://your-college-server.edu")
        self.prefix = ctk.StringVar(value="7000")
        self.num = ctk.StringVar(value="7115")
        self.delay = ctk.DoubleVar(value=10.0)
        self.default_download_dir = ctk.StringVar(value=os.path.expanduser("~/Downloads/CollegeVideos"))
        self.use_selenium = ctk.BooleanVar(value=False)
        self.chrome_binary = ctk.StringVar(value="/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta")
        self.skip_existing = ctk.BooleanVar(value=True)
        self.smart_skip_missing = ctk.BooleanVar(value=True)
        self.job_use_smart_map = ctk.BooleanVar(value=True)
        self.collection = []
        self.unavailable_urls = set()
        self.video_maps = {}
        self.jobs = {}
        self.job_counter = 0
        self.selected_job_id = None
        self.is_downloading = False
        self.is_mapping = False
        self.saved_headers = DEFAULT_HEADERS.copy()
        self.video_preview_after_id = None
        self.video_preview_token = 0
        self.video_preview_photo = None
        self.video_preview_url = None
        self.last_navigation_delta = 0
        self.job_started_at = None
        self.map_started_at = None
        self.map_stop_requested = False
        
        self.load_config()
        self.load_collection()
        self.load_unavailable_videos()
        self.load_video_maps()
        self._build_ui()
        self.after(100, self.update_full_url)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready • Direct requests mode active",
            text_color=self.colors["accent_2"],
            font=("Inter", 11),
            fg_color=self.colors["panel_3"],
            height=30,
        )
        self.status_label.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        self.toggle_selenium_mode()
        os.makedirs(self.default_download_dir.get(), exist_ok=True)

    def _build_ui(self):
        header = ctk.CTkFrame(self, height=82, fg_color=self.colors["bg"])
        header.pack(fill="x", padx=18, pady=(16, 0))
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        ctk.CTkLabel(
            title_frame,
            text="College Video Scraper Pro",
            font=("Inter", 28, "bold"),
            text_color=self.colors["text"],
        ).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(
            title_frame,
            text="Build URLs, preview targets, collect videos, and run careful range jobs.",
            font=("Inter", 12),
            text_color=self.colors["muted"],
        ).pack(anchor="w", pady=(2, 0))
        
        mode_frame = ctk.CTkFrame(header, fg_color=self.colors["panel"], corner_radius=8, border_width=1, border_color=self.colors["line"])
        mode_frame.pack(side="right", padx=2, pady=16)
        ctk.CTkLabel(mode_frame, text="Mode", font=("Inter", 10), text_color=self.colors["muted"]).pack(side="left", padx=(12, 4))
        self.mode_label = ctk.CTkLabel(mode_frame, text="REQUESTS", 
                                       font=("Inter", 11, "bold"), text_color=self.colors["accent_2"])
        self.mode_label.pack(side="left", padx=(4, 12), pady=8)
        
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color=self.colors["panel"],
            segmented_button_fg_color=self.colors["panel_3"],
            segmented_button_selected_color=self.colors["accent"],
            segmented_button_selected_hover_color="#0ea5e9",
            segmented_button_unselected_color=self.colors["panel_3"],
            segmented_button_unselected_hover_color=self.colors["panel_2"],
            border_width=1,
            border_color=self.colors["line"],
        )
        self.tabview.pack(fill="both", expand=True, padx=18, pady=12)
        
        self.explorer_tab = self.tabview.add("Explorer")
        self._build_explorer_tab()
        self.collection_tab = self.tabview.add("Collection")
        self._build_collection_tab()
        self.jobs_tab = self.tabview.add("Jobs")
        self._build_jobs_tab()
        self.settings_tab = self.tabview.add("Settings")
        self._build_settings_tab()

    def _build_explorer_tab(self):
        left_panel = ctk.CTkFrame(self.explorer_tab, width=430, corner_radius=10, fg_color=self.colors["panel_3"], border_width=1, border_color=self.colors["line"])
        left_panel.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left_panel.pack_propagate(False)
        
        ctk.CTkLabel(left_panel, text="URL Builder", font=("Inter", 16, "bold"), 
                     text_color=self.colors["text"]).pack(pady=(18, 4), padx=18, anchor="w")
        ctk.CTkLabel(left_panel, text="Every edit updates the preview immediately.", font=("Inter", 11), 
                     text_color=self.colors["muted"]).pack(padx=18, anchor="w")
        
        ctk.CTkLabel(left_panel, text="Base URL", font=("Inter", 10), text_color=self.colors["muted"]).pack(padx=18, anchor="w", pady=(18, 0))
        base_entry = ctk.CTkEntry(left_panel, textvariable=self.base_url, font=("Inter", 12), height=40, corner_radius=8, border_color=self.colors["line"], fg_color=self.colors["panel"])
        base_entry.pack(fill="x", padx=18, pady=(4, 14))
        base_entry.bind("<KeyRelease>", lambda e: self.update_full_url())
        
        ctk.CTkLabel(left_panel, text="Folder Prefix", font=("Inter", 10), text_color=self.colors["muted"]).pack(padx=18, anchor="w")
        prefix_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        prefix_frame.pack(fill="x", padx=18, pady=4)
        self.prefix_entry = ctk.CTkEntry(prefix_frame, textvariable=self.prefix, font=("Inter", 18, "bold"), width=124, height=44, justify="center", corner_radius=8, border_color=self.colors["line"], fg_color=self.colors["panel"])
        self.prefix_entry.pack(side="left", padx=(0, 8))
        self.prefix_entry.bind("<KeyRelease>", lambda e: self.update_full_url())
        
        btn_frame1 = ctk.CTkFrame(prefix_frame, fg_color="transparent")
        btn_frame1.pack(side="left")
        for delta, txt in [(-100, "–100"), (-10, "–10"), (-1, "–1"), (1, "+1"), (10, "+10"), (100, "+100")]:
            b = ctk.CTkButton(btn_frame1, text=txt, width=42, height=20, font=("Inter", 9), corner_radius=6,
                              fg_color=self.colors["panel_2"], hover_color=self.colors["line"],
                              command=lambda d=delta: self.change_value(self.prefix, d))
            b.pack(side="left", padx=1, pady=1)
        
        ctk.CTkLabel(left_panel, text="Video Number", font=("Inter", 10), text_color=self.colors["muted"]).pack(padx=18, anchor="w", pady=(14, 0))
        num_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        num_frame.pack(fill="x", padx=18, pady=4)
        self.num_entry = ctk.CTkEntry(num_frame, textvariable=self.num, font=("Inter", 18, "bold"), width=124, height=44, justify="center", corner_radius=8, border_color=self.colors["line"], fg_color=self.colors["panel"])
        self.num_entry.pack(side="left", padx=(0, 8))
        self.num_entry.bind("<KeyRelease>", lambda e: self.update_full_url())
        
        btn_frame2 = ctk.CTkFrame(num_frame, fg_color="transparent")
        btn_frame2.pack(side="left")
        for delta, txt in [(-100, "–100"), (-10, "–10"), (-1, "–1"), (1, "+1"), (10, "+10"), (100, "+100")]:
            b = ctk.CTkButton(btn_frame2, text=txt, width=42, height=20, font=("Inter", 9), corner_radius=6,
                              fg_color=self.colors["panel_2"], hover_color=self.colors["line"],
                              command=lambda d=delta: self.change_value(self.num, d))
            b.pack(side="left", padx=1, pady=1)
        
        ctk.CTkLabel(left_panel, text="Current URL", font=("Inter", 10), text_color=self.colors["muted"]).pack(padx=18, anchor="w", pady=(18, 2))
        self.url_label = ctk.CTkTextbox(left_panel, height=60, font=("JetBrains Mono", 10), corner_radius=8, fg_color=self.colors["panel"], border_width=1, border_color=self.colors["line"], text_color=self.colors["soft"])
        self.url_label.pack(fill="x", padx=18, pady=(0, 8))
        self.url_label.bind("<Button-1>", lambda e: self.copy_url())
        self.preview_state_label = ctk.CTkLabel(left_panel, text="", font=("Inter", 11), text_color=self.colors["muted"])
        self.preview_state_label.pack(fill="x", padx=18, pady=(0, 8), anchor="w")

        skip_cb = ctk.CTkCheckBox(
            left_panel,
            text="Smart skip known missing videos",
            variable=self.smart_skip_missing,
            font=("Inter", 10),
            text_color=self.colors["soft"],
        )
        skip_cb.pack(anchor="w", padx=18, pady=(0, 6))
        
        action_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        action_frame.pack(fill="x", padx=18, pady=10)
        ctk.CTkButton(action_frame, text="Open in Browser", height=42, font=("Inter", 12, "bold"), corner_radius=8,
                      fg_color=self.colors["panel_2"], hover_color=self.colors["line"],
                      command=self.open_in_browser).pack(fill="x", pady=4)
        ctk.CTkButton(action_frame, text="Download This Video", height=48, font=("Inter", 13, "bold"), corner_radius=8, 
                      fg_color=self.colors["accent_2"], hover_color="#16a34a", command=self.download_current).pack(fill="x", pady=4)
        ctk.CTkButton(action_frame, text="Add to Collection", height=42, font=("Inter", 12, "bold"), corner_radius=8, 
                      fg_color=self.colors["accent"], hover_color="#0ea5e9", command=self.add_to_collection).pack(fill="x", pady=4)

        intelligence_frame = ctk.CTkFrame(left_panel, fg_color=self.colors["panel"], corner_radius=8, border_width=1, border_color=self.colors["line"])
        intelligence_frame.pack(fill="x", padx=18, pady=(8, 12))
        ctk.CTkLabel(intelligence_frame, text="Smart Map Intelligence", font=("Inter", 12, "bold"), text_color=self.colors["text"]).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(intelligence_frame, text="Adaptive probing for this folder prefix.", font=("Inter", 10), text_color=self.colors["muted"]).pack(anchor="w", padx=12, pady=(0, 8))

        map_fields = ctk.CTkFrame(intelligence_frame, fg_color="transparent")
        map_fields.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(map_fields, text="Start", font=("Inter", 10), text_color=self.colors["muted"]).pack(side="left")
        self.map_start_entry = ctk.CTkEntry(map_fields, width=70, font=("Inter", 11), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.map_start_entry.insert(0, str(max(0, self.safe_int(self.num.get(), 0) - 500)))
        self.map_start_entry.pack(side="left", padx=(6, 10))
        ctk.CTkLabel(map_fields, text="End", font=("Inter", 10), text_color=self.colors["muted"]).pack(side="left")
        self.map_end_entry = ctk.CTkEntry(map_fields, width=70, font=("Inter", 11), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.map_end_entry.insert(0, str(self.safe_int(self.num.get(), 0) + 500))
        self.map_end_entry.pack(side="left", padx=(6, 10))
        ctk.CTkLabel(map_fields, text="Budget", font=("Inter", 10), text_color=self.colors["muted"]).pack(side="left")
        self.map_budget_entry = ctk.CTkEntry(map_fields, width=70, font=("Inter", 11), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.map_budget_entry.insert(0, "800")
        self.map_budget_entry.pack(side="left", padx=(6, 0))

        map_btns = ctk.CTkFrame(intelligence_frame, fg_color="transparent")
        map_btns.pack(fill="x", padx=12, pady=(0, 10))
        self.smart_map_button = ctk.CTkButton(
            map_btns,
            text="Map Current Prefix",
            height=34,
            font=("Inter", 11, "bold"),
            corner_radius=8,
            fg_color=self.colors["warn"],
            hover_color="#d97706",
            command=self.start_smart_map,
        )
        self.smart_map_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.stop_map_button = ctk.CTkButton(
            map_btns,
            text="Stop",
            width=68,
            height=34,
            font=("Inter", 11),
            corner_radius=8,
            fg_color=self.colors["panel_2"],
            hover_color=self.colors["line"],
            command=self.stop_smart_map,
        )
        self.stop_map_button.pack(side="right")
        self.map_progress = ctk.CTkProgressBar(intelligence_frame, height=10, progress_color=self.colors["warn"])
        self.map_progress.pack(fill="x", padx=12, pady=(0, 6))
        self.map_progress.set(0)
        self.map_status_label = ctk.CTkLabel(intelligence_frame, text="No map running", font=("Inter", 10), text_color=self.colors["muted"], wraplength=360, justify="left")
        self.map_status_label.pack(fill="x", padx=12, pady=(0, 10), anchor="w")
        
        right_panel = ctk.CTkFrame(self.explorer_tab, corner_radius=10, fg_color=self.colors["panel_3"], border_width=1, border_color=self.colors["line"])
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        ctk.CTkLabel(right_panel, text="Live Preview", font=("Inter", 16, "bold"), text_color=self.colors["text"]).pack(pady=(18, 4), padx=18, anchor="w")

        preview_card = ctk.CTkFrame(right_panel, fg_color=self.colors["panel"], corner_radius=10, border_width=1, border_color=self.colors["line"])
        preview_card.pack(fill="x", padx=18, pady=(8, 12))
        self.preview_title = ctk.CTkLabel(preview_card, text="Target video", font=("Inter", 11), text_color=self.colors["muted"])
        self.preview_title.pack(anchor="w", padx=16, pady=(14, 2))
        self.video_shell = ctk.CTkFrame(
            preview_card,
            fg_color=self.colors["panel_3"],
            corner_radius=8,
            height=300,
        )
        self.video_shell.pack(fill="x", padx=16, pady=(0, 12))
        self.video_shell.pack_propagate(False)
        self.video_surface = tk.Label(
            self.video_shell,
            text="Waiting for a valid MP4 URL",
            font=("Inter", 13, "bold"),
            fg=self.colors["muted"],
            bg=self.colors["panel_3"],
            bd=0,
            highlightthickness=0,
            compound="center",
        )
        self.video_surface.pack(fill="both", expand=True, padx=1, pady=1)
        self.preview_url_label = ctk.CTkLabel(preview_card, text="", font=("JetBrains Mono", 13, "bold"), text_color=self.colors["soft"], wraplength=650, justify="left")
        self.preview_url_label.pack(fill="x", padx=16, pady=(0, 10), anchor="w")
        self.preview_meta_label = ctk.CTkLabel(preview_card, text="", font=("Inter", 11), text_color=self.colors["muted"])
        self.preview_meta_label.pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(right_panel, text="Activity Log", font=("Inter", 14, "bold"), text_color=self.colors["text"]).pack(pady=(4, 8), padx=18, anchor="w")
        self.log_text = ctk.CTkTextbox(right_panel, font=("JetBrains Mono", 10), corner_radius=8, fg_color=self.colors["panel"], border_width=1, border_color=self.colors["line"], text_color=self.colors["soft"])
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log("Tool initialized. Ready for scraping.")
        self.log("Tip: Use range jobs for bulk fetching with delays.")

    def _build_collection_tab(self):
        list_frame = ctk.CTkFrame(self.collection_tab, corner_radius=10, fg_color=self.colors["panel_3"], border_width=1, border_color=self.colors["line"])
        list_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        header_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(header_frame, text="Collection", font=("Inter", 16, "bold"), text_color=self.colors["text"]).pack(side="left")
        self.collection_count_label = ctk.CTkLabel(header_frame, text="0 videos", font=("Inter", 11), text_color=self.colors["muted"])
        self.collection_count_label.pack(side="right")
        
        self.collection_listbox = Listbox(list_frame, bg=self.colors["panel"], fg=self.colors["text"], selectbackground=self.colors["accent"], 
                                          selectforeground="white", font=("Inter", 11), height=18, borderwidth=0,
                                          highlightthickness=0, activestyle="none")
        self.collection_listbox.pack(fill="both", expand=True, padx=15, pady=5)
        
        btn_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(btn_frame, text="Remove Selected", width=160, height=38, font=("Inter", 11), corner_radius=8,
                      fg_color=self.colors["danger"], hover_color="#dc2626", command=self.remove_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Clear All", width=140, height=38, font=("Inter", 11), corner_radius=8,
                      fg_color=self.colors["panel_2"], hover_color=self.colors["line"], command=self.clear_collection).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Batch Download", width=200, height=42, font=("Inter", 12, "bold"), corner_radius=8,
                      fg_color=self.colors["accent_2"], hover_color="#16a34a", command=self.start_batch_download).pack(side="right", padx=5)

    def _build_jobs_tab(self):
        jobs_frame = ctk.CTkFrame(self.jobs_tab, corner_radius=10, fg_color=self.colors["panel_3"], border_width=1, border_color=self.colors["line"])
        jobs_frame.pack(fill="both", expand=True, padx=15, pady=15)
        ctk.CTkLabel(jobs_frame, text="Range Job Automation", font=("Inter", 16, "bold"), text_color=self.colors["text"]).pack(pady=(18, 4), padx=20, anchor="w")
        ctk.CTkLabel(jobs_frame, text="Create automated download jobs for number ranges (e.g. 7000–7500). Delays prevent IP bans.", 
                     font=("Inter", 11), text_color=self.colors["muted"], wraplength=720).pack(padx=20, anchor="w")
        
        input_frame = ctk.CTkFrame(jobs_frame, fg_color=self.colors["panel"], corner_radius=10, border_width=1, border_color=self.colors["line"])
        input_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(input_frame, text="Fixed Prefix", font=("Inter", 10), text_color=self.colors["muted"]).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.job_prefix = ctk.CTkEntry(input_frame, width=120, font=("Inter", 12), placeholder_text="7000", fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.job_prefix.insert(0, "7000")
        self.job_prefix.grid(row=0, column=1, padx=10, pady=8)
        
        ctk.CTkLabel(input_frame, text="Start Number", font=("Inter", 10), text_color=self.colors["muted"]).grid(row=0, column=2, padx=15, pady=10, sticky="w")
        self.job_start = ctk.CTkEntry(input_frame, width=100, font=("Inter", 12), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.job_start.insert(0, "7100")
        self.job_start.grid(row=0, column=3, padx=10, pady=8)
        
        ctk.CTkLabel(input_frame, text="End Number", font=("Inter", 10), text_color=self.colors["muted"]).grid(row=0, column=4, padx=15, pady=10, sticky="w")
        self.job_end = ctk.CTkEntry(input_frame, width=100, font=("Inter", 12), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.job_end.insert(0, "7200")
        self.job_end.grid(row=0, column=5, padx=10, pady=8)
        
        ctk.CTkLabel(input_frame, text="Step", font=("Inter", 10), text_color=self.colors["muted"]).grid(row=0, column=6, padx=15, pady=10, sticky="w")
        self.job_step = ctk.CTkEntry(input_frame, width=60, font=("Inter", 12), fg_color=self.colors["panel_3"], border_color=self.colors["line"])
        self.job_step.insert(0, "1")
        self.job_step.grid(row=0, column=7, padx=10, pady=8)

        for entry in (self.job_prefix, self.job_start, self.job_end, self.job_step):
            entry.bind("<KeyRelease>", lambda e: self.update_job_preview())

        self.job_smart_map_cb = ctk.CTkCheckBox(
            jobs_frame,
            text="Use Smart Map Intelligence before downloading",
            variable=self.job_use_smart_map,
            font=("Inter", 11),
            text_color=self.colors["soft"],
        )
        self.job_smart_map_cb.pack(anchor="w", padx=22, pady=(0, 4))
        
        job_btn_frame = ctk.CTkFrame(jobs_frame, fg_color="transparent")
        job_btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(job_btn_frame, text="Refresh Preview", height=40, font=("Inter", 11), corner_radius=8,
                      fg_color=self.colors["panel_2"], hover_color=self.colors["line"],
                      command=self.preview_job).pack(side="left", padx=5)
        ctk.CTkButton(job_btn_frame, text="Start Range Download", height=42, font=("Inter", 12, "bold"), corner_radius=8,
                      fg_color=self.colors["warn"], hover_color="#d97706", command=self.start_range_job).pack(side="left", padx=10)
        ctk.CTkButton(job_btn_frame, text="Stop Selected", height=40, font=("Inter", 11), corner_radius=8,
                      fg_color=self.colors["danger"], hover_color="#dc2626",
                      command=self.stop_selected_job).pack(side="right", padx=5)
        ctk.CTkButton(job_btn_frame, text="Stop All", height=40, font=("Inter", 11), corner_radius=8,
                      fg_color=self.colors["panel_2"], hover_color=self.colors["line"],
                      command=self.stop_all_jobs).pack(side="right", padx=5)

        progress_frame = ctk.CTkFrame(jobs_frame, fg_color=self.colors["panel"], corner_radius=10, border_width=1, border_color=self.colors["line"])
        progress_frame.pack(fill="x", padx=20, pady=(4, 10))
        self.job_progress = ctk.CTkProgressBar(progress_frame, height=12, progress_color=self.colors["accent_2"])
        self.job_progress.pack(fill="x", padx=16, pady=(16, 8))
        self.job_progress.set(0)
        self.job_progress_label = ctk.CTkLabel(progress_frame, text="No active job", font=("Inter", 12, "bold"), text_color=self.colors["text"])
        self.job_progress_label.pack(anchor="w", padx=16, pady=(0, 2))
        self.job_detail_label = ctk.CTkLabel(progress_frame, text="Preview a range, then start a job to see live progress here.", font=("Inter", 11), text_color=self.colors["muted"])
        self.job_detail_label.pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(jobs_frame, text="Job Queue", font=("Inter", 13, "bold"), text_color=self.colors["text"]).pack(anchor="w", padx=20, pady=(0, 6))
        self.jobs_listbox = Listbox(
            jobs_frame,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="white",
            font=("Inter", 10),
            height=5,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
        )
        self.jobs_listbox.pack(fill="x", padx=20, pady=(0, 10))
        self.jobs_listbox.bind("<<ListboxSelect>>", lambda e: self.on_job_selected())
        
        self.job_log = ctk.CTkTextbox(jobs_frame, height=200, font=("JetBrains Mono", 10), corner_radius=8, fg_color=self.colors["panel"], border_width=1, border_color=self.colors["line"], text_color=self.colors["soft"])
        self.job_log.pack(fill="both", expand=True, padx=20, pady=15)
        self.update_job_preview()

    def _build_settings_tab(self):
        settings_frame = ctk.CTkFrame(self.settings_tab, corner_radius=10, fg_color=self.colors["panel_3"], border_width=1, border_color=self.colors["line"])
        settings_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        left = ctk.CTkFrame(settings_frame, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(left, text="Download Behavior", font=("Inter", 14, "bold"), text_color=self.colors["text"]).pack(anchor="w", pady=10, padx=10)
        
        delay_frame = ctk.CTkFrame(left, fg_color=self.colors["panel"], corner_radius=8, border_width=1, border_color=self.colors["line"])
        delay_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(delay_frame, text="Delay between downloads (seconds)", font=("Inter", 10), text_color=self.colors["muted"]).pack(anchor="w", padx=12, pady=6)
        delay_slider = ctk.CTkSlider(delay_frame, from_=2, to=20, number_of_steps=10, variable=self.delay, 
                                     command=lambda v: self.delay_label.configure(text=f"{float(v):.0f}s"))
        delay_slider.pack(fill="x", padx=12, pady=2)
        self.delay_label = ctk.CTkLabel(delay_frame, text=f"{float(self.delay.get()):.0f}s", font=("Inter", 11, "bold"), text_color=self.colors["soft"])
        self.delay_label.pack(anchor="e", padx=12, pady=2)
        
        skip_cb = ctk.CTkCheckBox(left, text="Skip already downloaded files (by filename)", variable=self.skip_existing, font=("Inter", 10))
        skip_cb.pack(anchor="w", padx=10, pady=8)
        
        ctk.CTkLabel(left, text="Default Download Folder", font=("Inter", 10), text_color=self.colors["muted"]).pack(anchor="w", padx=10, pady=(10, 2))
        folder_frame = ctk.CTkFrame(left, fg_color="transparent")
        folder_frame.pack(fill="x", padx=10)
        ctk.CTkEntry(folder_frame, textvariable=self.default_download_dir, font=("Inter", 10), fg_color=self.colors["panel"], border_color=self.colors["line"]).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(folder_frame, text="Browse", width=70, height=30, corner_radius=8, fg_color=self.colors["panel_2"], hover_color=self.colors["line"], command=self.choose_default_folder).pack(side="right")
        
        right = ctk.CTkFrame(settings_frame, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=10)
        
        ctk.CTkLabel(right, text="Selenium Automation", font=("Inter", 14, "bold"), text_color=self.colors["text"]).pack(anchor="w", pady=10, padx=10)
        
        selenium_cb = ctk.CTkCheckBox(right, text="Use Selenium (real browser clicks) when requests fail", 
                                      variable=self.use_selenium, font=("Inter", 10), command=self.toggle_selenium_mode)
        selenium_cb.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(right, text="Chrome Beta Path (for Selenium)", font=("Inter", 10), text_color=self.colors["muted"]).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkEntry(right, textvariable=self.chrome_binary, font=("Inter", 9), fg_color=self.colors["panel"], border_color=self.colors["line"]).pack(fill="x", padx=10)
        
        if not SELENIUM_AVAILABLE:
            ctk.CTkLabel(right, text="⚠️ Selenium not installed. Run: pip install selenium webdriver-manager", 
                         font=("Inter", 9), text_color=self.colors["warn"]).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(right, text="Custom Headers (JSON)", font=("Inter", 10), text_color=self.colors["muted"]).pack(anchor="w", padx=10, pady=(15, 2))
        self.headers_text = ctk.CTkTextbox(right, height=120, font=("JetBrains Mono", 9), fg_color=self.colors["panel"], border_width=1, border_color=self.colors["line"], text_color=self.colors["soft"])
        self.headers_text.pack(fill="x", padx=10, pady=5)
        self.headers_text.insert("1.0", json.dumps(self.saved_headers, indent=2))
        
        ctk.CTkButton(settings_frame, text="Save All Settings", height=40, font=("Inter", 12, "bold"), corner_radius=8,
                      fg_color=self.colors["accent"], hover_color="#0ea5e9", command=self.save_config).pack(pady=15, padx=20, fill="x")

    def toggle_selenium_mode(self):
        if self.use_selenium.get():
            self.mode_label.configure(text="SELENIUM", text_color=self.colors["warn"])
            self.status_label.configure(text="Selenium mode enabled • Will use real browser for downloads", text_color=self.colors["warn"])
        else:
            self.mode_label.configure(text="REQUESTS", text_color=self.colors["accent_2"])
            self.status_label.configure(text="Ready • Direct requests mode active", text_color=self.colors["accent_2"])

    def change_value(self, var, delta):
        current = self.safe_int(var.get(), 0)
        new_val = max(0, current + delta)
        self.last_navigation_delta = delta if var is self.num else 0
        if self.smart_skip_missing.get():
            new_val = self.next_known_available_value(var, new_val, delta)
        var.set(str(new_val))
        self.update_full_url()

    def next_known_available_value(self, var, candidate, delta):
        if delta == 0:
            return candidate

        step = 1 if delta > 0 else -1
        value = max(0, candidate)
        for _ in range(200):
            if var is self.num:
                url = self.build_url_for(num=value)
            else:
                url = self.build_url_for(prefix=value)
            if not url or url not in self.unavailable_urls:
                return value
            value = max(0, value + step)
            if value == 0 and step < 0:
                return value
        return candidate

    def safe_int(self, value, default=None):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def current_parts(self):
        base = self.base_url.get().strip().rstrip("/")
        prefix = self.safe_int(self.prefix.get())
        num = self.safe_int(self.num.get())
        if not base or prefix is None or num is None:
            return base, prefix, num, None
        return base, prefix, num, f"{base}/{prefix}/{num}.mp4"

    def build_url_for(self, prefix=None, num=None):
        base = self.base_url.get().strip().rstrip("/")
        prefix = self.safe_int(self.prefix.get()) if prefix is None else prefix
        num = self.safe_int(self.num.get()) if num is None else num
        if not base or prefix is None or num is None:
            return None
        return f"{base}/{prefix}/{num}.mp4"

    def update_full_url(self):
        base, prefix, num, full = self.current_parts()
        if full is None:
            full = "Complete the base URL, folder prefix, and video number to preview the MP4 URL."
            state = "Preview waiting for valid numeric values."
            color = self.colors["warn"]
            meta = "Filename: pending"
        else:
            state = "Live preview ready. Click the URL box to copy it."
            color = self.colors["accent_2"]
            meta = f"Filename: {prefix}_{num}.mp4 • Mode: {self.mode_label.cget('text') if hasattr(self, 'mode_label') else 'REQUESTS'}"
        self.url_label.delete("1.0", "end")
        self.url_label.insert("1.0", full)
        if hasattr(self, "preview_url_label"):
            self.preview_url_label.configure(text=full)
            self.preview_meta_label.configure(text=meta)
            self.preview_state_label.configure(text=state, text_color=color)
            if full.startswith(("http://", "https://")):
                self.schedule_video_preview(full)
            else:
                self.stop_video_preview("Waiting for a valid MP4 URL")

    def schedule_video_preview(self, url):
        if self.video_preview_after_id is not None:
            self.after_cancel(self.video_preview_after_id)
            self.video_preview_after_id = None

        if url == self.video_preview_url:
            return

        self.video_preview_token += 1
        token = self.video_preview_token

        if hasattr(self, "headers_text"):
            try:
                self.saved_headers = json.loads(self.headers_text.get("1.0", "end").strip() or "{}")
            except json.JSONDecodeError:
                pass

        if not VIDEO_PREVIEW_AVAILABLE:
            self.video_surface.configure(
                image="",
                text="Video preview needs opencv-python and pillow installed.",
                fg=self.colors["warn"],
            )
            return

        if url in self.unavailable_urls:
            self.video_preview_url = None
            self.video_surface.configure(image="", text="Known missing video from the saved map.", fg=self.colors["warn"])
            self.video_surface.image = None
            return

        self.video_preview_after_id = self.after(90, lambda: self.start_video_preview(url, token))

    def stop_video_preview(self, message=None):
        self.video_preview_token += 1
        self.video_preview_url = None
        self.video_preview_photo = None
        if self.video_preview_after_id is not None:
            self.after_cancel(self.video_preview_after_id)
            self.video_preview_after_id = None
        if hasattr(self, "video_surface"):
            self.video_surface.configure(
                image="",
                text=message or "Video preview stopped",
                fg=self.colors["muted"],
            )
            self.video_surface.image = None

    def start_video_preview(self, url, token=None):
        self.video_preview_after_id = None
        if url == self.video_preview_url:
            return

        if token is None:
            self.video_preview_token += 1
            token = self.video_preview_token
        elif token != self.video_preview_token:
            return

        self.video_preview_url = url
        self.video_surface.configure(image="", text="Checking video availability...", fg=self.colors["muted"])
        self.video_surface.image = None
        threading.Thread(target=self._video_preview_worker, args=(url, token), daemon=True).start()

    def _video_preview_worker(self, url, token):
        available, reason = self.check_video_available(url)
        if token != self.video_preview_token:
            return
        if not available:
            self.after(0, lambda: self.mark_video_unavailable(url, token, reason))
            return

        self.after(0, lambda: self._show_video_loading(token))
        cap = cv2.VideoCapture(url)
        if token != self.video_preview_token:
            cap.release()
            return
        if not cap.isOpened():
            self.after(0, lambda: self.mark_video_unavailable(url, token, "OpenCV could not read the stream"))
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_delay = 1 / fps if fps and fps > 1 else 1 / 24
        frame_delay = max(0.04, min(frame_delay, 0.08))
        last_frame_at = 0

        while token == self.video_preview_token:
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
                if not ok:
                    break

            now = time.time()
            if now - last_frame_at < frame_delay:
                time.sleep(frame_delay / 2)
                continue
            last_frame_at = now
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.after(0, lambda f=frame, t=token: self._show_video_frame(f, t))
            time.sleep(frame_delay)

        cap.release()

    def check_video_available(self, url):
        headers = DEFAULT_HEADERS.copy()
        headers.update(self.saved_headers)
        headers["Range"] = "bytes=0-2047"

        try:
            with requests.get(url, headers=headers, stream=True, timeout=(0.8, 1.8), allow_redirects=True) as response:
                status = response.status_code
                content_type = response.headers.get("Content-Type", "").lower()
                content_length = response.headers.get("Content-Length")
                response.close()

            if status in (200, 206):
                if "video" in content_type or "octet-stream" in content_type or content_type == "":
                    return True, f"HTTP {status}"
                if any(kind in content_type for kind in ("text/html", "application/json", "text/plain", "xml")):
                    return False, f"Unexpected content type: {content_type}"
                if content_length and int(content_length) > 0:
                    return True, f"HTTP {status}"
                return False, f"Unexpected content type: {content_type or 'unknown'}"
            return False, f"HTTP {status}"
        except Exception as e:
            return False, str(e)[:90]

    def start_smart_map(self):
        if self.is_mapping:
            messagebox.showinfo("Smart Map", "A smart map is already running.")
            return

        base, prefix, current, url = self.current_parts()
        if url is None or prefix is None or current is None:
            messagebox.showwarning("Smart Map", "Enter a valid base URL, folder prefix, and current video number first.")
            return

        try:
            start = int(self.map_start_entry.get())
            end = int(self.map_end_entry.get())
            budget = int(self.map_budget_entry.get())
        except ValueError:
            messagebox.showerror("Smart Map", "Start, end, and budget must be valid numbers.")
            return

        if budget <= 0 or start < 0 or end < 0:
            messagebox.showerror("Smart Map", "Budget must be greater than 0 and start/end must be non-negative.")
            return

        if start > end:
            messagebox.showerror("Smart Map", "Start must be less than or equal to end.")
            return

        center = min(max(current, start), end)
        self.is_mapping = True
        self.map_stop_requested = False
        self.map_started_at = time.time()
        self.smart_map_button.configure(state="disabled", text="Mapping...")
        self.update_map_progress_ui(0, min(budget, end - start + 1), f"Starting adaptive map for prefix {prefix}: {start}-{end}", self.colors["warn"])
        self.log(f"Smart map started for prefix {prefix}: start={start}, end={end}, budget={budget}, center={center}")
        self.log("Mapper strategy: scored frontier search with local refinement around hits and boundary uncertainty.")
        threading.Thread(target=self._smart_map_worker, args=(base, prefix, start, end, center, budget), daemon=True).start()

    def stop_smart_map(self):
        if self.is_mapping:
            self.map_stop_requested = True
            self.is_mapping = False
            self.update_map_progress_ui(0, 1, "Stopping smart map after the current probe finishes...", self.colors["warn"])
            self.log("Smart map stop requested.")

    def _smart_map_worker(self, base, prefix, start, end, center, budget):
        low = max(0, start)
        high = max(low, end)
        key = self.map_key(base, prefix)
        stored = self.video_maps.get(key, {})
        tested = {}

        for n in stored.get("available", []):
            if low <= int(n) <= high:
                tested[int(n)] = True
        for n in stored.get("missing", []):
            if low <= int(n) <= high:
                tested[int(n)] = False

        for n in self.cached_missing_numbers_for_prefix(base, prefix):
            if low <= n <= high and n not in tested:
                tested[n] = False

        probes = 0
        found_before = sum(1 for ok in tested.values() if ok)
        cached_count = len(tested)
        rng = random.Random(f"{base}|{prefix}|{center}|{time.time()}")
        self.log(f"Smart map loaded {cached_count} cached probes in [{low}, {high}], with {found_before} known hits.")

        while self.is_mapping and probes < budget:
            candidate, reason, score = self.select_smart_candidate(tested, low, high, center, rng, probes, budget)
            if candidate is None:
                self.log("Smart map stopped: no untested candidates left in the search window.")
                break

            url = self.url_for(base, prefix, candidate)
            self.update_map_progress_ui(
                probes,
                budget,
                f"Probe {probes + 1}/{budget}: {candidate} • {reason} • score {score:.3f}",
                self.colors["warn"],
            )
            self.log(f"Smart map probe {probes + 1}/{budget}: {candidate} ({reason}, score={score:.3f})")
            available, check_reason = self.check_video_available(url)
            probes += 1
            tested[candidate] = available

            if available:
                self.unavailable_urls.discard(url)
                self.log(f"Smart map HIT: {prefix}/{candidate}.mp4 ({check_reason})")
            else:
                self.unavailable_urls.add(url)
                self.log(f"Smart map miss: {prefix}/{candidate}.mp4 ({check_reason})")

            if probes % max(1, int(math.sqrt(max(1, budget)))) == 0:
                self.persist_smart_map(base, prefix, center, low, high, tested, probes, partial=True)

        stopped = self.map_stop_requested
        self.is_mapping = False
        self.persist_smart_map(base, prefix, center, low, high, tested, probes, partial=False)
        self.save_unavailable_videos()
        elapsed = self.format_duration(time.time() - self.map_started_at) if self.map_started_at else "0s"
        available_numbers = sorted(n for n, ok in tested.items() if ok)
        missing_numbers = sorted(n for n, ok in tested.items() if not ok)
        self.after(0, lambda: self.smart_map_button.configure(state="normal", text="Map Current Prefix"))
        self.update_map_progress_ui(
            probes,
            max(1, budget),
            f"Map {'stopped' if stopped else 'finished'}: {len(available_numbers)} hits, {len(missing_numbers)} missing, {probes} new probes • {elapsed}",
            self.colors["warn"] if stopped else self.colors["accent_2"],
        )
        self.log(f"Smart map {'stopped' if stopped else 'finished'} for prefix {prefix}: hits={len(available_numbers)}, missing={len(missing_numbers)}, new_probes={probes}, elapsed={elapsed}")
        self.log(f"Saved map JSON: {VIDEO_MAP_FILE}")
        self.log(f"Saved map CSV: {self.map_csv_path(base, prefix)}")

    def run_range_smart_map_preflight(self, job_id, base, prefix, start, end, budget):
        low = max(0, start)
        high = max(low, end)
        center = (low + high) // 2
        key = self.map_key(base, prefix)
        stored = self.video_maps.get(key, {})
        tested = {}

        for n in stored.get("available", []):
            if low <= int(n) <= high:
                tested[int(n)] = True
        for n in stored.get("missing", []):
            if low <= int(n) <= high:
                tested[int(n)] = False
        for n in self.cached_missing_numbers_for_prefix(base, prefix):
            if low <= n <= high and n not in tested:
                tested[n] = False

        probes = 0
        rng = random.Random(f"job|{base}|{prefix}|{start}|{end}|{time.time()}")
        cached_hits = sum(1 for ok in tested.values() if ok)
        cached_missing = sum(1 for ok in tested.values() if not ok)
        self.log(f"Smart Map preflight cache: {cached_hits} hits, {cached_missing} missing already known.", self.job_log)

        while self.job_should_continue(job_id) and probes < budget:
            candidate, reason, score = self.select_smart_candidate(tested, low, high, center, rng, probes, budget)
            if candidate is None:
                self.log("Smart Map preflight covered every value in the requested interval.", self.job_log)
                break

            url = self.url_for(base, prefix, candidate)
            self.update_managed_job(job_id, current=probes, total=budget, status="mapping", phase=f"smart map probe {candidate}", detail=f"Preflight {probes + 1}/{budget} • {reason} • score {score:.3f}")
            self.log(f"Smart Map preflight probe {probes + 1}/{budget}: {prefix}/{candidate}.mp4 ({reason}, score={score:.3f})", self.job_log)
            available, check_reason = self.check_video_available(url)
            probes += 1
            tested[candidate] = available

            if available:
                self.unavailable_urls.discard(url)
                self.log(f"Smart Map preflight HIT: {prefix}/{candidate}.mp4 ({check_reason})", self.job_log)
            else:
                self.unavailable_urls.add(url)
                self.log(f"Smart Map preflight miss: {prefix}/{candidate}.mp4 ({check_reason})", self.job_log)

            if probes % max(1, int(math.sqrt(max(1, budget)))) == 0:
                self.persist_smart_map(base, prefix, center, low, high, tested, probes, partial=True)
                self.save_unavailable_videos()

        self.persist_smart_map(base, prefix, center, low, high, tested, probes, partial=not self.job_should_continue(job_id))
        self.save_unavailable_videos()
        return tested

    def select_smart_candidate(self, tested, low, high, center, rng, generation, budget):
        untested_count = (high - low + 1) - len(tested)
        if untested_count <= 0:
            return None, "complete", 0

        if not tested:
            return center, "seed at current video number", 1.0

        candidates = set()
        tested_numbers = sorted(tested)
        hits = sorted(n for n, ok in tested.items() if ok)
        misses = sorted(n for n, ok in tested.items() if not ok)

        def add(n):
            if low <= n <= high and n not in tested:
                candidates.add(n)

        add(center)
        for n in tested_numbers:
            left_gap = self.distance_to_previous_tested(n, tested_numbers, low)
            right_gap = self.distance_to_next_tested(n, tested_numbers, high)
            local_scale = max(1, round(math.sqrt(max(left_gap, right_gap, 1))))
            add(n - local_scale)
            add(n + local_scale)
            add(n - max(1, local_scale // 2))
            add(n + max(1, local_scale // 2))

        for hit in hits:
            add(hit - 1)
            add(hit + 1)
            nearest_gap = self.nearest_untested_gap(hit, tested, low, high)
            if nearest_gap:
                gap_low, gap_high = nearest_gap
                add((gap_low + gap_high) // 2)
                add(gap_low)
                add(gap_high)

        for left, right in zip(tested_numbers, tested_numbers[1:]):
            if right - left > 1:
                gap_low = left + 1
                gap_high = right - 1
                span = gap_high - gap_low + 1
                midpoint = (gap_low + gap_high) // 2
                add(midpoint)
                if tested[left] != tested[right]:
                    add(gap_low)
                    add(gap_high)
                else:
                    offset = max(1, round(math.sqrt(span)))
                    add(midpoint - offset)
                    add(midpoint + offset)

        first = tested_numbers[0]
        if first > low:
            add((low + first - 1) // 2)
            add(first - max(1, round(math.sqrt(first - low))))
        last = tested_numbers[-1]
        if last < high:
            add((last + 1 + high) // 2)
            add(last + max(1, round(math.sqrt(high - last))))

        population = max(12, round(math.sqrt(max(1, budget)) * 2))
        spread = max(1, high - low)
        for _ in range(population):
            if hits and rng.random() < 0.55:
                anchor = rng.choice(hits)
                nearest = max(1, self.nearest_tested_distance(anchor, tested_numbers, spread))
                mutation = max(1, round(abs(rng.gauss(0, math.sqrt(nearest)))))
                add(anchor + rng.choice([-1, 1]) * mutation)
            else:
                anchor = center if rng.random() < 0.5 else rng.randint(low, high)
                mutation = max(1, round(abs(rng.gauss(0, math.sqrt(spread)))))
                add(max(low, min(high, anchor + rng.choice([-1, 1]) * mutation)))

        if not candidates:
            for n in range(low, high + 1):
                if n not in tested:
                    return n, "fallback lowest untested", 0

        best = None
        best_score = -1
        best_reason = ""
        for candidate in candidates:
            score, reason = self.smart_candidate_score(candidate, tested, low, high, center, rng)
            if score > best_score:
                best = candidate
                best_score = score
                best_reason = reason
        return best, best_reason, best_score

    def smart_candidate_score(self, candidate, tested, low, high, center, rng):
        tested_numbers = sorted(tested)
        hits = [n for n, ok in tested.items() if ok]
        radius = max(1, high - low)
        nearest_tested = min(abs(candidate - n) for n in tested_numbers) if tested_numbers else radius
        novelty = min(1, nearest_tested / max(1, math.sqrt(radius)))
        locality = math.exp(-abs(candidate - center) / max(1, radius / 3))

        if hits:
            nearest_hit = min(abs(candidate - n) for n in hits)
            hit_refinement = 1 / (1 + nearest_hit)
        else:
            hit_refinement = 0

        boundary = 0
        left = max((n for n in tested_numbers if n < candidate), default=None)
        right = min((n for n in tested_numbers if n > candidate), default=None)
        if left is not None and right is not None and tested[left] != tested[right]:
            boundary = 1 / max(1, right - left)

        untested_interval = self.untested_interval_size(candidate, tested, low, high)
        uncertainty = min(1, math.log1p(untested_interval) / math.log1p(radius))
        exploration_weight = 0.35 + 0.25 * (1 - min(1, len(hits) / max(1, len(tested))))
        refinement_weight = 0.45 if hits else 0.15
        score = (
            exploration_weight * uncertainty
            + 0.25 * novelty
            + refinement_weight * hit_refinement
            + 0.25 * boundary
            + 0.15 * locality
            + rng.random() * 0.03
        )

        if boundary:
            reason = "boundary refinement"
        elif hit_refinement:
            reason = "local refinement near live hit"
        elif uncertainty > novelty:
            reason = "uncertain interval exploration"
        else:
            reason = "novel candidate mutation"
        return score, reason

    def distance_to_previous_tested(self, value, tested_numbers, low):
        previous = max((n for n in tested_numbers if n < value), default=low - 1)
        return value - previous

    def distance_to_next_tested(self, value, tested_numbers, high):
        next_value = min((n for n in tested_numbers if n > value), default=high + 1)
        return next_value - value

    def nearest_tested_distance(self, value, tested_numbers, fallback):
        others = [abs(value - n) for n in tested_numbers if n != value]
        return min(others) if others else fallback

    def nearest_untested_gap(self, value, tested, low, high):
        best = None
        best_distance = None
        start = None
        for n in range(low, high + 1):
            if n not in tested and start is None:
                start = n
            if (n in tested or n == high) and start is not None:
                end = n - 1 if n in tested else n
                distance = 0 if start <= value <= end else min(abs(value - start), abs(value - end))
                if best_distance is None or distance < best_distance:
                    best = (start, end)
                    best_distance = distance
                start = None
        return best

    def untested_interval_size(self, candidate, tested, low, high):
        left = candidate
        while left - 1 >= low and left - 1 not in tested:
            left -= 1
        right = candidate
        while right + 1 <= high and right + 1 not in tested:
            right += 1
        return right - left + 1

    def map_key(self, base, prefix):
        return f"{base.rstrip('/')}|{prefix}"

    def url_for(self, base, prefix, num):
        return f"{base.rstrip('/')}/{prefix}/{num}.mp4"

    def cached_missing_numbers_for_prefix(self, base, prefix):
        prefix_path = f"{base.rstrip('/')}/{prefix}/"
        nums = []
        for url in self.unavailable_urls:
            if url.startswith(prefix_path) and url.endswith(".mp4"):
                try:
                    nums.append(int(os.path.basename(url)[:-4]))
                except ValueError:
                    pass
        return nums

    def persist_smart_map(self, base, prefix, center, start, end, tested, probes, partial=False):
        key = self.map_key(base, prefix)
        existing = self.video_maps.get(key, {})
        available = set(int(n) for n in existing.get("available", []))
        missing = set(int(n) for n in existing.get("missing", []))

        for n, ok in tested.items():
            if ok:
                available.add(int(n))
                missing.discard(int(n))
            else:
                missing.add(int(n))
                available.discard(int(n))

        self.video_maps[key] = {
            "base_url": base.rstrip("/"),
            "prefix": int(prefix),
            "available": sorted(available),
            "missing": sorted(missing),
            "last_center": int(center),
            "last_start": int(start),
            "last_end": int(end),
            "last_probe_count": int(probes),
            "updated_at": datetime.now().isoformat(),
            "partial": partial,
        }
        self.save_video_maps()
        self.export_map_csv(base, prefix)

    def map_csv_path(self, base, prefix):
        safe_base = "".join(ch if ch.isalnum() else "_" for ch in base.rstrip("/"))[-60:]
        return os.path.join(APP_DIR, f"video_map_{safe_base}_{prefix}.csv")

    def export_map_csv(self, base, prefix):
        key = self.map_key(base, prefix)
        data = self.video_maps.get(key, {})
        path = self.map_csv_path(base, prefix)
        rows = []
        for n in data.get("available", []):
            rows.append((int(n), "available", self.url_for(base, prefix, int(n))))
        for n in data.get("missing", []):
            rows.append((int(n), "missing", self.url_for(base, prefix, int(n))))
        rows.sort(key=lambda row: row[0])
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["video_number", "status", "url"])
            writer.writerows(rows)

    def _show_video_loading(self, token):
        if token != self.video_preview_token:
            return
        self.video_surface.configure(image="", text="Loading video preview...", fg=self.colors["muted"])
        self.video_surface.image = None

    def mark_video_unavailable(self, url, token, reason):
        if token != self.video_preview_token:
            return
        self.unavailable_urls.add(url)
        self.save_unavailable_videos()
        self.video_preview_url = None
        self.video_surface.configure(image="", text=f"No playable MP4 found here. {reason}", fg=self.colors["warn"])
        self.video_surface.image = None
        self.preview_state_label.configure(text=f"Marked missing and cached: {url.rsplit('/', 1)[-1]}", text_color=self.colors["warn"])
        self.log(f"Marked missing: {url} ({reason})")

    def smart_jump_from_missing(self, url, delta, token):
        if token != self.video_preview_token or not self.smart_skip_missing.get():
            return
        _, prefix, num, current_url = self.current_parts()
        if current_url != url or num is None:
            return

        step = 1 if delta > 0 else -1
        next_num = max(0, num + step)
        next_num = self.next_known_available_value(self.num, next_num, step)
        if next_num != num:
            self.num.set(str(next_num))
            self.last_navigation_delta = step
            self.update_full_url()

    def _show_video_frame(self, frame, token):
        if token != self.video_preview_token:
            return

        width = max(320, self.video_surface.winfo_width() - 12)
        height = max(180, self.video_surface.winfo_height() - 12)
        source_h, source_w = frame.shape[:2]
        scale = min(width / source_w, height / source_h)
        target_w = max(1, int(source_w * scale))
        target_h = max(1, int(source_h * scale))

        image = Image.fromarray(frame).resize((target_w, target_h), Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(image, master=self.video_surface)
        self.video_preview_photo = photo
        self.video_surface.image = photo
        try:
            self.video_surface.configure(image=photo, text="")
        except tk.TclError:
            self.stop_video_preview("Video preview reset.")

    def _show_video_error(self, token, message):
        if token != self.video_preview_token:
            return
        self.video_surface.configure(image="", text=message, fg=self.colors["warn"])
        self.video_surface.image = None

    def copy_url(self):
        url = self.url_label.get("1.0", "end").strip()
        if not url.startswith(("http://", "https://")):
            self.log("Preview is incomplete; nothing copied.")
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.log("URL copied to clipboard")

    def get_current_url(self):
        _, _, _, url = self.current_parts()
        if url is None:
            raise ValueError("Enter a valid base URL, folder prefix, and video number first.")
        return url

    def get_filename(self):
        _, prefix, num, url = self.current_parts()
        if url is None:
            raise ValueError("Enter valid numeric values before creating a filename.")
        return f"{prefix}_{num}.mp4"

    def log(self, msg, target=None):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self.log(msg, target))
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}\n"
        if target is None:
            target = self.log_text
        target.insert("end", full_msg)
        target.see("end")

    def format_duration(self, seconds):
        seconds = max(0, int(seconds))
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    def update_job_progress_ui(self, current, total, title, detail, color=None):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self.update_job_progress_ui(current, total, title, detail, color))
            return

        progress = 0 if total <= 0 else min(1, max(0, current / total))
        self.job_progress.set(progress)
        self.job_progress_label.configure(text=title, text_color=color or self.colors["text"])
        self.job_detail_label.configure(text=detail)

    def create_range_job_record(self, prefix, start, end, step, save_dir, use_smart_map):
        self.job_counter += 1
        job_id = f"job-{self.job_counter}"
        name = f"{prefix}: {start}-{end} step {step}"
        self.jobs[job_id] = {
            "id": job_id,
            "name": name,
            "type": "range",
            "prefix": prefix,
            "start": start,
            "end": end,
            "step": step,
            "save_dir": save_dir,
            "use_smart_map": use_smart_map,
            "status": "queued",
            "phase": "queued",
            "current": 0,
            "total": len(range(start, end + 1, step)),
            "detail": f"Queued • saving to {save_dir}",
            "stop": False,
            "started_at": None,
            "finished_at": None,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.selected_job_id = job_id
        self.refresh_jobs_list()
        self.show_job(job_id)
        return job_id

    def refresh_jobs_list(self):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self.refresh_jobs_list)
            return
        if not hasattr(self, "jobs_listbox"):
            return
        current_selection = self.selected_job_id
        self.jobs_listbox.delete(0, END)
        ordered = list(self.jobs.values())
        ordered.sort(key=lambda job: int(job["id"].split("-")[-1]), reverse=True)
        self._jobs_list_order = [job["id"] for job in ordered]
        for job in ordered:
            pct = 0 if job["total"] <= 0 else int((job["current"] / job["total"]) * 100)
            self.jobs_listbox.insert(END, f"{job['id']} • {job['status'].upper()} • {pct}% • {job['name']} • {job['phase']}")
        if current_selection in self._jobs_list_order:
            idx = self._jobs_list_order.index(current_selection)
            self.jobs_listbox.selection_set(idx)

    def on_job_selected(self):
        selection = self.jobs_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(getattr(self, "_jobs_list_order", [])):
            return
        self.selected_job_id = self._jobs_list_order[idx]
        self.show_job(self.selected_job_id)

    def show_job(self, job_id):
        job = self.jobs.get(job_id)
        if not job:
            return
        self.update_job_progress_ui(
            job["current"],
            max(1, job["total"]),
            f"{job['id']} • {job['status'].title()} • {job['phase']}",
            job["detail"],
            self.job_status_color(job["status"]),
        )

    def job_status_color(self, status):
        return {
            "queued": self.colors["muted"],
            "running": self.colors["accent"],
            "mapping": self.colors["warn"],
            "waiting": self.colors["warn"],
            "stopping": self.colors["warn"],
            "stopped": self.colors["danger"],
            "complete": self.colors["accent_2"],
            "failed": self.colors["danger"],
        }.get(status, self.colors["text"])

    def update_managed_job(self, job_id, current=None, total=None, status=None, phase=None, detail=None, **stats):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self.update_managed_job(job_id, current, total, status, phase, detail, **stats))
            return
        job = self.jobs.get(job_id)
        if not job:
            return
        if current is not None:
            job["current"] = current
        if total is not None:
            job["total"] = total
        if status is not None:
            job["status"] = status
        if phase is not None:
            job["phase"] = phase
        if detail is not None:
            job["detail"] = detail
        for key, value in stats.items():
            if key in job:
                job[key] = value
        self.refresh_jobs_list()
        if self.selected_job_id in (None, job_id):
            self.selected_job_id = job_id
            self.show_job(job_id)

    def job_should_continue(self, job_id):
        job = self.jobs.get(job_id)
        return bool(job and not job.get("stop"))

    def stop_selected_job(self):
        job_id = self.selected_job_id
        if not job_id or job_id not in self.jobs:
            messagebox.showinfo("Jobs", "Select a running job first.")
            return
        self.jobs[job_id]["stop"] = True
        self.update_managed_job(job_id, status="stopping", phase="stop requested", detail="Stop requested. The job will halt after the current network operation.")
        self.log(f"Stop requested for {job_id}: {self.jobs[job_id]['name']}", self.job_log)

    def stop_all_jobs(self):
        if not self.jobs:
            return
        for job_id, job in self.jobs.items():
            if job["status"] not in ("complete", "failed", "stopped"):
                job["stop"] = True
                self.update_managed_job(job_id, status="stopping", phase="stop requested", detail="Stop requested. Waiting for current operation to finish.")
        self.log("Stop requested for all active jobs.", self.job_log)

    def has_active_jobs(self):
        return any(job["status"] not in ("complete", "failed", "stopped") for job in self.jobs.values())

    def update_map_progress_ui(self, current, total, detail, color=None):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, lambda: self.update_map_progress_ui(current, total, detail, color))
            return

        progress = 0 if total <= 0 else min(1, max(0, current / total))
        self.map_progress.set(progress)
        self.map_status_label.configure(text=detail, text_color=color or self.colors["muted"])

    def open_in_browser(self):
        try:
            url = self.get_current_url()
        except ValueError as e:
            messagebox.showwarning("Incomplete URL", str(e))
            return
        webbrowser.open(url)
        self.log(f"Opened in browser: {url}")

    def download_current(self):
        try:
            url = self.get_current_url()
            filename = self.get_filename()
        except ValueError as e:
            messagebox.showwarning("Incomplete URL", str(e))
            return
        save_dir = self.default_download_dir.get()
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        if os.path.exists(filepath) and self.skip_existing.get():
            self.log(f"Skipped because it already exists: {filename}")
            return
        
        self.log(f"Starting download: {filename}")
        
        if self.use_selenium.get() and SELENIUM_AVAILABLE:
            threading.Thread(target=self._download_selenium, args=(url, filepath), daemon=True).start()
        else:
            threading.Thread(target=self._download_requests, args=(url, filepath), daemon=True).start()

    def _download_requests(self, url, filepath, silent=False):
        headers = DEFAULT_HEADERS.copy()
        try:
            custom = json.loads(self.headers_text.get("1.0", "end").strip())
            headers.update(custom)
        except:
            pass
        
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                downloaded = 0
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                size_mb = downloaded / (1024 * 1024)
                if not silent:
                    self.log(f"✅ Downloaded: {os.path.basename(filepath)} ({size_mb:.1f} MB)")
                return True
        except Exception as e:
            if not silent:
                self.log(f"❌ Download failed: {str(e)[:80]}")
            return False

    def _download_selenium(self, url, filepath, silent=False):
        if not SELENIUM_AVAILABLE:
            self.log("❌ Selenium not available. Install: pip install selenium webdriver-manager")
            return False
        
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        if self.chrome_binary.get() and os.path.exists(self.chrome_binary.get()):
            options.binary_location = self.chrome_binary.get()
        
        prefs = {
            "download.default_directory": os.path.dirname(filepath),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            time.sleep(2.5)
            js = f"""
            const a = document.createElement('a');
            a.href = '{url}';
            a.download = '{os.path.basename(filepath)}';
            document.body.appendChild(a);
            a.click();
            a.remove();
            """
            driver.execute_script(js)
            time.sleep(3)
            driver.quit()
            
            if os.path.exists(filepath):
                if not silent:
                    self.log(f"✅ Selenium download complete: {os.path.basename(filepath)}")
                return True
            else:
                if not silent:
                    self.log("⚠️ Selenium triggered but file not found. Check Chrome downloads.")
                return False
        except Exception as e:
            if not silent:
                self.log(f"❌ Selenium error: {str(e)[:70]}")
            return False

    def add_to_collection(self):
        try:
            url = self.get_current_url()
            filename = self.get_filename()
        except ValueError as e:
            messagebox.showwarning("Incomplete URL", str(e))
            return
        
        if any(item["url"] == url for item in self.collection):
            self.log("Already in collection")
            return
        
        self.collection.append({"url": url, "filename": filename, "added": datetime.now().isoformat()})
        self.save_collection()
        self.refresh_collection_list()
        self.log(f"Added to collection: {filename}")

    def refresh_collection_list(self):
        self.collection_listbox.delete(0, END)
        for item in self.collection:
            self.collection_listbox.insert(END, f"  {item['filename']}  →  {item['url'][:60]}...")
        self.collection_count_label.configure(text=f"{len(self.collection)} videos")

    def remove_selected(self):
        selection = self.collection_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        removed = self.collection.pop(idx)
        self.save_collection()
        self.refresh_collection_list()
        self.log(f"🗑️ Removed: {removed['filename']}")

    def clear_collection(self):
        if messagebox.askyesno("Clear Collection", "Remove all videos from collection?"):
            self.collection = []
            self.save_collection()
            self.refresh_collection_list()
            self.log("🧹 Collection cleared")

    def start_batch_download(self):
        if not self.collection:
            messagebox.showwarning("Empty Collection", "Add videos to collection first!")
            return
        
        save_dir = filedialog.askdirectory(title="Choose folder to save all videos",
                                           initialdir=self.default_download_dir.get())
        if not save_dir:
            return
        
        self.is_downloading = True
        self.log(f"🚀 Starting BATCH DOWNLOAD of {len(self.collection)} videos → {save_dir}")
        self.status_label.configure(text="Batch download in progress...", text_color="#f59e0b")
        threading.Thread(target=self._batch_worker, args=(save_dir,), daemon=True).start()

    def _batch_worker(self, save_dir):
        os.makedirs(save_dir, exist_ok=True)
        total = len(self.collection)
        success_count = 0
        
        for i, item in enumerate(self.collection):
            if not self.is_downloading:
                break
            filename = item["filename"]
            filepath = os.path.join(save_dir, filename)
            
            if os.path.exists(filepath) and self.skip_existing.get():
                self.log(f"⏭️ [{i+1}/{total}] Skipped (exists): {filename}")
                success_count += 1
                continue
            
            self.log(f"⬇️ [{i+1}/{total}] Downloading: {filename}")
            
            if self.use_selenium.get() and SELENIUM_AVAILABLE:
                ok = self._download_selenium(item["url"], filepath, silent=True)
            else:
                ok = self._download_requests(item["url"], filepath, silent=True)
            
            if ok:
                success_count += 1
            
            if i < total - 1:
                delay = float(self.delay.get()) + random.uniform(-1.5, 1.5)
                time.sleep(max(3, delay))
        
        self.is_downloading = False
        self.log(f"🎉 BATCH COMPLETE: {success_count}/{total} successful")
        self.status_label.configure(text="Batch finished • Ready", text_color="#22c55e")

    def preview_job(self):
        self.update_job_preview()

    def update_job_preview(self):
        preserve_logs = hasattr(self, "jobs") and self.has_active_jobs()
        try:
            prefix = int(self.job_prefix.get())
            start = int(self.job_start.get())
            end = int(self.job_end.get())
            step = int(self.job_step.get())
        except ValueError:
            if not preserve_logs:
                self.job_log.delete("1.0", "end")
                self.job_log.insert("end", "Live job preview waiting for valid numeric values.\n")
            return

        if step <= 0:
            if not preserve_logs:
                self.job_log.delete("1.0", "end")
                self.job_log.insert("end", "Step must be greater than 0.\n")
            return

        if start > end:
            if not preserve_logs:
                self.job_log.delete("1.0", "end")
                self.job_log.insert("end", "Start number must be less than or equal to end number.\n")
            return

        if preserve_logs:
            return
        
        count = len(range(start, end + 1, step))
        self.job_log.delete("1.0", "end")
        smart_map_note = "enabled" if self.job_use_smart_map.get() else "disabled"
        self.job_log.insert("end", f"Live job preview: {count} videos\n")
        self.job_log.insert("end", f"Prefix: {prefix}\n")
        self.job_log.insert("end", f"Range: {start} → {end} (step {step})\n\n")
        self.job_log.insert("end", f"Smart Map preflight: {smart_map_note}\n\n")
        self.job_log.insert("end", "First 5 URLs:\n")
        for n in list(range(start, end + 1, step))[:5]:
            base = self.base_url.get().rstrip("/")
            self.job_log.insert("end", f"  {base}/{prefix}/{n}.mp4\n")

    def start_range_job(self):
        try:
            prefix = int(self.job_prefix.get())
            start = int(self.job_start.get())
            end = int(self.job_end.get())
            step = int(self.job_step.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers")
            return

        if step <= 0:
            messagebox.showerror("Invalid Input", "Step must be greater than 0")
            return

        if start > end:
            messagebox.showerror("Invalid Input", "Start number must be less than or equal to end number")
            return
        
        save_dir = filedialog.askdirectory(title="Save folder for range job",
                                           initialdir=self.default_download_dir.get())
        if not save_dir:
            return
        
        had_active_jobs = self.has_active_jobs()
        numbers = list(range(start, end + 1, step))
        job_id = self.create_range_job_record(prefix, start, end, step, save_dir, self.job_use_smart_map.get())
        if not had_active_jobs:
            self.job_log.delete("1.0", "end")
        else:
            self.log("--- New job queued while other jobs are active ---", self.job_log)
        self.update_managed_job(job_id, current=0, total=len(numbers), status="queued", phase="preparing", detail=f"{len(numbers)} videos queued • saving to {save_dir}")
        self.log(f"{job_id} queued: {start}-{end} (prefix {prefix}, step {step})", self.job_log)
        self.log(f"Destination: {save_dir}", self.job_log)
        self.log(f"Mode: {self.mode_label.cget('text')} • Delay: {float(self.delay.get()):.0f}s + jitter", self.job_log)
        threading.Thread(target=self._range_job_worker, args=(job_id, prefix, start, end, step, save_dir, self.job_use_smart_map.get()), daemon=True).start()

    def _range_job_worker(self, job_id, prefix, start, end, step, save_dir, use_smart_map):
        os.makedirs(save_dir, exist_ok=True)
        numbers = list(range(start, end + 1, step))
        original_total = len(numbers)
        base = self.base_url.get().rstrip("/")
        mapped_missing = 0
        started_at = time.time()
        self.update_managed_job(job_id, status="running", phase="starting", detail=f"Started • {original_total} candidate values", started_at=started_at)

        if use_smart_map:
            self.log(f"{job_id}: Smart Map preflight enabled; mapping range before downloads.", self.job_log)
            self.update_managed_job(job_id, current=0, total=max(1, original_total), status="mapping", phase="smart map preflight", detail=f"Mapping {start}-{end} for prefix {prefix} before downloading")
            tested = self.run_range_smart_map_preflight(job_id, base, prefix, start, end, max(1, end - start + 1))
            if not self.job_should_continue(job_id):
                self.update_managed_job(job_id, status="stopped", phase="stopped during mapping", detail="Stopped during Smart Map preflight.", finished_at=time.time())
                self.log(f"{job_id}: stopped during Smart Map preflight.", self.job_log)
                return
            confirmed_available = {n for n, ok in tested.items() if ok}
            confirmed_missing = {n for n, ok in tested.items() if not ok}
            mapped_missing = len([n for n in numbers if n in confirmed_missing])
            unknown = [n for n in numbers if n not in tested]
            numbers = [n for n in numbers if n in confirmed_available]
            self.log(f"{job_id}: Smart Map preflight complete: {len(confirmed_available)} valid, {len(confirmed_missing)} missing, {len(unknown)} unknown in requested job sequence.", self.job_log)
            if unknown:
                self.log(f"Unknown values skipped because they were not confirmed by the map: {unknown[:12]}{'...' if len(unknown) > 12 else ''}", self.job_log)
            self.update_managed_job(job_id, current=0, total=max(1, len(numbers)), status="running", phase="download queue prepared", detail=f"{len(numbers)} valid videos queued • {mapped_missing} mapped missing skipped")

        total = len(numbers)
        success = 0
        failed = 0
        skipped = 0

        if total == 0:
            self.update_managed_job(job_id, current=1, total=1, status="complete", phase="no valid videos", detail=f"Smart Map skipped {mapped_missing or original_total} unavailable values.", finished_at=time.time())
            self.log(f"{job_id}: finished with no confirmed valid videos to download.", self.job_log)
            return
        
        for i, n in enumerate(numbers):
            if not self.job_should_continue(job_id):
                break
            url = f"{base}/{prefix}/{n}.mp4"
            filename = f"{prefix}_{n}.mp4"
            filepath = os.path.join(save_dir, filename)
            completed = i
            elapsed = time.time() - started_at
            eta = self.format_duration((elapsed / completed) * (total - completed)) if completed else "calculating"
            
            if os.path.exists(filepath) and self.skip_existing.get():
                skipped += 1
                success += 1
                self.update_managed_job(job_id, current=i + 1, total=total, status="running", phase=f"skipped {filename}", detail=f"{i+1}/{total} complete • {success} ok, {failed} failed, {skipped} skipped • ETA {eta}", success=success, failed=failed, skipped=skipped)
                self.log(f"{job_id} [{i+1}/{total}] Skipped existing file: {filename}", self.job_log)
                continue
            
            self.update_managed_job(job_id, current=i, total=total, status="running", phase=f"downloading {filename}", detail=f"{i+1}/{total} • {url} • ETA {eta}", success=success, failed=failed, skipped=skipped)
            self.log(f"{job_id} [{i+1}/{total}] Downloading {filename}", self.job_log)
            self.log(f"URL: {url}", self.job_log)
            
            if self.use_selenium.get() and SELENIUM_AVAILABLE:
                ok = self._download_selenium(url, filepath, silent=True)
            else:
                ok = self._download_requests(url, filepath, silent=True)
            
            if ok:
                success += 1
                self.log(f"{job_id} [{i+1}/{total}] Done: {filename}", self.job_log)
            else:
                failed += 1
                self.log(f"{job_id} [{i+1}/{total}] Failed: {filename}", self.job_log)

            completed = i + 1
            elapsed = time.time() - started_at
            eta = self.format_duration((elapsed / completed) * (total - completed)) if completed else "calculating"
            self.update_managed_job(job_id, current=completed, total=total, status="running", phase=f"completed {filename}", detail=f"{completed}/{total} complete • {success} ok, {failed} failed, {skipped} skipped • ETA {eta}", success=success, failed=failed, skipped=skipped)
            
            if i < total - 1:
                delay = float(self.delay.get()) + random.uniform(-1, 2)
                wait_seconds = max(4, delay)
                self.log(f"{job_id}: Waiting {wait_seconds:.1f}s before the next video", self.job_log)
                for remaining in range(int(wait_seconds), 0, -1):
                    if not self.job_should_continue(job_id):
                        break
                    self.update_managed_job(job_id, current=completed, total=total, status="waiting", phase="waiting before next video", detail=f"Next up: {prefix}_{numbers[i + 1]}.mp4 • {remaining}s left • {completed}/{total} complete • ETA {eta}", success=success, failed=failed, skipped=skipped)
                    time.sleep(1)
                fractional_wait = wait_seconds - int(wait_seconds)
                if self.job_should_continue(job_id) and fractional_wait > 0:
                    time.sleep(fractional_wait)
        
        elapsed = self.format_duration(time.time() - started_at)
        if self.job_should_continue(job_id):
            status = "complete"
            phase = "finished"
            detail = f"{success}/{total} ok • {failed} failed • {skipped} skipped • Took {elapsed}"
            self.log(f"{job_id}: Range job finished: {success}/{total} ok, {failed} failed, {skipped} skipped, took {elapsed}", self.job_log)
        else:
            status = "stopped"
            phase = "stopped"
            detail = f"Stopped at {success + failed + skipped}/{total} • {success} ok, {failed} failed, {skipped} skipped • Ran {elapsed}"
            self.log(f"{job_id}: Range job stopped: {success} ok, {failed} failed, {skipped} skipped, ran {elapsed}", self.job_log)
        self.update_managed_job(job_id, current=success + failed + skipped, total=total, status=status, phase=phase, detail=detail, finished_at=time.time(), success=success, failed=failed, skipped=skipped)

    def choose_default_folder(self):
        folder = filedialog.askdirectory(initialdir=self.default_download_dir.get())
        if folder:
            self.default_download_dir.set(folder)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                self.base_url.set(data.get("base_url", self.base_url.get()))
                self.prefix.set(str(data.get("prefix", self.prefix.get())))
                self.num.set(str(data.get("num", self.num.get())))
                self.delay.set(data.get("delay", self.delay.get()))
                self.default_download_dir.set(data.get("download_dir", self.default_download_dir.get()))
                self.use_selenium.set(data.get("use_selenium", False))
                self.chrome_binary.set(data.get("chrome_binary", self.chrome_binary.get()))
                self.skip_existing.set(data.get("skip_existing", True))
                self.smart_skip_missing.set(data.get("smart_skip_missing", True))
                self.job_use_smart_map.set(data.get("job_use_smart_map", True))
                if "headers" in data:
                    self.saved_headers = data["headers"]
            except Exception as e:
                print(f"Config load error: {e}")

    def save_config(self):
        try:
            headers = json.loads(self.headers_text.get("1.0", "end").strip() or "{}")
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid Headers JSON", f"Fix the custom headers JSON before saving.\n\n{e}")
            return

        data = {
            "base_url": self.base_url.get(),
            "prefix": self.safe_int(self.prefix.get(), 0),
            "num": self.safe_int(self.num.get(), 0),
            "delay": float(self.delay.get()),
            "download_dir": self.default_download_dir.get(),
            "use_selenium": self.use_selenium.get(),
            "chrome_binary": self.chrome_binary.get(),
            "skip_existing": self.skip_existing.get(),
            "smart_skip_missing": self.smart_skip_missing.get(),
            "job_use_smart_map": self.job_use_smart_map.get(),
            "headers": headers
        }
        self.saved_headers = headers
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
        self.log("💾 Settings saved successfully")

    def load_collection(self):
        if os.path.exists(COLLECTION_FILE):
            try:
                with open(COLLECTION_FILE, "r") as f:
                    self.collection = json.load(f)
            except:
                self.collection = []

    def save_collection(self):
        with open(COLLECTION_FILE, "w") as f:
            json.dump(self.collection, f, indent=2)

    def load_unavailable_videos(self):
        if os.path.exists(UNAVAILABLE_FILE):
            try:
                with open(UNAVAILABLE_FILE, "r") as f:
                    self.unavailable_urls = set(json.load(f))
            except Exception:
                self.unavailable_urls = set()

    def save_unavailable_videos(self):
        with open(UNAVAILABLE_FILE, "w") as f:
            json.dump(sorted(self.unavailable_urls), f, indent=2)

    def load_video_maps(self):
        if os.path.exists(VIDEO_MAP_FILE):
            try:
                with open(VIDEO_MAP_FILE, "r") as f:
                    self.video_maps = json.load(f)
                for data in self.video_maps.values():
                    base = data.get("base_url", "").rstrip("/")
                    prefix = data.get("prefix")
                    if not base or prefix is None:
                        continue
                    for n in data.get("missing", []):
                        self.unavailable_urls.add(self.url_for(base, prefix, int(n)))
                    for n in data.get("available", []):
                        self.unavailable_urls.discard(self.url_for(base, prefix, int(n)))
            except Exception:
                self.video_maps = {}

    def save_video_maps(self):
        with open(VIDEO_MAP_FILE, "w") as f:
            json.dump(self.video_maps, f, indent=2)

    def on_closing(self):
        self.stop_video_preview()
        self.save_config()
        self.save_collection()
        self.save_unavailable_videos()
        self.save_video_maps()
        self.destroy()


if __name__ == "__main__":
    app = VideoScraperApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
