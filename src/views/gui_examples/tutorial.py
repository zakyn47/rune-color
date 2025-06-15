import customtkinter as ctk


def button_callback():
    print("button pressed")


def checkbox_callback():
    print("checkbox pressed")


# 1. -----------------------------------------------------------------------------------
if False:
    app = ctk.CTk()
    app.mainloop()


# 2. -----------------------------------------------------------------------------------
if False:
    app = ctk.CTk()
    app.title("my app")
    app.geometry("400x150")
    button = ctk.CTkButton(app, text="my button", command=button_callback)
    button.grid(row=0, column=0, padx=0, pady=0)

    app.mainloop()

# 3. -----------------------------------------------------------------------------------
if False:
    app = ctk.CTk()
    app.title("my app")
    app.geometry("400x150")
    app.grid_columnconfigure(0, weight=1)
    btn_home = ctk.CTkButton(app, text="home", command=button_callback)
    btn_home.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

    app.mainloop()

# 4. -----------------------------------------------------------------------------------
if False:
    PAD = 20
    PAD_TOP = 0
    PAD_BOT = PAD
    PADY = (PAD_TOP, PAD_BOT)
    app = ctk.CTk()
    app.title("my app")
    app.geometry("400x150")
    app.grid_columnconfigure((0, 1), weight=1)  # Equal weights means equally-spaced.

    btn_home = ctk.CTkButton(app, text="home", command=button_callback)
    btn_home.grid(row=0, column=0, padx=PAD, pady=PAD, sticky="ew", columnspan=2)

    chkbx_1 = ctk.CTkCheckBox(app, text="checkbox 1")
    chkbx_1.grid(row=1, column=0, padx=PAD, pady=PADY, sticky="w")
    chkbx_2 = ctk.CTkCheckBox(app, text="checkbox 2")
    chkbx_2.grid(row=1, column=1, padx=PAD, pady=PADY, sticky="w")

    app.mainloop()


# 4. -----------------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("my app")
        self.geometry("400x150")
        self.grid_columnconfigure((0, 1), weight=1)

        self.button = ctk.CTkButton(
            self, text="my button", command=self.button_callback
        )
        self.button.grid(row=0, column=0, padx=20, pady=20, sticky="ew", columnspan=2)
        self.checkbox_1 = ctk.CTkCheckBox(self, text="checkbox 1")
        self.checkbox_1.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        self.checkbox_2 = ctk.CTkCheckBox(self, text="checkbox 2")
        self.checkbox_2.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="w")

    def button_callback(self):
        print("button pressed")


app = App()
app.mainloop()
