<p align="center">
  <img src="../img/website/wiki-logo.png" alt="logo" height="300"/>
</p>

# Runecolor Wiki<!-- omit in toc -->

<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [1. General FAQ](#1-general-faq)
- [2. Architecture](#2-architecture)
  - [2.1 Design Pattern](#21-design-pattern)
  - [2.2 Core Classes](#22-core-classes)
- [3. Quickstart ](#3-quickstart-)
  - [3.1 Creating a Bot](#31-creating-a-bot)
  - [3.2 Testing a Bot Without the UI](#32-testing-a-bot-without-the-ui)
- [4. Packaging](#4-packaging)

<!-- TOC end -->

<!-- TOC --><a name="1-general-faq"></a>
# 1. General FAQ
1. **What is Runecolor?**
    - Runecolor is a desktop client for managing automation scripts in oldschool runescape.
    - Built on top of [OS-Bot-COLOR](https://github.com/kelltom/OS-Bot-COLOR) and [runedark](https://github.com/cemenenkoff/runedark-public)
    - Kinda playground for me to learn programming.
2. **Is Runecolor safe?**
    - As a rule, it's best to review a developer's code or scan any executable file you receive for viruses before running it to ensure you're using safe software.
3. **What are the general approaches to gaming software automation?**
    - There are three general types:
        - ***Injection***: Injects unauthorized code into the game, similar to jailbreaking a phone.
        - ***Reflection***: Uses external applications to read game memory and make decisions.
          - ***Example***: If memory at `0x7FFE0300B8C0` drops below 50, a bot could instruct a character to drink a potion.
        - ***Color***: Reads pixel colors on the screen to make decisions without accessing game code.
4. **Why is color botting the safest approach?**
    - Color bots don't alter game code directly; they rely solely on screen visuals, making them harder to detect.
5. **How are injection methods detected?**
    - Game servers inspect data packets for irregularities.
        - **Analogy**: A unique scuff mark on boxes shows authenticity; a missing or altered mark raises suspicion.
6. **How are reflection methods detected?**
    - Servers flag actions that wouldn't be possible through the standard UI.
        - **Example**: A bot detects a potion in the inventory and drinks it even if the inventory tab isn't open, which a human player couldn't do without switching views.
7. **How was Runecolor built?**
    - Runecolor's core uses [`MSS`](https://python-mss.readthedocs.io/) and [`OpenCV`](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html).
    - It was developed and tested on Windows.
8.  **Can I be banned for using Runecolor?**
    - Sure you can, and probably will.
9.  **Is it safe to bot on my main account?**
    - No.

<!-- TOC --><a name="2-architecture"></a>
# 2. Architecture
<!-- TOC --><a name="21-design-pattern"></a>
## 2.1 Design Pattern
- The core of Runecolor is designed using the [Model-View-Controller (MVC)](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) pattern.
- This pattern is used to separate the application's *logic* from its *presentation*. In this app:
  - ***Models*** refer to bots (their properties, functions, etc.).
  - ***Views*** refer to the user interface (the buttons, text, etc.).
  - A ***Controller*** handles communication between these two layers.
<p align="center">
  <img src="../img/website/mvc-process.svg" width="600"/>
</p>

<!-- TOC --><a name="22-core-classes"></a>
## 2.2 Core Classes
- [`RuneLiteBot`](../model/runelite_bot.py)
  - Derived from the base [`Bot`](../model/bot.py), this class contains the general utility functions shared by all bots that interface with RuneLite.
- [`RuneLiteWindow`](../model/runelite_window.py)
  - Derived from the base [`Window`](../model/window.py), this class tailors window references to the idiosyncrasies of RuneLite.
- [`RuneLiteObject`](../utilities/geometry.py#L230)
  - This class represents an object on the screen, bounded by a [`Rectangle`](../utilities/geometry.py#L16)
  - Note that the bounding [`Rectangle`](../utilities/geometry.py#L16) for a [`RuneLiteObject`](../utilities/geometry.py#L230) is contained within a larger reference [`Rectangle`](../utilities/geometry.py#L16) (i.e. the entire screen).
```swift
    (0, 0) ---- Main Monitor Screen Area ------- + ---------------- +
        |                                        |                  |
        |                                        |                  |
        |                                        | top              |
        |                                        |                  |
        |                                        |                  |
        |-----left-- + ----- Rectangle --------- +                  |
        |            |                           |                  |
        |            |                           |                  |
        |            |  + -- RuneLiteObject -- + |                  |
        |            |  |                      | | height           |
        |            |  |                      | |                  |
        |            |  |                      | |                  |
        |            |  + -------------------- + |                  |
        |            + --------- width --------- +                  |
        |                                                           |
        |                                                           |
        + --------------------------------------------------------- +
```
  - Note that this coordinate system is defined with the origin in the upper *left* corner.
  - This is because right-handed click-and-drag operations usually occur from a click in the upper-left corner of the screen that then drags down to the lower-right corner.

<!-- TOC --><a name="3-quickstart"></a>
# 3. Quickstart <img height=20 src="../img/website/windows-logo.png"/>
1. Install [Python 3.10](https://www.python.org/downloads/release/python-3109/).
2. Install [Git Bash for Windows](https://git-scm.com/downloads).
3. Open an IDE (e.g. [VS Code](https://code.visualstudio.com/)).
4. Clone this repository.
5. Set up a virtual environment.
   1. Create a virtual environment: `py -3.10 -m venv venv`
   2. Activate the newly-created virtual environment: `venv/Scripts/activate`
   3. Install dependencies: `pip install -r requirements.txt`
6. Run: `python src/runecolor.py`


<!-- TOC --><a name="31-creating-a-bot"></a>
## 3.1 Creating a Bot
- First, check out the existing [base template](../model/osrs/template.py).
- Then, see one of the basic bots and emulate its implementation.

<!-- TOC --><a name="32-testing-a-bot-without-the-ui"></a>
## 3.2 Testing a Bot Without the UI
- Ensure default settings are hard-coded in the bot's `__init__` method (its constructor).
- Then, see the [final few lines in `src/runecolor.py`](../rune_dark.py#L633) and change them appropriately.

<!-- TOC --><a name="4-packaging"></a>
# 4. Packaging
- Compiling builds (i.e. compiling `src/runecolor.py` into an executable) can be done with these approaches:
  - [Pyinstaller](https://customtkinter.tomschimansky.com/documentation/packaging)
    - This method is not secure, as source code and assets are stored in temp files during execution.
    - Using the [`auto-py-to-exe`](https://pypi.org/project/auto-py-to-exe/) GUI makes this process easier.
  - [Nuitka](https://github.com/Nuitka/Nuitka)
    - This method is far more secure and modern, but build times are significant.
    - The standard command to compile a version of Runecolor is:
      - `python -m nuitka --onefile --follow-imports --enable-plugin=tk-inter --enable-plugin=no-qt src/runecolor.py`
  - [PyArmor](https://github.com/dashingsoft/pyarmor)
    - A tool used to obfuscate python scripts, bind obfuscated scripts to fixed machine, or expire obfuscated scripts.

- ***Using [Nuitka](https://github.com/Nuitka/Nuitka) and [PyArmor](https://github.com/dashingsoft/pyarmor) together is the best way to compile Runecolor and protect its code through obfuscation.***
1. Make sure both Nuitka and PyArmor are installed:
   1. `pip install nuitka pyarmor`
2. Obfuscate `runecolor.py` with PyArmor.
   1. Initialize a PyArmor project:
      1. `pyarmor init --src . --entry src/runecolor.py dist_protected`
         1. This command sets up a PyArmor project with `runecolor.py` as the entry script and creates a folder named `dist_protected` where the obfuscated files will go.
   2. Obfuscate the files:
      1. `pyarmor pack -x "src/runecolor.py" --output dist-protected`
         1. This command obfuscates `runecolor.py` and places the obfuscated code in the `dist_protected` directory.
3. Compile the obfuscated script with Nuitka:
   1. `python -m nuitka --standalone --follow-imports --enable-plugin=tk-inter --enable-plugin=no-qt src/runecolor.py`
      1. `--standalone` creates a standalone executable that bundles all required dependencies so that the program can run independently of an external Python installation.
      2. `--follow-imports` tells Nuitka to follow all imports in the script and include those modules and their dependencies in the compiled executable.
      3. `--enable-plugin=tk-inter` enables the `tk-inter`  plugin in Nuitka. This includes Tkinter, which is the standard Python GUI library, ensuring Tkinter-dependent code works properly in the compiled executable.
      4. `--enable-plugin=no-qt` enables the `no-qt` plugin in Nuitka, which excludes Qt libraries from the final executable. This can reduce the executable's size, especially if the code doesn't depend on Qt.
      5. `src/runecolor.py` specifies `runecolor.py` in the `src` directory as the entry point to be compiled.
4. Test the compiled executable:
   1. `./src/runecolor`
