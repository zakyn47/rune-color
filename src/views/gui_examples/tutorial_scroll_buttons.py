from typing import List

import customtkinter as ctk


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dynamic Button List")
        self.geometry("200x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        button_names = [
            "Button 1",
            "Button 2",
            "Button 3",
            "Button 4",
            "Button 5",
            "Button 6",
            "7",
            "8",
            "9",
            "10",
        ]
        self.scrollable_button_frame = MyScrollableButtonFrame(
            self, title="Dynamic Buttons", button_names=button_names
        )
        self.scrollable_button_frame.grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="nsew"
        )

    def button_callback(self, button_name):
        print(f"{button_name} clicked")


class MyScrollableButtonFrame(ctk.CTkScrollableFrame):
    def __init__(self, master: App, button_names: List[str], title: str):
        super().__init__(master, label_text=title)
        self.grid_columnconfigure(0, weight=1)
        self.button_names = button_names
        self.title = title
        self.buttons = []

        # Create buttons dynamically based on the provided list of button names
        for i, button_name in enumerate(self.button_names):
            button = ctk.CTkButton(
                self,
                text=button_name,
                command=lambda name=button_name: master.button_callback(name),
            )
            button.grid(row=i + 1, column=0, padx=10, pady=(10, 0), sticky="ew")
            self.buttons.append(button)


app = App()
app.mainloop()
