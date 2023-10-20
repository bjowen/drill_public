#!/usr/bin/python3
# by Ben Owen

import DrillBits
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from DrillBits import CODE
import numpy as np

# Read setup.xml for parameters.
setup = ET.parse("../setup.xml").getroot()
age = setup.find("age").text
dec = setup.find("dec").text
ra = setup.find("ra").text
# Convert days to seconds.
span = int(float(setup.find("span").text) * 86400)
start = int(setup.find("start").text)

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
mismatch = config.find("./searches/mismatch").text
rmw = config.find("./searches/running_median_window").text
ul_band = float(config.find('./upper_limits/band').text)
fdr = float(config.find('./upper_limits/false_dismissal').text)
try:
    new_uls = config.find("options/new_style_uls").text
except:
    new_uls = None

# read upper limit bands
upper = ET.parse("../upper_limits.xml").getroot()

# Find the one corresponding to the script argument
jobs = upper.findall(".//upper_limit")
j = str(sys.argv[1])
job = [e for e in jobs if e.find("job").text == j]
ul_freq = job[0].find("freq").text
ul_band = job[0].find("band").text
loudest_2F = job[0].find('loudest_2F').text
loudest_nonvetoed_2F = job[0].find('loudest_nonvetoed_2F').text
fraction_vetoed = float(job[0].find('fraction_vetoed').text)

# THIS PARAMETER IS CHOSEN AD HOC
adj = 0.005

# If too much of the UL band is vetoed, UL is zero and don't bother
if fraction_vetoed >= fdr:
    with open('upper_limit.txt.' + j, 'w') as f:
        f.write('h0=0\n')
    sys.exit()

# Are we using new style upper limits or not?
if new_uls != None:
    # my_fdr accounts for vetoed bands
    my_fdr = (fdr - fraction_vetoed) / (1.0 - fraction_vetoed)
    my_2F = loudest_nonvetoed_2F
else:
    my_fdr = fdr
    my_2F = loudest_2F

# If our upper limit file exists, assume this is a rerun, see how it did
if os.path.exists("upper_limit.txt." + j):
    injections_fdr = float(job[0].find('injections_fdr').text)
else:
    injections_fdr = 0

# If injections_fdr is too high, adjust my_fdr and clear injections for rerun
if injections_fdr > fdr:
    # Read fdr last used and decrement by adj:
    with open("upper_limit.txt." + j, "r") as ulf:
        # Get command line arg used in previous upper limit
        a = [w for w in ulf.readlines()[1].split() if w.startswith('--false-dism=')][0]
        my_fdr = float(a.split('=')[1]) - adj
        # This means no upper limit
        if my_fdr <= 0:
            with open('upper_limit.txt.' + j, 'w') as f:
                f.write('h0=0\n')
                sys.exit()

    # Remove any old injection files so this reruns
    os.system("/bin/rm -f injections/" + j + "/*")
# This was a good result, don't waste CPU rerunning
elif injections_fdr > 0:
    sys.exit()

# Now it's either a bad result to rerun or a fresh run
# Run upper limit estimate with my_fdr
sft_glob = '../sfts/*.sft'
cmd = CODE + "/bin/lalapps_ComputeFstatMCUpperLimit  --alpha=" + ra + " --delta=" + dec + " --freq=" + ul_freq + " --freq-band=" + ul_band + " --loudest-2F=" + my_2F + "  --max-mismatch=" + mismatch +" --sft-patt=" + sft_glob +" --rng-med-win=" + rmw + "  --false-dism=" + str(my_fdr) + " --output-file=upper_limit.txt.$SLURM_ARRAY_TASK_ID  --2F-pdf-hist-file=upper_limit_histogram.txt.$SLURM_ARRAY_TASK_ID  --2F-pdf-hist-binw=10 --mism-hist-file=" + CODE + "/upper_limit_mismatch_histogram.txt"
print(cmd)
os.system(cmd)
