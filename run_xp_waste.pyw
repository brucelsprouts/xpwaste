#!/usr/bin/env python3
"""
XP Waste Timer - Windows Launcher
Double-click this file to run the XP Waste Timer without a console window.

If you get an error, try running setup.bat first.
"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    # Import and run the main application
    from main import main
    main()
except ImportError as e:
    import tkinter.messagebox as msgbox
    msgbox.showerror(
        "Missing Dependencies", 
        f"Required module not found: {e}\n\n"
        "Please run setup.bat or install PyQt5:\n"
        "pip install PyQt5"
    )