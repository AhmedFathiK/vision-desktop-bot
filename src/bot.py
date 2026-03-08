from botcity.core import DesktopBot
from api import get_posts
from utils import get_resource_path
import pygetwindow as gw
import os
from time import sleep

class NotepadBot(DesktopBot):

    def start(self):
            self.open_notepad()
            posts = get_posts()[:5]
            for post in posts:
                self.write_post(post)
                self.save_post(post)
                self.close_notepad()
                break
    def open_notepad(self):
        self.load_images()
        self.show_desktop()

        #this is to force using medium icons on desktop
        self.type_keys(["ctrl", "shift", "3"])
        

        #loop through all notepad icons (priorating medium icon), in case the above keys failed
        notepad_icons = ("notepad_medium", "notepad_small", "notepad_large")
        for notepad_icon in notepad_icons:
            notepad = self.find(notepad_icon, matching=0.97, waiting_time=3000)
            if notepad:
                self.click(clicks=2)
                break
        if not notepad: #if notepad not found, try to open it using run command
            self.type_keys(["win", "r"])
            self.type_keys("notepad")
            self.key_enter()

    def close_notepad(self):
        self.get_notepad_window()
        self.type_keys(["ctrl", "shift", "w"])

    def load_images(self):
        images_path = get_resource_path("images")
        self.add_image("notepad_small", os.path.join(images_path, "notepad-small.png"))
        self.add_image("notepad_medium", os.path.join(images_path, "notepad-medium.png"))
        self.add_image("notepad_large", os.path.join(images_path, "notepad-large.png"))

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
        sleep(3)
        self.paste(os.path.join(self.get_target_folder(), f"post_{post['id']}.txt"))
        self.key_enter()

    def get_target_folder(self):
        folder = os.path.join(os.path.expanduser("~"), "Desktop", "tjm-project")
        os.makedirs(folder, exist_ok=True)
        return folder