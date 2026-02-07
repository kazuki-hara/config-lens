import os
import customtkinter
from pathlib import Path
from services.cisco_config import CiscoConfigService

class MainWindow(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Config Lens")
        self.geometry("800x600")
        # Additional UI setup can be done here
        self.setup_ui()

    def setup_ui(self):
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.button = customtkinter.CTkButton(
            master=self,
            text="Load Current running-config",
            command=self.button_load_running_config
        )
        self.button.place(x=100, y=100)

    def button_load_running_config(self):
        print("Load Current running-config button clicked")
        file_path = MainWindow.read_file_path()
        print(f"Selected file path: {file_path}")
        cisco_service = CiscoConfigService()
        config = cisco_service.read_config(file_path)
        print(f"Loaded config: {config}")

    @staticmethod
    def read_file_path() -> Path:
        current_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = customtkinter.filedialog.askopenfilename(initialdir=current_dir)
        return Path(file_path)

