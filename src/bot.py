from botcity.core import DesktopBot
from api import get_posts
from utils import get_resource_path
from dialogs import handle_dialogs
import pygetwindow as gw
import os
import time
from time import sleep
import cv2
import numpy as np

class NotepadBot(DesktopBot):

    def start(self):
        self.load_images()
        # Create debug directory for annotated screenshots
        os.makedirs("debug_screenshots", exist_ok=True)
        
        posts = get_posts()[:10]
        for post in posts:
            print(f"Processing post {post['id']}...")
            try:
                self.open_notepad(post_id=post['id'])
                self.type_keys(["ctrl", "n"]) # Ensure new tab
                self.write_post(post)
                self.save_post(post)
            except Exception as e:
                print(f"[ERROR] Failed to process post {post['id']}: {e}")
            finally:
                self.close_notepad()
                
    def open_notepad(self, post_id=None):
        self.show_desktop()
        handle_dialogs(self) # Handle any potential dialogs that might block opening

        #this is to force using medium icons on desktop
        self.type_keys(["ctrl", "shift", "3"])
        

        #loop through all notepad icons (priorating medium icon), in case the above keys failed
        notepad_icons = ("notepad_medium", "notepad_small", "notepad_large")
        notepad = None
        
        # Retry logic: 3 attempts with 1s delay
        for attempt in range(1, 4):
            print(f"Searching for Notepad icon (Attempt {attempt}/3)...")
            for notepad_icon in notepad_icons:
                # Use short wait time since we are looping
                notepad = self.find(notepad_icon, matching=0.97, waiting_time=500)
                if notepad:
                    print(f"Icon found: {notepad_icon}")
                    
                    """ # --- DELIVERABLE: Annotated Screenshot ---
                    if post_id and attempt == 1: # Only save for the first success to avoid spam
                        #commented now for it is only for debugging
                        self.save_annotated_screenshot(notepad, f"post_{post_id}_icon_grounding.png")
                    # ----------------------------------------- """

                    self.move()
                    self.click(clicks=2)
                    break
            
            if notepad:
                break
            
            sleep(1) # 1s delay between attempts

        if not notepad: #if notepad not found, try to open it using run command
            print("[WARN] Icon not found after 3 attempts. Fallback to Run command.")
            self.type_keys(["win", "r"])
            self.type_keys("notepad")
            self.key_enter()
            
        # Validate that Notepad actually opened
        if not self.wait_for_notepad_window(timeout=10):
            raise Exception("Failed to open Notepad: Window not found within timeout.")

        handle_dialogs(self)

    def save_annotated_screenshot(self, region, filename):
        """Captures screen and draws a rectangle around the found region."""
        try:
            # Save raw screenshot
            raw_path = os.path.join("debug_screenshots", "temp_raw.png")
            self.save_screenshot(raw_path)
            
            # Load with OpenCV
            screenshot = cv2.imread(raw_path)
            if screenshot is None:
                print("[WARN] Failed to load screenshot for annotation.")
                return

            # Region is (left, top, width, height)
            x, y, w, h = region
            
            # Draw rectangle (Green, thickness 2)
            cv2.rectangle(screenshot, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text
            cv2.putText(screenshot, "Notepad Icon Grounded", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Save final
            path = os.path.join("debug_screenshots", filename)
            cv2.imwrite(path, screenshot)
            print(f"[DEBUG] Saved annotated screenshot to {path}")
            
            # Cleanup temp
            if os.path.exists(raw_path):
                os.remove(raw_path)
                
        except Exception as e:
            print(f"[WARN] Failed to save annotated screenshot: {e}")

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
