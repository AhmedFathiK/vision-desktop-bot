import pygetwindow as gw
from time import sleep

def handle_dialogs(bot):
    """
    Dispatcher method to handle known and unknown dialogs.
    Args:
        bot: The bot instance to interact with (find, type_keys, etc.)
    """
    # 1. Handle "Cannot find file" dialog (known)
    if handle_cant_find_file_dialog(bot):
        return
        
    # 2. Handle "Confirm Save As" dialog (known)
    if handle_confirm_save_as_dialog(bot):
        return

    # 3. Handle unknown/generic dialogs
    handle_unknown_dialogs(bot)

def handle_cant_find_file_dialog(bot):
    """Handles the 'Cannot find file' dialog using image recognition."""
    if bot.find("cant_find_file_dialog_dark", matching=0.97, waiting_time=500):
        print("[INFO] Detected 'Cannot find file' dialog (Dark). Dismissing...")
        bot.key_enter()
        return True
    elif bot.find("cant_find_file_dialog_light", matching=0.97, waiting_time=500):
        print("[INFO] Detected 'Cannot find file' dialog (Light). Dismissing...")
        bot.key_enter()
        return True
    return False

def handle_confirm_save_as_dialog(bot):
    """Handles the 'Confirm Save As' dialog by checking window title."""
    windows = gw.getWindowsWithTitle("Confirm Save As")
    if windows:
        print("[INFO] Detected 'Confirm Save As' dialog. Confirming...")
        windows[0].activate()
        bot.type_keys(["alt", "y"])
        return True
    return False

def handle_unknown_dialogs(bot):
    """
    Handles any unexpected dialogs by checking if the active window is NOT the main Notepad window.
    Attempts to bypass them by pressing Enter or Esc.
    """
    try:
        # Wait a brief moment to allow any potential dialog to appear and gain focus
        sleep(0.5)
        
        active_window = gw.getActiveWindow()
        if not active_window:
            return

        # Ignore windows with empty titles or known system windows (e.g., Desktop/Taskbar)
        if not active_window.title or active_window.title in ["Program Manager", "Task Switching"]:
            return

        # Check if the active window is NOT the main Notepad window
        # Notepad titles usually contain " - Notepad" (e.g., "Untitled - Notepad")
        # Exact "Notepad" title is typically a dialog (Error, Save prompt, About)
        is_main_notepad = " - Notepad" in active_window.title
        
        if not is_main_notepad:
            print(f"[WARN] Unexpected active window detected: '{active_window.title}'")
            
            # Attempt to bring Notepad back to focus first
            # The user might have just switched windows (Alt+Tab)
            notepad_windows = gw.getWindowsWithTitle(" - Notepad")
            if notepad_windows:
                print("Notepad window found in background. Attempting to switch back...")
                try:
                    notepad_windows[0].activate()
                    sleep(0.5)
                    if " - Notepad" in gw.getActiveWindow().title:
                        print("[INFO] Successfully switched back to Notepad.")
                        return
                except Exception as e:
                    print(f"Could not activate Notepad directly (might be blocked by dialog): {e}")

            # Special handling for "Notepad" dialogs (likely "Do you want to save?" or errors)
            if active_window.title == "Notepad":
                print("Likely 'Do you want to save?' dialog. Attempting 'Don't Save' (Alt+N)...")
                bot.type_keys(["alt", "n"])
                sleep(1)
                
                # Check if gone
                active_window = gw.getActiveWindow()
                if not active_window or " - Notepad" in active_window.title:
                    print("[INFO] Successfully dismissed 'Notepad' dialog.")
                    return

            # Try to interact with it to bypass/close
            # Strategy 1: Press Enter (Common for "OK", "Yes", "Save", "Confirm")
            print("Attempting to bypass with Enter...")
            bot.key_enter()
            sleep(1)
            
            # Check if still stuck on a non-Notepad window
            active_window = gw.getActiveWindow()
            is_main_notepad = active_window and (" - Notepad" in active_window.title)
            
            if not is_main_notepad:
                # Strategy 2: Press Esc (Common for "Cancel", "Close")
                print("Enter failed. Attempting to dismiss with Esc...")
                bot.key_esc()
                sleep(1)
                
            # Verify if we are back to Notepad
            active_window = gw.getActiveWindow()
            if active_window and (" - Notepad" in active_window.title):
                print("[INFO] Successfully returned focus to Notepad.")
            else:
                print("[ERROR] Failed to dismiss unexpected dialog. Manual intervention may be required.")
                
    except Exception as e:
        print(f"[ERROR] Error handling dialogs: {e}")
