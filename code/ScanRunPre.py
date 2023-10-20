#!/usr/bin/python3
# by Ben Owen
#   Prescript for ScanRun.py.
#   Inputs: config.xml, <sft_dir>/*.sft
#   Outputs: sfts/*.sft, sft_database.xml.$TASK

import DrillBits
import os
import tempfile
import xml.etree.ElementTree as ET
from DrillBits import CODE

# Read configuration parameters.
cfg = ET.parse('config.xml').getroot()
breaks = cfg.findall('./searches/band_breaks/freq')
break_freqs = [float(el.text) for el in breaks]
run_start = cfg.find('./data/start').text
run_stop = cfg.find('./data/stop').text
sft_dir = cfg.find('./data/sft_dir').text
ul_band = cfg.find('./upper_limits/band').text

# Find all SFTs with a system call.
cmd = 'find sft_dir -name "*.sft"'
cmd = cmd.replace('sft_dir', sft_dir)
sft_paths = os.popen(cmd)

# Make SFT XML database for whole run.
sft_root = ET.Element('sfts')
for path in sft_paths:
    path = path.rstrip()
    sft = ET.SubElement(sft_root, 'sft')
    ET.SubElement(sft, 'path').text = path
    name = path.split('/')[-1]
    ifo = name.split('_')[1]
    ET.SubElement(sft, 'ifo').text = ifo
    start = name.split('-')[2]
    ET.SubElement(sft, 'start').text = start

# Sort SFTs by start time.
sft_root[:] = sorted(sft_root, key=lambda el: int(el.findtext('start')))
sfts = sft_root.findall("sft")

# Make glob directory for all SFTs as soft links.
os.system("mkdir -p sfts")
for sft in sfts:
    os.system("ln -s " + sft.find("path").text + " sfts 2>/dev/null")

# Split into chunks for parallel jobs
tasks = 20
l = len(sfts)
os.system("mkdir -p jobs/ScanRun")
os.chdir("jobs/ScanRun")
for c in range(tasks):
    c_root = ET.Element('sfts')
    # WILL THIS MISS SOME?
    for sft in sfts[int(c*l/tasks) : int((c+1)*l/tasks)]:
        c_root.append(sft)
    # Write task file
    DrillBits.indent(c_root)
    ET.ElementTree(c_root).write('sft_database.xml.' + str(c))

# Write job array submit file
DrillBits.write_submit_array(None, "ScanRun.py", tasks)
