
***Remember to strip ICC profiles with ImageMagick***

If using GIMP to edit images, it will by default attach an sRGB profile that prompts the following warning in Python:
    `libpng warning: iCCP: known incorrect sRGB profile`

This warning comes from libraries associated with OpenCV. According to [this article](https://imagemagick.org/script/color-management.php), "[m]ost image processing algorithms assume a linear colorspace, therefore it might be prudent to convert to linear color or remove the gamma function before certain image processing algorithms are applied."

The cmd command we should use to strip ICC profiles is:
`magick myimage.png -set colorspace RGB myRGBimage.png`
