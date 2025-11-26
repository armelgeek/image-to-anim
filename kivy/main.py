# python core modules
import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
import sys
from threading import Thread

# kivy world
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDFlatButton, MDFloatingActionButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.dialog import MDDialog

from kivy.uix.videoplayer import VideoPlayer
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method

# IMPORTANT: Set this property for keyboard behavior
Window.softinput_mode = "below_target"

# Import your local screen classes & modules
from screens.divider import MyMDDivider
from sketchApi import get_split_lens, initiate_sketch, generate_svg_from_image_sketch
from kivg import Kivg

## Global definitions
__version__ = "0.2.2"
# Determine the base path for your application's resources
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_path = os.path.dirname(os.path.abspath(__file__))
kv_file_path = os.path.join(base_path, 'main_layout.kv')


# app class
class DlImg2SktchApp(MDApp):
    split_len = NumericProperty(10)
    frame_rate = NumericProperty(25)
    obj_skip_rate = NumericProperty(8)
    bck_skip_rate = NumericProperty(14)
    main_img_duration = NumericProperty(2)
    internal_storage = ObjectProperty()
    external_storage = ObjectProperty()
    video_dir = ObjectProperty()
    split_len_options = ObjectProperty()
    split_len_drp = ObjectProperty
    image_path = StringProperty("")
    vid_download_path = StringProperty("")
    is_cv2_running = ObjectProperty()
    animation_mode = StringProperty("Video")  # "Video" or "SVG Live"
    kivg_instance = ObjectProperty(None)  # Kivg instance for SVG animation
    is_svg_file = ObjectProperty(False)  # Track if uploaded file is SVG

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Orange"
        self.top_menu_items = {
            "Documentation": {
                "icon": "file-document-check",
                "action": "web",
                "url": "https://blog.daslearning.in/llm_ai/genai/image-to-animation.html",
            },
            "Contact Us": {
                "icon": "card-account-phone",
                "action": "web",
                "url": "https://daslearning.in/contact/",
            },
            "Check for update": {
                "icon": "github",
                "action": "update",
                "url": "",
            }
        }
        return Builder.load_file(kv_file_path)

    def on_start(self):

        # paths setup
        if platform == "android":
            from android.permissions import request_permissions, Permission
            sdk_version = 28
            try:
                VERSION = autoclass('android.os.Build$VERSION')
                sdk_version = VERSION.SDK_INT
                print(f"Android SDK: {sdk_version}")
                #self.show_toast_msg(f"Android SDK: {sdk_version}")
            except Exception as e:
                print(f"Could not check the android SDK version: {e}")
            if sdk_version >= 33:  # Android 13+
                permissions = [Permission.READ_MEDIA_IMAGES]
            else:  # Android 9–12
                permissions = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            request_permissions(permissions)
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            android_path = context.getExternalFilesDir(None).getAbsolutePath()
            self.video_dir = os.path.join(android_path, 'generated')
            image_dir = os.path.join(android_path, 'images')
            os.makedirs(image_dir, exist_ok=True)
            self.internal_storage = android_path
            try:
                Environment = autoclass("android.os.Environment")
                self.external_storage = Environment.getExternalStorageDirectory().getAbsolutePath()
            except Exception:
                self.external_storage = os.path.abspath("/storage/emulated/0/")
        else:
            self.internal_storage = os.path.abspath("/")
            self.external_storage = os.path.abspath("/")
            self.video_dir = os.path.join(self.user_data_dir, 'generated')
        os.makedirs(self.video_dir, exist_ok=True)
        test_file = os.path.join(self.video_dir, "test.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("Test write")
            print(f"Successfully wrote to {test_file}")
            os.remove(test_file)  # Clean up
        except Exception as e:
            print(f"Failed to write to {test_file}: {e}")

        # file managers
        self.is_img_manager_open = False
        self.img_file_manager = MDFileManager(
            exit_manager=self.img_file_exit_manager,
            select_path=self.select_img_path,
            ext=[".png", ".jpg", ".jpeg", ".webp", ".svg"],  # Added SVG support
            selector="file",  # Restrict to selecting files only
            preview=True,
            #show_hidden_files=True,
        )
        self.is_vid_manager_open = False
        self.vid_file_manager = MDFileManager(
            exit_manager=self.vid_file_exit_manager,
            select_path=self.select_vid_path,
            selector="folder",  # Restrict to selecting directories only
        )

        # Menu items
        self.split_len_drp = self.root.ids.split_len_drp
        menu_items = []
        self.split_len_options = MDDropdownMenu(
            md_bg_color="#bdc6b0",
            caller=self.split_len_drp,
            items=menu_items,
        )
        # top menu
        menu_items = [
            {
                "text": menu_key,
                "leading_icon": self.top_menu_items[menu_key]["icon"],
                "on_release": lambda x=menu_key: self.top_menu_callback(x),
                "font_size": sp(36)
            } for menu_key in self.top_menu_items
        ]
        self.menu = MDDropdownMenu(
            items=menu_items,
            width_mult=4,
        )

    def menu_bar_callback(self, button):
        self.menu.caller = button
        self.menu.open()

    def top_menu_callback(self, text_item):
        self.menu.dismiss()
        action = ""
        url = ""
        try:
            action = self.top_menu_items[text_item]["action"]
            url = self.top_menu_items[text_item]["url"]
        except Exception as e:
            print(f"Erro in menu process: {e}")
        if action == "web" and url != "":
            self.open_link(url)
        elif action == "update":
            buttons = [
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.txt_dialog_closer
                ),
                MDFlatButton(
                    text="Releases",
                    theme_text_color="Custom",
                    text_color="green",
                    on_release=self.update_checker
                ),
            ]
            self.show_text_dialog(
                "Check for update",
                f"Your version: {__version__}",
                buttons
            )

    def show_toast_msg(self, message, is_error=False):
        from kivymd.uix.snackbar import MDSnackbar
        bg_color = (0.2, 0.6, 0.2, 1) if not is_error else (0.8, 0.2, 0.2, 1)
        MDSnackbar(
            MDLabel(
                text = message,
                font_style = "Subtitle1"
            ),
            md_bg_color=bg_color,
            y=dp(24),
            pos_hint={"center_x": 0.5},
            duration=3
        ).open()

    def show_text_dialog(self, title, text="", buttons=[]):
        self.txt_dialog = MDDialog(
            title=title,
            text=text,
            buttons=buttons
        )
        self.txt_dialog.open()

    def set_split_len(self, value):
        self.split_len = int(value)
        self.split_len_drp.text = str(self.split_len)
        self.split_len_options.dismiss()

    def open_img_file_manager(self):
        """Open the file manager to select an image file. On android use Downloads or Pictures folders only"""
        try:
            self.img_file_manager.show(self.external_storage)  # external storage
            self.is_img_manager_open = True
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def open_vid_file_manager(self, instance):
        """Open the file manager to select destination folder. On android use Downloads or Videos folders only"""
        try:
            self.vid_file_manager.show(self.external_storage)
            self.is_vid_manager_open = True
        except Exception as e:
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def select_img_path(self, path: str):
        """Handle image/SVG file selection with validation"""
        import os
        
        # Validate file exists and is a regular file
        if not os.path.exists(path):
            self.show_toast_msg("File does not exist", is_error=True)
            return
        
        if not os.path.isfile(path):
            self.show_toast_msg("Path is not a file", is_error=True)
            return
        
        # Validate file extension
        valid_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.svg']
        file_ext = os.path.splitext(path)[1].lower()
        if file_ext not in valid_extensions:
            self.show_toast_msg(f"Unsupported file type: {file_ext}", is_error=True)
            return
        
        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = os.path.getsize(path)
        if file_size > max_size:
            self.show_toast_msg("File too large (max 50MB)", is_error=True)
            return
        
        self.image_path = path
        
        # Check if the file is an SVG
        if path.lower().endswith('.svg'):
            self.is_svg_file = True
            # For SVG files, show file info and skip split_lens calculation
            filename = os.path.basename(path)
            img_box = self.root.ids.img_selector_lbl
            img_box.text = f"{filename} (SVG, {file_size} bytes)"
            
            # For SVG, we don't need split_len options
            self.split_len_options = MDDropdownMenu(
                md_bg_color="#bdc6b0",
                caller=self.split_len_drp,
                items=[],
            )
            self.split_len_drp.text = "N/A"
            
            self.show_toast_msg(f"Selected SVG file: {filename}")
            self.img_file_exit_manager()
            
            # Auto-switch to SVG Live mode if an SVG is uploaded
            try:
                segmented_control = self.root.ids.animation_mode
                for item in segmented_control.children:
                    if hasattr(item, 'text') and item.text == "SVG Live":
                        item.active = True
                        self.animation_mode = "SVG Live"
                        self.show_toast_msg("Switched to SVG Live mode")
                        break
            except Exception as e:
                print(f"Error switching mode: {e}")
        else:
            # Regular image file
            self.is_svg_file = False
            api_resp = get_split_lens(path)
            split_lens = api_resp["split_lens"]
            image_details = api_resp["image_res"]
            img_box = self.root.ids.img_selector_lbl
            img_box.text = f"{image_details}"
            menu_items = [
                {
                    "text": f"{option}",
                    "on_release": lambda x=f"{option}": self.set_split_len(x),
                    "font_size": sp(24)
                } for option in split_lens
            ]
            self.split_len_options = MDDropdownMenu(
                md_bg_color="#bdc6b0",
                caller=self.split_len_drp,
                items=menu_items,
            )
            if len(split_lens) >= 1:
                if 10 in split_lens:
                    self.split_len = 10
                else:
                    self.split_len = split_lens[0]
            else:
                self.split_len = 1
            self.split_len_drp.text = str(self.split_len)
            print(f"Initial split len: {self.split_len}")
            self.show_toast_msg(f"Selected image: {path}")
            self.img_file_exit_manager()

    def select_vid_path(self, path: str):
        """
        Called when a directory is selected. Save the Video file.
        """
        import shutil
        filename = os.path.basename(self.vid_download_path)
        chosen_path = os.path.join(path, filename) # destination path
        try:
            shutil.copyfile(self.vid_download_path, chosen_path)
            print(f"File successfully download to: {chosen_path}")
            self.show_toast_msg(f"File download to: {chosen_path}")
            self.vid_file_exit_manager()
            os.remove(self.vid_download_path)
            self.vid_download_path = ""
            player_box = self.root.ids.player_box
            player_box.clear_widgets()
        except Exception as e:
            print(f"Error saving file: {e}")
            self.show_toast_msg(f"Error saving file: {e}", is_error=True)

    def img_file_exit_manager(self, *args):
        """Called when the user reaches the root of the directory tree."""
        self.is_img_manager_open = False
        self.img_file_manager.close()

    def vid_file_exit_manager(self, *args):
        """Called when the user reaches the root of the directory tree."""
        self.is_vid_manager_open = False
        self.vid_file_manager.close()

    def on_animation_mode_change(self):
        """Handle animation mode change from UI"""
        try:
            # Get active segment control item
            segmented_control = self.root.ids.animation_mode
            for item in segmented_control.children:
                if hasattr(item, 'active') and item.active:
                    self.animation_mode = item.text
                    self.show_toast_msg(f"Animation mode: {self.animation_mode}")
                    break
        except Exception as e:
            print(f"Error changing animation mode: {e}")

    def submit_sketch_req(self):
        if self.image_path == "":
            self.show_toast_msg("No image is selected", is_error=True)
            return
        if self.is_cv2_running:
            self.show_toast_msg("Please wait for the previous request to finish", is_error=True)
            return
        
        # Check if SVG file is being used with Video mode
        if self.is_svg_file and self.animation_mode == "Video":
            self.show_toast_msg("SVG files can only be used in SVG Live mode. Switching mode...", is_error=True)
            # Auto-switch to SVG Live mode
            try:
                segmented_control = self.root.ids.animation_mode
                for item in segmented_control.children:
                    if hasattr(item, 'text') and item.text == "SVG Live":
                        item.active = True
                        self.animation_mode = "SVG Live"
                        break
            except Exception as e:
                print(f"Error switching mode: {e}")
            return
        
        # Check animation mode
        if self.animation_mode == "SVG Live":
            self.submit_svg_animation()
        else:
            self.submit_video_animation()

    def submit_video_animation(self):
        """Original video-based animation"""
        split_len = self.split_len
        frame_rate = self.root.ids.frame_rate.text if self.root.ids.frame_rate.text != "" else self.frame_rate
        obj_skip_rate = self.root.ids.obj_skip_rate.text if self.root.ids.obj_skip_rate.text != "" else self.obj_skip_rate
        bck_skip_rate = self.root.ids.bck_skip_rate.text if self.root.ids.bck_skip_rate.text != "" else self.bck_skip_rate
        main_img_duration = self.root.ids.main_img_duration.text if self.root.ids.main_img_duration.text != "" else self.main_img_duration
        sketch_thread = Thread(target=initiate_sketch, args=(self.image_path, split_len, int(frame_rate), int(obj_skip_rate), int(bck_skip_rate), int(main_img_duration), self.task_complete_callback, self.video_dir, platform), daemon=True)
        sketch_thread.start()
        self.is_cv2_running = True
        player_box = self.root.ids.player_box
        player_box.clear_widgets()
        player_box.add_widget(MDSpinner(
            size_hint = [None, None],
            size = (dp(32), dp(32)),
            active = True,
            pos_hint={'center_x': .5, 'center_y': .5}
        ))

    def submit_svg_animation(self):
        """SVG-based live animation using kivg"""
        from kivy.uix.widget import Widget
        import datetime
        
        try:
            # Show spinner while preparing animation
            player_box = self.root.ids.player_box
            player_box.clear_widgets()
            spinner = MDSpinner(
                size_hint = [None, None],
                size = (dp(32), dp(32)),
                active = True,
                pos_hint={'center_x': .5, 'center_y': .5}
            )
            player_box.add_widget(spinner)
            
            # Check if it's already an SVG file
            if self.is_svg_file:
                # Direct SVG file - animate it directly
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self._start_svg_animation(self.image_path, player_box), 0)
                self.show_toast_msg("Loading SVG animation...")
            else:
                # Image file - generate SVG first
                split_len = self.split_len
                
                # Generate SVG in a thread
                svg_thread = Thread(
                    target=self._generate_and_animate_svg, 
                    args=(self.image_path, split_len, player_box),
                    daemon=True
                )
                svg_thread.start()
                self.is_cv2_running = True
            
        except Exception as e:
            print(f"Error in SVG animation: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast_msg(f"Error: {e}", is_error=True)

    def _generate_and_animate_svg(self, image_path, split_len, player_box):
        """Generate SVG and schedule animation on main thread"""
        import datetime
        from kivy.clock import Clock
        
        try:
            # Generate SVG file path
            now = datetime.datetime.now()
            current_time = str(now.strftime("%H%M%S"))
            current_date = str(now.strftime("%Y%m%d"))
            svg_filename = f"sketch_{current_date}_{current_time}.svg"
            svg_path = os.path.join(self.video_dir, svg_filename)
            
            # Generate SVG using sketchApi (which uses the same algorithm as video generation)
            result = generate_svg_from_image_sketch(
                image_path=image_path,
                split_len=split_len,
                output_path=svg_path
            )
            
            if result["status"]:
                # Schedule animation on main thread
                Clock.schedule_once(lambda dt: self._start_svg_animation(svg_path, player_box), 0)
            else:
                # Show error
                Clock.schedule_once(lambda dt: self.show_toast_msg(result["message"], is_error=True), 0)
                Clock.schedule_once(lambda dt: setattr(self, 'is_cv2_running', False), 0)
            
        except Exception as e:
            print(f"Error generating SVG: {e}")
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.show_toast_msg(f"Error: {e}", is_error=True), 0)
            Clock.schedule_once(lambda dt: setattr(self, 'is_cv2_running', False), 0)

    def _start_svg_animation(self, svg_path, player_box):
        """Start SVG animation on the main thread with validation"""
        from kivy.uix.widget import Widget
        import os
        
        try:
            # Validate SVG file before animation
            if not os.path.exists(svg_path):
                self.show_toast_msg("SVG file not found", is_error=True)
                self.is_cv2_running = False
                return
            
            if not os.path.isfile(svg_path):
                self.show_toast_msg("Invalid SVG path", is_error=True)
                self.is_cv2_running = False
                return
            
            # Validate file size (max 10MB for SVG to prevent resource exhaustion)
            max_svg_size = 10 * 1024 * 1024  # 10MB
            svg_size = os.path.getsize(svg_path)
            if svg_size > max_svg_size:
                self.show_toast_msg("SVG file too large for animation (max 10MB)", is_error=True)
                self.is_cv2_running = False
                return
            
            # Basic SVG content validation
            try:
                with open(svg_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024)  # Read first 1KB
                    if not content.strip().startswith('<?xml') and '<svg' not in content:
                        self.show_toast_msg("Invalid SVG file format", is_error=True)
                        self.is_cv2_running = False
                        return
            except Exception as e:
                self.show_toast_msg(f"Error reading SVG: {e}", is_error=True)
                self.is_cv2_running = False
                return
            
            # Clear player box
            player_box.clear_widgets()
            
            # Create a widget for SVG drawing
            svg_widget = Widget()
            player_box.add_widget(svg_widget)
            
            # Create Kivg instance and draw with animation
            self.kivg_instance = Kivg(svg_widget)
            self.kivg_instance.draw(
                svg_path,
                animate=True,
                anim_type="seq",
                fill=True,
                line_width=2,
                line_color=[0, 0, 0, 1],
                dur=0.01,
                show_hand=True
            )
            
            self.is_cv2_running = False
            self.show_toast_msg("SVG animation started!")
            
        except Exception as e:
            print(f"Error starting SVG animation: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast_msg(f"Error: {e}", is_error=True)
            self.is_cv2_running = False

    def task_complete_callback(self, result):
        status = result["status"]
        player_box = self.root.ids.player_box
        message = result["message"]
        self.is_cv2_running = False
        if status is True:
            self.vid_download_path = message
            self.show_toast_msg(f"Video generated at: {message}")
            player_box.clear_widgets()
            player = VideoPlayer(
                source = message,
                options={'fit_mode': 'contain'}
            )
            down_btn = MDFloatingActionButton(
                icon="download",
                type="small",
                theme_icon_color="Custom",
                md_bg_color='#e9dff7',
                icon_color='#211c29',
            )
            player_box.add_widget(player)
            down_btn.bind(on_release=self.open_vid_file_manager)
            player_box.add_widget(down_btn)
            player.state = 'play'
        else:
            self.show_toast_msg(message, is_error=True)

    def reset_all(self):
        img_selector_lbl = self.root.ids.img_selector_lbl
        frame_rate = self.root.ids.frame_rate
        obj_skip_rate = self.root.ids.obj_skip_rate
        bck_skip_rate = self.root.ids.bck_skip_rate
        main_img_duration = self.root.ids.main_img_duration
        # start reset
        self.image_path = ""
        self.is_svg_file = False
        self.split_len = 10
        menu_items = []
        self.split_len_options = MDDropdownMenu(
            md_bg_color="#bdc6b0",
            caller=self.split_len_drp,
            items=menu_items,
        )
        self.split_len_drp.text = "speed"
        img_selector_lbl.text = "Select an image or SVG file >"
        frame_rate.text = "25"
        obj_skip_rate.text = "8"
        bck_skip_rate.text = "14"
        main_img_duration.text = "2"

    def events(self, instance, keyboard, keycode, text, modifiers):
        """Handle mobile device button presses (e.g., Android back button)."""
        if keyboard in (1001, 27):  # Android back button or equivalent
            if self.is_img_manager_open:
                # Check if we are at the root of the directory tree
                if self.img_file_manager.current_path == self.external_storage:
                    self.show_toast_msg(f"Closing file manager from main storage")
                    self.img_file_exit_manager()
                else:
                    self.img_file_manager.back()  # Navigate back within file manager
                return True  # Consume the event to prevent app exit
            if self.is_vid_manager_open:
                # Check if we are at the root of the directory tree
                if self.vid_file_manager.current_path == self.external_storage:
                    self.show_toast_msg(f"Closing file manager from main storage")
                    self.vid_file_exit_manager()
                else:
                    self.vid_file_manager.back()  # Navigate back within file manager
                return True  # Consume the event to prevent app exit
        return False

    def txt_dialog_closer(self, instance):
        self.txt_dialog.dismiss()

    def update_checker(self, instance):
        self.txt_dialog.dismiss()
        self.open_link("https://github.com/daslearning-org/image-to-animation-offline/releases")

    def open_demo_video(self):
        self.open_link("https://youtu.be/_UuAIjSzUJQ")

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

if __name__ == '__main__':
    DlImg2SktchApp().run()
