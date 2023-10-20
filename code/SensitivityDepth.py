#!/usr/bin/python3

import DrillBits
import math
import subprocess
import xml.etree.ElementTree as ET
from DrillBits import CODE

# Read setup.xml for parameters.
setup = ET.parse('setup.xml').getroot()
span = int(float(setup.find('span').text) * 86400)
start = int(setup.find('start').text)

# Read upper limits.
ul_root = ET.parse('upper_limits.xml').getroot()
ul_jobs = ul_root.findall('.//upper_limit')

# For each upper limit band:
for job in ul_jobs:
    # Write arguments for PSD computation of that band.
    with open("cpsd_args.txt", "w") as ca:
        ca.write("inputData=sfts/*.sft\n")
        ca.write("startTime=" + str(start) + "\n")
        ca.write("endTime=" + str(start + span - 1800) + "\n")
        ca.write("outputPSD=/dev/stdout\n")
        ca.write("Freq=" + job.find('freq').text + "\n")
        ca.write("FreqBand=" + job.find('band').text + "\n")
        ca.write("binSizeHz=" + job.find('band').text + "\n")
    # Run and read PSD computation.
    for line in subprocess.Popen(args = [CODE + "/bin/lalapps_ComputePSD", "@cpsd_args.txt"], stdout = subprocess.PIPE).stdout.readlines():
        line = str(line, 'utf-8')
        words = line.split()
        if words[0] == "%%":
            continue
        freq = float(words[0])
        psd = float(words[1])
        break
    # Compute sensitivity depth for this band, zero if no strain limit.
    h0 = float(job.find('h0').text)
    if h0 > 0:
        depth = math.sqrt(float(psd)) / float(job.find('h0').text)
    else:
        depth = 0
    # Record in upper limit data.
    try:
        job.find('psd').text = str(psd)
    except:
        ET.SubElement(job, 'psd').text = str(psd)
    try:
        job.find('depth').text = str(depth)
    except:
        ET.SubElement(job, 'depth').text = str(depth)
    print(str(freq) + ' ' + str(psd) + ' ' + str(depth))

# Write upper limit bands file
DrillBits.indent(ul_root)
ET.ElementTree(ul_root).write('upper_limits.xml')
