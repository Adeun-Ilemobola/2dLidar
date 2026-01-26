from ui.main_window import MainWindow
import customtkinter as ctk

def main():
    ctk.set_appearance_mode("dark")          
    ctk.set_default_color_theme("blue")     

    app = MainWindow(title="Pi Control Panel", size=(1000, 900))
    app.mainloop()

if __name__ == "__main__":
    main()
