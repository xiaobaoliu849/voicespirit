import sys
import os
import logging
import traceback
import signal
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
# Ensure the app directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ui.main_window_modern import ModernMainWindow
from app.ui.styles.theme import apply_theme
from app.ui.components.splash_screen import SplashScreen

def get_app_path():
    """Get the application base path, works for both dev and packaged."""
    if getattr(sys, 'frozen', False):
        # Running as packaged exe
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def setup_logging():
    """Configures logging to file and console."""
    log_file = os.path.join(get_app_path(), 'voice_spirit.log')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def global_exception_hook(exctype, value, tb):
    """
    Global exception handler to catch unhandled exceptions
    and display a dialog instead of crashing silently.
    """
    # Skip KeyboardInterrupt - let it close the app gracefully
    if issubclass(exctype, KeyboardInterrupt):
        logging.info("KeyboardInterrupt received, exiting...")
        app = QApplication.instance()
        if app:
            app.quit()
        return
    
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.critical(f"Unhandled exception:\n{error_msg}")
    
    # Ensure usage of the existing QApplication instance
    app = QApplication.instance()
    if app:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Application Error")
        msg_box.setText("An unexpected error occurred.")
        msg_box.setDetailedText(error_msg)
        # Explicitly set style sheet for error dialog
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
                color: #333333;
            }
            QLabel {
                color: #333333;
                background-color: transparent;
            }
            QPushButton {
                background-color: #E66840;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #D45630;
            }
        """)
        msg_box.exec()
    else:
        print("CRITICAL: Application crashed before UI could initialize.")
        print(error_msg)

sys.excepthook = global_exception_hook

# Handle Ctrl+C in terminal
def sigint_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    logging.info("Ctrl+C received, shutting down...")
    app = QApplication.instance()
    if app:
        app.quit()
    else:
        sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

def main():
    setup_logging()
    logging.info("Starting Voice Spirit 2.0...")

    # High DPI scaling
    # os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1" # Qt6 defaults this to 1
    # os.environ["QT_SCALE_FACTOR"] = "1" # REMOVED: This forces 100% scale, breaking High DPI
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Critical for Windows sharpness: Tell OS we are DPI aware
    if os.name == 'nt':
        try:
            import ctypes
            # 2 = Process_Per_Monitor_DPI_Aware (Better scaling), 1 = System_DPI_Aware
            ctypes.windll.shcore.SetProcessDpiAwareness(2) 
        except Exception:
            pass
    
    # DPI Scaling: Use Round instead of PassThrough for pixel-perfect rendering
    # PassThrough causes fractional pixel calculations = blurry text
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Use Fusion for better QSS support

    # Force light theme palette to override Windows dark mode
    # This ensures QMessageBox and other dialogs use light colors
    from PySide6.QtGui import QPalette, QColor
    light_palette = QPalette()
    # Window and base colors
    light_palette.setColor(QPalette.Window, QColor(255, 255, 255))
    light_palette.setColor(QPalette.WindowText, QColor(55, 65, 81))  # TEXT_SECONDARY
    light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.AlternateBase, QColor(243, 244, 246))  # GRAY_100
    light_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ToolTipText, QColor(55, 65, 81))
    light_palette.setColor(QPalette.Text, QColor(55, 65, 81))
    light_palette.setColor(QPalette.Button, QColor(243, 244, 246))
    light_palette.setColor(QPalette.ButtonText, QColor(55, 65, 81))
    light_palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    light_palette.setColor(QPalette.Link, QColor(230, 104, 64))  # PRIMARY
    light_palette.setColor(QPalette.Highlight, QColor(230, 104, 64))  # PRIMARY
    light_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    # Disabled colors
    light_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(156, 163, 175))
    light_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(156, 163, 175))
    light_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(156, 163, 175))
    app.setPalette(light_palette)

    app.setApplicationName("Voice Spirit")
    app.setOrganizationName("VoiceSpiritTeam")
    
    # Set application icon
    from PySide6.QtGui import QIcon, QFont
    from app.core.config import get_resource_path
    icon_path = get_resource_path('logo.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        logging.info(f"Application icon loaded: {icon_path}")
    else:
        logging.warning(f"Icon file not found: {icon_path}")

    # Font Configuration: Microsoft YaHei @ 12pt (Better CJK rendering)
    font = QFont("Microsoft YaHei")  # Not "UI" - better for CJK
    font.setPointSize(12)  # Standard readable size
    font.setHintingPreference(QFont.PreferFullHinting)  # Sharper text edges
    # Note: Don't use PreferAntialias - let Windows ClearType handle subpixel rendering
    app.setFont(font)

    # Apply global theme
    apply_theme(app)

    try:
        # Create and show Splash Screen
        splash = SplashScreen()
        splash.show()
        
        # Process events to render splash immediately
        app.processEvents()
        
        # Initialize Main Window (Simulate loading time if fast)
        # In real app, we do heavy loading here (e.g. DB init, Config)
        main_window = ModernMainWindow()
        apply_theme(app)
        
        # Use a timer to close splash and show main window after delay
        QTimer.singleShot(2500, lambda: splash.finish(main_window)) # 2.5s delay for effect
        
        # Run loop
        sys.exit(app.exec())
    except Exception as e:
        logging.critical("Main loop crashed", exc_info=True)
        # The excepthook might catch this, but just in case
        sys.exit(1)

if __name__ == "__main__":
    main()

