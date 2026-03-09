
import ctypes
import ctypes.wintypes
import logging
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QKeySequence

# Constants for Windows API
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

class GlobalHotkeyManager(QObject):
    """
    Manages global hotkeys using Windows Native API (user32.dll).
    This ensures hotkeys work even when the application is not in focus.
    """
    # Signal emitted when a registered hotkey is pressed. 
    # Sends the action name (e.g., "toggle_window")
    hotkey_triggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user32 = ctypes.windll.user32
        self.hotkey_map = {}  # ID -> Action Name
        self.next_id = 1
        self.logger = logging.getLogger(__name__)

    def register_hotkey(self, action_name, key_sequence_str, hwnd=None):
        """
        Register a global hotkey.
        
        Args:
            action_name (str): Unique identifier for the action (e.g., "toggle_window")
            key_sequence_str (str): Key sequence string (e.g., "Alt+Space", "Ctrl+Shift+X")
            hwnd (int, optional): Window handle to associate the hotkey with.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Unregister existing hotkey for this action if it exists
        # (We need to track action->id mapping to do this efficiently, 
        #  but for now we simply rely on the user manually unregistering or overwriting)
        
        modifiers, vk = self._parse_key_sequence(key_sequence_str)
        if vk is None:
            self.logger.error(f"Invalid key sequence: {key_sequence_str}")
            return False

        # Generate a new unique ID
        hotkey_id = self.next_id
        self.next_id += 1

        # Register with Windows
        # RegisterHotKey(hWnd, id, fsModifiers, vk)
        # If hWnd is provided, messages are sent to that window.
        # If hWnd is None, messages are posted to the thread message queue.
        
        success = self.user32.RegisterHotKey(hwnd, hotkey_id, modifiers, vk)
        
        if success:
            self.hotkey_map[hotkey_id] = action_name
            self.logger.info(f"Registered hotkey: {key_sequence_str} -> {action_name} (ID: {hotkey_id})")
            return True
        else:
            self.logger.error(f"Failed to register hotkey: {key_sequence_str} (Error: {ctypes.GetLastError()})")
            return False

    def unregister_all(self, hwnd=None):
        """Unregister all hotkeys managed by this instance."""
        for hotkey_id in list(self.hotkey_map.keys()):
            self.user32.UnregisterHotKey(hwnd, hotkey_id)
        self.hotkey_map.clear()
        self.logger.info("Unregistered all hotkeys.")

    def process_native_event(self, event_type, message):
        """
        Process native events forwarded from MainWindow.
        
        Args:
            event_type (bytes): The event type (e.g. b"windows_generic_MSG")
            message (int): The pointer to the MSG structure
            
        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                if hotkey_id in self.hotkey_map:
                    action = self.hotkey_map[hotkey_id]
                    self.logger.info(f"Hotkey triggered: {action}")
                    self.hotkey_triggered.emit(action)
                    return True
        return False

    def _parse_key_sequence(self, key_str):
        """
        Parse a Qt-style key sequence string into Windows modifiers and VK code.
        """
        if not key_str:
            return 0, None
            
        sequence = QKeySequence(key_str)
        key_comb = sequence[0] # Get the first key combination as QKeyCombination
        
        # Convert to int for bitwise operations
        key = key_comb.toCombined()
        
        # Extract modifiers
        modifiers = 0
        if key & Qt.KeyboardModifier.AltModifier.value:
            modifiers |= MOD_ALT
        if key & Qt.KeyboardModifier.ControlModifier.value:
            modifiers |= MOD_CONTROL
        if key & Qt.KeyboardModifier.ShiftModifier.value:
            modifiers |= MOD_SHIFT
        if key & Qt.KeyboardModifier.MetaModifier.value:
            modifiers |= MOD_WIN
            
        # Extract key code (strip modifiers)
        # This is a simplification. Qt key codes often map directly to VK codes for ASCII,
        # but special keys might need a lookup table. 
        # For simple keys (A-Z, 0-9, Space, etc.), Qt key code matches VK or ASCII.
        key_code = key & ~Qt.KeyboardModifier.KeyboardModifierMask.value
        
        vk = None
        if 0x20 <= key_code <= 0x5A: # Space .. Z (ASCII)
             vk = key_code
        elif 0x30 <= key_code <= 0x39: # 0-9
             vk = key_code
        else:
            # Helper map for common non-ASCII keys
            qt_to_vk = {
                Qt.Key_Space: 0x20,
                Qt.Key_F1: 0x70, Qt.Key_F2: 0x71, Qt.Key_F3: 0x72, Qt.Key_F4: 0x73,
                Qt.Key_F5: 0x74, Qt.Key_F6: 0x75, Qt.Key_F7: 0x76, Qt.Key_F8: 0x77,
                Qt.Key_F9: 0x78, Qt.Key_F10: 0x79, Qt.Key_F11: 0x7A, Qt.Key_F12: 0x7B,
                Qt.Key_Escape: 0x1B,
                Qt.Key_Tab: 0x09,
                Qt.Key_Backspace: 0x08,
                Qt.Key_Return: 0x0D,
                Qt.Key_Enter: 0x0D,
                Qt.Key_Insert: 0x2D,
                Qt.Key_Delete: 0x2E,
                Qt.Key_Home: 0x24,
                Qt.Key_End: 0x23,
                Qt.Key_PageUp: 0x21,
                Qt.Key_PageDown: 0x22,
                Qt.Key_Left: 0x25,
                Qt.Key_Up: 0x26,
                Qt.Key_Right: 0x27,
                Qt.Key_Down: 0x28,
            }
            vk = qt_to_vk.get(key_code)
            
        # Fallback for letters if mistakenly handled above or lower case
        if vk is None and 0x41 <= key_code <= 0x5A: # A-Z
             vk = key_code
             
        return modifiers, vk
