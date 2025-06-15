from typing import List

import customtkinter as ctk


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("400x220")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        values = ["value 1", "value 2", "value 3", "value 4", "value 5", "value 6"]
        self.scrollable_checkbox_frame = MyScrollableCheckboxFrame(
            self, title="Values", values=values
        )
        self.scrollable_checkbox_frame.grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="nsew"
        )

        self.button = ctk.CTkButton(
            self, text="my button", command=self.button_callback
        )
        self.button.grid(row=3, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

    def button_callback(self):
        print("checkbox_frame:", self.scrollable_checkbox_frame.get())


class MyScrollableCheckboxFrame(ctk.CTkScrollableFrame):
    def __init__(self, master: App, values: List[str], title: str):
        super().__init__(master, label_text=title)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title
        self.checkboxes = []

        for i, value in enumerate(self.values):
            checkbox = ctk.CTkCheckBox(self, text=value)
            checkbox.grid(row=i + 1, column=0, padx=10, pady=(10, 0), sticky="w")
            self.checkboxes.append(checkbox)

    def get(self):
        checked_checkboxes = []
        for checkbox in self.checkboxes:
            if checkbox.get() == 1:  # If the box is checked...
                checked_checkboxes.append(checkbox.cget("text"))
        return checked_checkboxes


class MyRadiobuttonFrame(ctk.CTkFrame):
    def __init__(self, master, values, title):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title
        self.radiobuttons = []
        self.variable = ctk.StringVar(value="")

        self.title = ctk.CTkLabel(
            self, text=self.title, fg_color="gray30", corner_radius=0
        )

        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        for i, value in enumerate(self.values):
            radiobutton = ctk.CTkRadioButton(
                self, text=value, value=value, variable=self.variable
            )
            radiobutton.grid(row=i + 1, column=0, padx=10, pady=(10, 0), sticky="w")
            self.radiobuttons.append(radiobutton)

        def get(self):
            return self.variable.get()

        def set(self, value):
            self.variable.set(value)


app = App()
app.mainloop()
