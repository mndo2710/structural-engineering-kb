"""Script to generate offscreen screenshots of the redesigned PySide6 GUI."""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.dialogs.add_calculation_dialog import AddCalculationDialog

def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Load Windows fonts for clean offscreen rendering
    for font_file in ["segoeui.ttf", "segoeuib.ttf", "segoeuiz.ttf", "seguisym.ttf", "arial.ttf"]:
        font_path = f"C:/Windows/Fonts/{font_file}"
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)

    app.setFont(QFont("Segoe UI", 10))

    out_dir = os.path.abspath("tests/screenshots")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Main Window Expanded View (Wood connection workspace C-02)
    win = MainWindow()
    win.resize(1320, 840)
    win.select_calculation("C-02")
    win.show()
    app.processEvents()

    pix_main = win.grab()
    p1 = os.path.join(out_dir, "redesign_main_window_wood_connection.png")
    pix_main.save(p1, "PNG")
    print(f"Saved: {p1} ({pix_main.width()}x{pix_main.height()})")

    # 2. Main Window Collapsed Rail (48px)
    win.toggle_sidebar()
    win.sidebar_frame.setFixedWidth(48)
    app.processEvents()

    pix_collapsed = win.grab()
    p2 = os.path.join(out_dir, "redesign_sidebar_collapsed_rail.png")
    pix_collapsed.save(p2, "PNG")
    print(f"Saved: {p2} ({pix_collapsed.width()}x{pix_collapsed.height()})")

    # 3. Add Calculation Dialog
    dialog = AddCalculationDialog()
    dialog.resize(850, 560)
    dialog.show()
    app.processEvents()

    pix_dialog = dialog.grab()
    p3 = os.path.join(out_dir, "redesign_add_calculation_dialog.png")
    pix_dialog.save(p3, "PNG")
    print(f"Saved: {p3} ({pix_dialog.width()}x{pix_dialog.height()})")

if __name__ == "__main__":
    main()
