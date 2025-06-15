from typing import List

import customtkinter as ctk


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("400x200")
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        self.checkbox_frame_1 = MyCheckboxFrame(self, ["wilbur", "gus", "mia"], "OGs")
        self.checkbox_frame_1.grid(
            row=0, column=0, padx=10, pady=(10, 0), sticky="nsew"
        )
        self.checkbox_frame_2 = MyCheckboxFrame(
            self, ["woody", "lucy", "cooper"], "Homies"
        )
        self.checkbox_frame_2.grid(
            row=0, column=1, padx=10, pady=(10, 0), sticky="nsew"
        )
        self.checkbox_frame_2.configure(fg_color="transparent")

        self.radiobutton_frame = MyRadiobuttonFrame(
            self, ["Solo", "Macy", "Azsa"], "Homies"
        )
        self.radiobutton_frame.grid(
            row=0, column=3, padx=10, pady=(10, 0), sticky="nsew"
        )

        self.button = ctk.CTkButton(
            self, text="my button", command=self.button_callback
        )
        self.button.grid(row=3, column=0, padx=10, pady=10, sticky="nsew", columnspan=4)

    def button_callback(self):
        print("button pressed")
        print("checked checkboxes left:", self.checkbox_frame_1.get())
        print("checked checkboxes right:", self.checkbox_frame_2.get())


class MyCheckboxFrame(ctk.CTkFrame):
    def __init__(self, master: App, values: List[str], title):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title
        self.checkboxes = []

        self.title = ctk.CTkLabel(
            self, text=self.title, fg_color="#FF0000", corner_radius=0
        )
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

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
