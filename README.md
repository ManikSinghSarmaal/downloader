# College Video Scraper Pro v2.0
 
A powerful desktop tool for scraping and downloading videos from college data repositories with automation and IP protection.
 
## Features
- Smart URL iterator with live preview & one-click actions
- Direct requests downloads (fast) + Selenium fallback (real Chrome Beta clicks)
- Collection system with batch download + configurable delays (10s default + jitter)
- Range Jobs for automated bulk scraping (start–end–step)
 
## Quick Start (Mac)
```bash
uv init
uv add customtkinter requests
uv run python main.py
```
(Optional: `pip install selenium webdriver-manager` for Selenium mode)
 
## Usage
1. Set your college Base URL in Explorer tab
2. Use +/- buttons to iterate, then Download or Add to Collection
3. Batch Download from Collection (asks for save folder)
4. Use Jobs tab for large range automation
 
