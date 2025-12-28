# KM Plot

Inkscape extension for Knox Makers to drive HPGL based vinyl/plotter devices over serial. Largely based on the built-in Export > Plot extension for Inkscape but with a GTK interface and Serial Port detection.

## Manual Installation

1) Copy the files into your Inkscape extensions directory:
   - Linux: `~/.config/inkscape/extensions/`
     - Flatpak: `~/.var/app/org.inkscape.Inkscape/config/inkscape/extensions/`
     - Snap: `~/snap/inkscape/current/.config/inkscape/extensions/`
   - macOS (Inkscape app bundle): `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`
   - Windows: `%APPDATA%\Inkscape\extensions\`

2) Restart Inkscape, then find the extension under **Extensions -> Knox Makers -> KM Plot**.

3) Connect your plotter via USB/serial; select the detected port in the Device tab, adjust settings as needed, and click **Send to plotter**.
