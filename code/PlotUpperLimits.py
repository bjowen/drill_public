#!/usr/bin/python3
# by Ben Owen
# Run from main search directory

import DrillBits
import xml.etree.ElementTree as ET

# Read setup.xml for parameters.
setup = ET.parse("setup.xml").getroot()

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
fdr = float(config.find('./upper_limits/false_dismissal').text)

# Read upper limit bands
uls = ET.parse("upper_limits.xml").getroot()

# Loop over upper limit bands
for ul in uls:
    # Take frequency in middle of band
    f = float(ul.find('freq').text) + float(ul.find('band').text)/2
    # Check h0 against injections, though it should have been done earlier
    h0 = float(ul.find('h0').text)
    if float(ul.find('injections_fdr').text) > fdr:
        h0 = 0
    # Print to stdout
    print(str(f) + " " + str(h0))
