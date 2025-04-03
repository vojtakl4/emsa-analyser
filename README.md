# A simple gel analyser for electromobility shift assay (EMSA)

This [Fiji](https://imagej.net/software/fiji/) script has been developed as a lightweight open source gel analyser since I couldn't find any available on the web (apart from ImageJ's default one, which is quite limited and somehow confusing without reading a tutorial).

The tool currently supports:
 - displaying gel files (so far tested on `.tif` files and `.gel` files from Typhoon FLA 9000 scanner accompanying software)
 - multiple vertical or horizontal lane selection
 - adjustable lane width
 - optional auto-adjustment of contrast to make features on a gel easier to see (intensity values used for analysis are not affected)
 - background subtraction with a plane-fitting method
 - analysis of areas of interest on the selected lanes as a sum of intensity peaks in a region after background subtraction
 - multiple areas of interest supported
 - analysis results may be saved as a `.txt` file

## Installing and running the script

Download the `.py` file from this repository. In your Fiji, click on Plugins > Install (or hit Ctrl+Shift+M). In the window that opens, find the downloaded file, click Open, then Save in the second window that shows up. Restart Fiji. Great! You should now have the script locally installed.

To use the script, first open the gel file you wish to analyse in your Fiji, then click on Plugins > emsa script (it's usually right at the end of the Plugins menu). Have fun!
