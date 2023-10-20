#!/usr/bin/python3
# by Ben Owen
#   Take coarse custom fscan of run for use in finding optimal stretches. This
# script should be run as a batch job.
#   Inputs: sft_database.xml.TASK
#   Outputs: sft_database.xml

import DrillBits
import xml.etree.ElementTree as ET

# Read number of tasks from submit file.
with open("submit.sh", "r") as f:
    for line in f.readlines():
        if "array" in line:
            tasks = int(line.split("array=")[1].split("-")[1])

# Collect all SFTs from all files into sft_root.
sft_root = ET.Element("sfts")
for t in range(tasks):
    t_root = ET.parse("sft_database.xml." + str(t)).getroot()
    for sft in t_root.findall("sft"):
        sft_root.append(sft)

# Write database of all SFTs.
DrillBits.indent(sft_root)
ET.ElementTree(sft_root).write('../../sft_database.xml')

