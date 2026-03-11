from botcity.core import DesktopBot
from .api import get_posts
from .utils import get_resource_path
from .dialogs import handle_dialogs
import pygetwindow as gw
import pyautogui
import os
import time
from time import sleep
import cv2
import numpy as np
import json
import logging
from google import genai
from google.genai import types

class NotepadBot(DesktopBot):

    def start(self):
        self.load_images()
        # Create debug directory for annotated screenshots
        os.makedirs("debug_screenshots", exist_ok=True)
        
        posts = get_posts()[:10]
        for post in posts:
            logging.info(f"Processing post {post['id']}...")
            try:
                self.open_notepad(post_id=post['id'])
                self.type_keys(["ctrl", "a"]) # Select all content
                self.type_keys(["backspace"]) # Clear content
                self.write_post(post)
                self.save_post(post)
            except Exception as e:
                logging.error(f"Failed to process post {post['id']}: {e}")
            finally:
                self.close_notepad()
                
    def find_icon_with_vlm(self, description: str):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        screenshot_path = os.path.join("debug_screenshots", "temp_vlm_query.png")
        try:
            self.save_screenshot(screenshot_path)
            
            client = genai.Client(api_key=api_key)

            with open(screenshot_path, "rb") as f:
                image_bytes = f.read()

            # ── STEP 1: PLANNER ── Ask where to search (coarse)
            planner_prompt = f"""You are analyzing a Windows desktop screenshot.
            I am looking for the icon labeled '{description}'.
            Describe which area of the screen it is in.
            Return ONLY a JSON with the search region:
            {{"x": <left>, "y": <top>, "w": <width>, "h": <height>}}
            Be generous — return a region at least 300x300 pixels that definitely contains the icon.
            Screen is 1920x1080."""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    planner_prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                ]
            )

            region = self._parse_json(response.text)
            if not region or region.get("x", -1) == -1:
                return None

            rx, ry, rw, rh = region["x"], region["y"], region["w"], region["h"]
            logging.info(f"[VLM] Planner identified search region: ({rx}, {ry}, {rw}, {rh})")

            # ── STEP 2: CROP the region
            img = cv2.imread(screenshot_path)
            # Clamp to screen bounds
            rx = max(0, rx); ry = max(0, ry)
            rw = min(rw, 1920 - rx); rh = min(rh, 1080 - ry)
            
            # Ensure we have a valid crop region
            if rw <= 0 or rh <= 0:
                logging.warning(f"Invalid crop region: {rx}, {ry}, {rw}, {rh}")
                return None
                
            crop = img[ry:ry+rh, rx:rx+rw]
            crop_path = os.path.join("debug_screenshots", "temp_vlm_crop.png")
            cv2.imwrite(crop_path, crop)

            # ── STEP 3: GROUNDER ── Find exact location in cropped image
            # Read back the cropped image bytes
            with open(crop_path, "rb") as f:
                crop_bytes = f.read()

            grounder_prompt = f"""Find the icon labeled '{description}' in this cropped screenshot.
            Return ONLY raw JSON, no markdown:
            {{"x": <left_pixel>, "y": <top_pixel>, "w": <width>, "h": <height>}}
            If not found: {{"x": -1, "y": -1, "w": 0, "h": 0}}
            Coordinates are relative to this cropped image."""

            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=[
                    grounder_prompt,
                    types.Part.from_bytes(data=crop_bytes, mime_type="image/png")
                ]
            )

            local = self._parse_json(response.text)
            if not local or local.get("x", -1) == -1:
                return None

            # ── STEP 4: Translate local coords back to screen coords
            screen_x = rx + local["x"]
            screen_y = ry + local["y"]
            logging.info(f"[VLM] Grounder found icon at local ({local['x']}, {local['y']}) -> screen ({screen_x}, {screen_y})")

            return (screen_x, screen_y, local["w"], local["h"])
            
        except Exception as e:
            logging.warning(f"VLM detection failed: {e}") 
            return None
        finally:
            for path in [screenshot_path, "debug_screenshots/temp_vlm_crop.png"]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

    def _parse_json(self, text: str):
        """Safely parse JSON from Gemini response, stripping markdown fences."""
        try:
            if not text: return None
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text.strip())
        except Exception as e:
            logging.warning(f"JSON parse failed: {e} - raw: {text!r}")
            return None

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
            logging.info(f"Searching for Notepad icon (Attempt {attempt}/3)...")
    
            # PRIMARY: VLM
            try:
                vlm_bbox = self.find_icon_with_vlm("Notepad.exe - Shortcut")
                if vlm_bbox:
                    logging.info(f"[VLM] Icon found at: {vlm_bbox}")
                    notepad = vlm_bbox
                    if post_id:
                        self.save_annotated_screenshot(notepad, f"post_{post_id}_icon_grounding.png")
                    
                    x, y, w, h = notepad
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # Use pyautogui for more reliable clicking
                    pyautogui.moveTo(center_x, center_y)
                    sleep(0.3)
                    pyautogui.doubleClick(center_x, center_y)
                    
                    logging.info(f"[VLM] Icon clicked at: {center_x}, {center_y}")
                    logging.info("Notepad opened via VLM Grounding")
                    self.mouse_move(500, 500)
            except Exception as e:
                logging.warning(f"VLM interaction failed: {e}")

            # FALLBACK: only run if VLM didn't find anything
            if not notepad:
                for notepad_icon in notepad_icons:
                    notepad = self.find(notepad_icon, matching=0.97, waiting_time=500)
                    if notepad:
                        logging.info(f"Icon found: {notepad_icon}")
                        if post_id:
                            self.save_annotated_screenshot(notepad, f"post_{post_id}_icon_grounding.png")
                        logging.info(f"Notepad opened via Template Matching: {notepad_icon}")
                        self.move()
                        self.click(clicks=2)
                        self.mouse_move(500, 500)
                        break

            if notepad:
                break
            
            sleep(1)

        if not notepad: #if notepad not found, try to open it using run command
            logging.warning("Icon not found after 3 attempts. Fallback to Run command.")
            logging.info("Notepad opened via Run Command (Fallback)")
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
            # Check if file already exists
            path = os.path.join("debug_screenshots", filename)
            if os.path.exists(path):
                logging.info(f"Screenshot {filename} already exists. Skipping.")
                return

            # Save raw screenshot
            raw_path = os.path.join("debug_screenshots", "temp_raw.png")
            self.save_screenshot(raw_path)
            
            # Load with OpenCV
            screenshot = cv2.imread(raw_path)
            if screenshot is None:
                logging.warning("Failed to load screenshot for annotation.")
                return

            # Region is (left, top, width, height)
            x, y, w, h = region
            
            # Draw rectangle (Green, thickness 2)
            cv2.rectangle(screenshot, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add text
            cv2.putText(screenshot, "Notepad Icon Grounded", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Save final
            # path is already defined above
            cv2.imwrite(path, screenshot)
            logging.debug(f"Saved annotated screenshot to {path}")
            
            # Cleanup temp
            if os.path.exists(raw_path):
                os.remove(raw_path)
                
        except Exception as e:
            logging.warning(f"Failed to save annotated screenshot: {e}")

    def wait_for_notepad_window(self, timeout=10):
        """Wait for Notepad window to appear, handling potential error dialogs."""
        logging.info("Waiting for Notepad to open...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            # Check for error dialogs first (e.g., "Cannot find the ... file")
            # These usually have the title "Notepad" and are small in size
            try:
                windows = gw.getWindowsWithTitle("Notepad")
                for window in windows:
                    # Heuristic: Error dialogs are typically small (height < 300) and have title "Notepad"
                    if window.title == "Notepad" and window.height < 300:
                        logging.info(f"Dismissing error dialog: '{window.title}' (Size: {window.width}x{window.height})")
                        window.activate()
                        self.key_enter()
                        sleep(0.5)
            except Exception as e:
                logging.error(f"Error handling potential dialog: {e}")

            # Now check for the main Notepad window
            main_windows = gw.getWindowsWithTitle(" - Notepad")
            if not main_windows:
                # Fallback: Check for windows titled "Notepad" that are likely the main window (larger size)
                candidates = gw.getWindowsWithTitle("Notepad")
                main_windows = [w for w in candidates if w.height >= 300]
            
            if main_windows:
                logging.info(f"Notepad opened successfully: {main_windows[0].title}")
                try:
                    main_windows[0].activate()
                    return True
                except Exception as e:
                    logging.warning(f"Failed to activate main window: {e}")
            
            sleep(1)
        logging.warning("Timeout waiting for Notepad.")
        return False

    def close_notepad(self):
        """Close Notepad tabs one by one using Ctrl+W until the window is gone."""
        logging.info("Closing Notepad tabs...")
        max_attempts = 10  # Safety break
        attempts = 0
        
        while attempts < max_attempts:
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
                # It handles "Do you want to save?" and other dialogs
                handle_dialogs(self)
                
            except Exception as e:
                logging.error(f"Error closing tab: {e}")
                sleep(1)
            
            attempts += 1
        
        if attempts >= max_attempts:
             logging.warning("Failed to close all Notepad tabs gracefully. Force killing process...")
             os.system("taskkill /f /im notepad.exe")

    def load_images(self):
        images_path = get_resource_path("images")
        self.add_image("notepad_small", os.path.join(images_path, "notepad-small.png"))
        self.add_image("notepad_medium", os.path.join(images_path, "notepad-medium.png"))
        self.add_image("notepad_large", os.path.join(images_path, "notepad-large.png"))
        self.add_image("cant_find_file_dialog_dark", os.path.join(images_path, "cant_find_file_dialog_dark.png"))
        self.add_image("cant_find_file_dialog_light", os.path.join(images_path, "cant_find_file_dialog_light.png"))

    def show_desktop(self):
        """Minimize all windows to show the desktop."""
        try:
            # Method 1: PyAutoGUI hotkey
            # Use 'win + m' (Minimize All) instead of 'win + d' (Show Desktop toggle)
            # 'win + d' can toggle windows back open if desktop is already shown.
            # 'win + m' is idempotent (safe to call multiple times).
            pyautogui.hotkey('win', 'm')
            sleep(1)
            
            # Method 2: Minimize all windows explicitly using pygetwindow as backup
            # This is helpful if 'win+m' fails
            # windows = gw.getAllWindows()
            # for win in windows:
            #     if not win.isMinimized and win.title:
            #         try:
            #             win.minimize()
            #         except:
            #             pass
            
            logging.info("Desktop shown.")
        except Exception as e:
            logging.warning(f"Failed to show desktop: {e}")

    def get_notepad_window(self):
        # find window by title
        windows = gw.getWindowsWithTitle(" - Notepad")
        if windows:
            win = windows[0]
            win.activate()

    def write_post(self, post):
        self.get_notepad_window()
        self.paste(f"Title: {post['title']}")
        sleep(0.5) # Wait for paste to complete
        
        # Re-focus before Enter to handle potential interruptions
        self.get_notepad_window()
        self.key_enter()
        sleep(0.5)
        self.key_enter()
        sleep(0.5)
        
        # Re-focus before Body paste to handle potential interruptions
        self.get_notepad_window()
        self.paste(post["body"])
        
    def save_post(self, post):
        self.get_notepad_window()
        self.type_keys(["ctrl", "shift", "s"])
        
        # Wait for "Save As" dialog to appear
        # Note: The dialog title is usually "Save As" in English Windows
        if not self.wait_for_window("Save As", timeout=5):
             logging.error("'Save As' dialog did not appear.")
             raise Exception("'Save As' dialog missing")

        # Ensure we are focused on the file name input
        self.paste(os.path.join(self.get_target_folder(), f"post_{post['id']}.txt"))
        sleep(0.5) # Wait for paste to complete

        # Ensure focus is still on Save As dialog before pressing Enter
        if self.wait_for_window("Save As", timeout=2):
            self.key_enter()
        else:
            logging.warning("'Save As' dialog lost focus or closed unexpectedly.")
        
        # Wait a moment for potential "Confirm Save As" dialog
        sleep(1)
        handle_dialogs(self) # This will handle confirm overwrite if exists using the modular handler

    def wait_for_window(self, title, timeout=10):
        """Wait for a window with specific title to appear."""
        logging.info(f"Waiting for window '{title}'...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                logging.info(f"Window '{title}' found.")
                windows[0].activate()
                return True
            sleep(0.5)
        logging.warning(f"Timeout waiting for window '{title}'.")
        return False

    def get_target_folder(self):
        folder = os.path.join(os.path.expanduser("~"), "Desktop", "tjm-project")
        os.makedirs(folder, exist_ok=True)
        return folder
