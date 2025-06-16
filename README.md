<div align="center">

![Platform: Windows](https://img.shields.io/badge/platform-windows-blue)
![Python Version](https://img.shields.io/badge/python-3.10.9-blue)

![logo](src/img/ui/splash.png)
</div>

- Runecolor is a desktop client for managing automation scripts in oldschool runescape.
- Built on top of [OS-Bot-COLOR](https://github.com/kelltom/OS-Bot-COLOR) and [runedark](https://github.com/cemenenkoff/runedark-public)
- Kinda playground for me to learn programming

# Features
- Unlike traditional injection or reflection frameworks, Runecolor takes a hands-off approach, leveraging computer vision and optical character recognition for precise and efficient automation.

  - ***Object Detection***: Detects and converts in-game objects into data structures.
  - ***Image Recognition***: Identifies images within images using computer vision.
  - ***Color-on-Color OCR***: Reads text on varying font and background colors reliably.
  - ***Humanization***: Adds randomness to mouse movements, wait times, and keystrokes for natural behavior.

# Quickstart <img height=20 src="src/img/website/windows-logo.png"/>
1. Install [Python 3.10.9](https://www.python.org/downloads/release/python-3109/).
2. Install [Git Bash for Windows](https://git-scm.com/downloads).
3. Open an IDE (e.g. [VS Code](https://code.visualstudio.com/)).
4. Clone this repository.
5. Set up a virtual environment.
   1. Create virtual environment `py -3.10.9 -m venv venv`
   3. Activate virtual environment: `venv/Scripts/activate`
   4. Install dependencies: `pip install -r requirements.txt`
6. Run: `python src/rune_dark.py`



#
#
Based on:
- [runedark-public](https://github.com/cemenenkoff/runedark-public) by [cemenenkoff](https://github.com/cemenenkoff)
- [OS-Bot-COLOR](https://github.com/kelltom/OS-Bot-COLOR) by [kelltom](https://github.com/kelltom)
- Licensed under the MIT License.
