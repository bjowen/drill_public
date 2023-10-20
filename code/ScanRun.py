#!/usr/bin/python3
# by Ben Owen
#   Take coarse custom fscan of run for use in finding optimal stretches.
#   Inputs: sft_database.xml.$TASK
#   Outputs: sft_database.xml.$TASK

import DrillBits
import os
import sys
import xml.etree.ElementTree as ET
from DrillBits import CODE

# Read configuration parameters
cfg = ET.parse("../../config.xml").getroot()
breaks = cfg.findall('./searches/band_breaks/freq')
break_freqs = [float(el.text) for el in breaks]
# Test for psd_file in config.xml

# Open the input file, taken from the argument.
fname = "sft_database.xml." + str(sys.argv[1])
sft_root = ET.parse(fname).getroot()

# For each SFT in our input file:
for sft in sft_root.findall("sft"):
    # Remove any existing "power" elements.
    for old in sft.findall("power"):
        sft.remove(old)
    # Compute SFT power in each band.
    for i in range(len(breaks)-1):
        band = str(break_freqs[i+1] - break_freqs[i])
        cmd = CODE + "/bin/lalapps_ComputePSD --inputData='" + sft.find("path").text + "' --outputPSD='/dev/stdout' --Freq=" + breaks[i].text + " --FreqBand=" + band + " --binSizeHz=" + band
        print(cmd)
        for line in os.popen(cmd).readlines():
            words = line.split()
            if (words[0] != "%%"):
                power = words[1]
        foo = ET.SubElement(sft, "power")
        foo.text = power
        foo.set("comment", "per Hz, " + breaks[i].text + " to " + breaks[i+1].text + " Hz")

# Write back to this task's SFT database.
DrillBits.indent(sft_root)
ET.ElementTree(sft_root).write(fname)

