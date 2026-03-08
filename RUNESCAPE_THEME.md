# RuneScape Theme Code for XP Waste Timer

## To add the RuneScape theme, find the _apply_theme function in main.py and add this code after the docstring:

```python
        if self._theme == "runescape":
            # RuneScape-inspired color palette
            style = """
            QWidget {
                color: #FFD700;
                font-family: Segoe UI, sans-serif;
                background-color: #2B1B0F;
            }
            QDialog {
                background-color: #2B1B0F;
            }
            QMenuBar {
                background-color: #2B1B0F;
                color: #FFD700;
                border: none;
            }
            QMenuBar::item:selected {
                background-color: #3D2A1D;
            }
            QMenu {
                background-color: #2B1B0F;
                color: #FFD700;
                border: 1px solid #8B4513;
            }
            QMenu::item:selected {
                background-color: #00FF00;
                color: #000000;
            }
            #SessionBox {
                border-radius: 8px;
                padding: 8px;
                border: 2px solid #8B4513;
            }
            #SessionBox[sessionType="focus"] {
                background-color: #3D2A1D;
                border-color: #FFD700;
            }
            #SessionBox[sessionType="short_break"] {
                background-color: #1A3D2E;
                border-color: #00FF00;
            }
            #SessionBox[sessionType="long_break"] {
                background-color: #2D1B69;
                border-color: #00BFFF;
            }
            #TitleLabel {
                font-size: 24px;
                font-weight: bold;
                margin: 12px 0;
                color: #FFD700;
            }
            #SessionLabel {
                font-size: 18px;
                margin: 8px 0;
                color: #FFD700;
            }
            #CycleLabel {
                font-size: 13px;
                margin: 4px 0;
                color: #C0C0C0;
            }
            #TimeLabel {
                font-size: 40px;
                font-weight: bold;
                margin: 16px 0;
                color: #00FF00;
            }
            #SessionLabel, #TimeLabel, #CycleLabel {
                background-color: transparent;
            }
            #TotalTimeLabel, #OverallTimeLabel {
                font-size: 14px;
                margin: 4px 0;
                color: #C0C0C0;
            }
            QPushButton {
                background-color: #8B4513;
                color: #FFD700;
                border: 2px solid #CD853F;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #A0522D;
                border-color: #FFD700;
            }
            QPushButton:pressed {
                background-color: #654321;
                color: #00FF00;
            }
            QGroupBox {
                border: 2px solid #8B4513;
                border-radius: 4px;
                margin-top: 10px;
                color: #FFD700;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QListWidget {
                background-color: #3D2A1D;
                border: 2px solid #8B4513;
                color: #FFD700;
            }
            QSpinBox {
                background-color: #3D2A1D;
                color: #FFD700;
                border: 2px solid #8B4513;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QScrollBar:vertical {
                background-color: #3D2A1D;
                width: 12px;
                border: 1px solid #8B4513;
            }
            QScrollBar::handle:vertical {
                background-color: #FFD700;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00FF00;
            }
            QScrollBar:horizontal {
                background-color: #3D2A1D;
                height: 12px;
                border: 1px solid #8B4513;
            }
            QScrollBar::handle:horizontal {
                background-color: #FFD700;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #00FF00;
            }
            """
```

## Also update the _set_theme function to include "runescape":

Change this line:
```python
if theme not in ("dark", "light"):
```

To:
```python
if theme not in ("runescape", "dark", "light"):
```

## Update _toggle_theme function for 3-way cycling:

Replace the _toggle_theme function with:
```python
def _toggle_theme(self):
    """Cycles between runescape, dark, and light themes."""
    if self._theme == "runescape":
        new_theme = "dark"
    elif self._theme == "dark":
        new_theme = "light"
    else:
        new_theme = "runescape"
    self._set_theme(new_theme)
    # Update menu text
    if hasattr(self, "theme_action"):
        if self._theme == "runescape":
            self.theme_action.setText("Switch to Dark Mode")
        elif self._theme == "dark":
            self.theme_action.setText("Switch to Light Mode")
        else:
            self.theme_action.setText("Switch to RuneScape Mode")
```

## Color Palette Details:

- **Gold (#FFD700)**: Primary text color, reminiscent of RuneScape's gold
- **Brown (#2B1B0F)**: Main background, earthy RuneScape interface feel
- **Bronze (#8B4513)**: Button backgrounds and borders
- **Green (#00FF00)**: XP gain color and hover effects
- **Blue (#00BFFF)**: Long break session accent
- **Dark Green (#1A3D2E)**: Short break session background
- **Light Gray (#C0C0C0)**: Secondary text