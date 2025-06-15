import pathlib

import customtkinter as ctk

fonts_path = pathlib.Path(__file__).parent
ctk.FontManager.load_font(str(fonts_path.joinpath("CascadiaCode.ttf")))


def get_font(
    family: str = "Verdana",
    size: int = 14,
    weight: str = "normal",
    slant: str = "roman",
    underline: bool = False,
) -> ctk.CTkFont:
    """Return a font object customized with the specified parameters.

    This function serves as a convenient wrapper for creating font objects using the
    `ctk.CTkFont` class. It offers default values suited for customtkinter's default
    theme fonts.

    To get a list of font families available on a local Windows machine, the following
    two lines of PowerShell lists them in the console:
        ```
        [System.Reflection.Assembly]::LoadWithPartialName("System.Drawing")
        (New-Object System.Drawing.Text.InstalledFontCollection).Families
        ```

    Args:
        family (str, optional): Font family from those available on the local machine,
            a CTkFont default ("Helvetica", "Arial", "Times New Roman", "Courier New",
            or "Verdana"), or loaded locally. Defaults to "Verdana".
        size (int, optional): The desired font size. Defaults to 14.
        weight (str, optional): Choose between "normal" or "bold". Defaults to "normal".
        slant (str, optional): Choose between "roman", "italic", or "oblique" which is
            similar to italic, but less pronounced (and some fonts do not distinguish
            between oblique and italic styles). Defaults to "roman".
        underline (bool, optional): Whether the text should be underlined. Defaults to
            False.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    return ctk.CTkFont(
        family=family, size=size, weight=weight, slant=slant, underline=underline
    )


def title_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for titles (largest).

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 24
    return get_font(**kwargs)


def heading_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for headings.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 18
    if "weight" not in kwargs:
        kwargs["weight"] = "bold"
    return get_font(**kwargs)


def heading_font_normal(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for headings.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 18
    if "weight" not in kwargs:
        kwargs["weight"] = "normal"
    return get_font(**kwargs)


def subheading_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for subheadings.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 16
    if "weight" not in kwargs:
        kwargs["weight"] = "bold"
    return get_font(**kwargs)


def body_large_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for body text.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 15
    return get_font(**kwargs)


def body_med_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for body text.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 14
    return get_font(**kwargs)


def button_med_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for button text.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 14
    if "weight" not in kwargs:
        kwargs["weight"] = "bold"
    return get_font(**kwargs)


def button_small_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for button text.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 12
    if "weight" not in kwargs:
        kwargs["weight"] = "bold"
    return get_font(**kwargs)


def small_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for small text, such as captions or footnotes.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 12
    return get_font(**kwargs)


def micro_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for micro text, such as version stamps.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 10
    return get_font(**kwargs)


def log_font(**kwargs) -> ctk.CTkFont:
    """Get a `CTkFont` preset for monospaced log text.

    Returns:
        ctk.CTkFont: Font object to be applied to text displayed in `customtinkter`
            widgets by setting the `font` option.
    """
    if "size" not in kwargs:
        kwargs["size"] = 12
    if "family" in kwargs:
        kwargs.pop("family")
    return get_font(family="Cascadia Code", **kwargs)
