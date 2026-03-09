from botcity.core import DesktopBot
from api import get_posts
from utils import get_resource_path
from dialogs import handle_dialogs
import pygetwindow as gw
import os
import time
from time import sleep

class NotepadBot(DesktopBot):

    def start(self):
        self.load_images()
        posts = get_posts()[:5]
        for post in posts:
            print(f"Processing post {post['id']}...")
            try:
                self.open_notepad()
                self.type_keys(["ctrl", "n"]) # Ensure new tab
                self.write_post(post)
                self.save_post(post)
            except Exception as e:
                print(f"[ERROR] Failed to process post {post['id']}: {e}")
            finally:
                self.close_notepad()
                
    def open_notepad(self):
        self.show_desktop()
        handle_dialogs(self) # Handle any potential dialogs that might block opening

        #this is to force using medium icons on desktop
        self.type_keys(["ctrl", "shift", "3"])
        

        #loop through all notepad icons (priorating medium icon), in case the above keys failed
        notepad_icons = ("notepad_medium", "notepad_small", "notepad_large")
        for notepad_icon in notepad_icons:
            notepad = self.find(notepad_icon, matching=0.97, waiting_time=3000)
            if notepad:
                self.move()
                self.click(clicks=2)
                break
        if not notepad: #if notepad not found, try to open it using run command
            self.type_keys(["win", "r"])
            self.type_keys("notepad")
            self.key_enter()
            
        # Validate that Notepad actually opened
        if not self.wait_for_notepad_window(timeout=10):
            raise Exception("Failed to open Notepad: Window not found within timeout.")

        handle_dialogs(self)
    def wait_for_notepad_window(self, timeout=10):
        """Wait for Notepad window to appear, handling potential error dialogs."""
        print("Waiting for Notepad to open...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            # Check for error dialogs first (e.g., "Cannot find the ... file")
            # These usually have the title "Notepad" and are small in size
            try:
                windows = gw.getWindowsWithTitle("Notepad")
                for window in windows:
                    # Heuristic: Error dialogs are typically small (height < 300) and have title "Notepad"
                    if window.title == "Notepad" and window.height < 300:
                        print(f"Dismissing error dialog: '{window.title}' (Size: {window.width}x{window.height})")
                        window.activate()
                        self.key_enter()
                        sleep(0.5)
            except Exception as e:
                print(f"Error handling potential dialog: {e}")

            # Now check for the main Notepad window
            main_windows = gw.getWindowsWithTitle(" - Notepad")
            if not main_windows:
                # Fallback: Check for windows titled "Notepad" that are likely the main window (larger size)
                candidates = gw.getWindowsWithTitle("Notepad")
                main_windows = [w for w in candidates if w.height >= 300]
            
            if main_windows:
                print(f"Notepad opened successfully: {main_windows[0].title}")
                try:
                    main_windows[0].activate()
                    return True
                except Exception as e:
                    print(f"Failed to activate main window: {e}")
            
            sleep(1)
        print("Timeout waiting for Notepad.")
        return False

    def close_notepad(self):
        """Close Notepad tabs one by one using Ctrl+W until the window is gone."""
        print("Closing Notepad tabs...")
        while True:
            # Check if Notepad is still open
            windows = gw.getWindowsWithTitle(" - Notepad")
            if not windows:
                break
            
            try:
                win = windows[0]
                win.activate()
                self.type_keys(["ctrl", "w"])
                sleep(0.5)
                # Delegate to the centralized dialog handler
                handle_dialogs(self)
            except Exception as e:
                print(f"Error closing tab: {e}")
                break

    def load_images(self):
        images_path = get_resource_path("images")
        self.add_image("notepad_small", os.path.join(images_path, "notepad-small.png"))
        self.add_image("notepad_medium", os.path.join(images_path, "notepad-medium.png"))
        self.add_image("notepad_large", os.path.join(images_path, "notepad-large.png"))
        self.add_image("cant_find_file_dialog_dark", os.path.join(images_path, "cant_find_file_dialog_dark.png"))
        self.add_image("cant_find_file_dialog_light", os.path.join(images_path, "cant_find_file_dialog_light.png"))

    def show_desktop(self):
        self.type_keys(["win", "d"])

    def get_notepad_window(self):
        # find window by title
        windows = gw.getWindowsWithTitle(" - Notepad")
        if windows:
            win = windows[0]
            win.activate()

    def write_post(self, post):
        self.get_notepad_window()
        self.paste(f"Title: {post['title']}")
        self.key_enter()
        self.key_enter()
        self.paste(post["body"])
        
    def save_post(self, post):
        self.get_notepad_window()
        self.type_keys(["ctrl", "shift", "s"])
        
        # Wait for "Save As" dialog to appear
        # Note: The dialog title is usually "Save As" in English Windows
        if not self.wait_for_window("Save As", timeout=5):
             print("[ERROR] 'Save As' dialog did not appear.")
             raise Exception("'Save As' dialog missing")

        # Ensure we are focused on the file name input
        self.paste(os.path.join(self.get_target_folder(), f"post_{post['id']}.txt"))
        self.key_enter()
        
        # Wait a moment for potential "Confirm Save As" dialog
        sleep(1)
        handle_dialogs(self) # This will handle confirm overwrite if exists using the modular handler

    def wait_for_window(self, title, timeout=10):
        """Wait for a window with specific title to appear."""
        print(f"Waiting for window '{title}'...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                print(f"Window '{title}' found.")
                windows[0].activate()
                return True
            sleep(0.5)
        print(f"Timeout waiting for window '{title}'.")
        return False

    def get_target_folder(self):
        folder = os.path.join(os.path.expanduser("~"), "Desktop", "tjm-project")
        os.makedirs(folder, exist_ok=True)
        return folder
