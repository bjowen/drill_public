#!/usr/bin/python3
# by Ben Owen

import DrillBits
import os
import sys
import xml.etree.ElementTree as ET
from DrillBits import CODE

# Read setup.xml for parameters.
setup = ET.parse("../../setup.xml").getroot()
age = setup.find("age").text
dec = setup.find("dec").text
ra = setup.find("ra").text
# Convert days to seconds.
span = int(float(setup.find("span").text) * 86400)
start = int(setup.find("start").text)

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
max_braking = config.find("./searches/max_braking").text
min_braking = config.find("./searches/min_braking").text
mismatch = config.find("./searches/mismatch").text
rmw = config.find("./searches/running_median_window").text

# Check if this job ran ok last time and don't rerun it
j = str(sys.argv[1])
ran_ok = True
# Check if error file is not full
try:
    with open('error.' + job, 'r') as f:
        for line in f:
            if len(line) > 0:
                ran_ok = False
except:
    pass
# Check if histogram file finished
try:
    with open('histogram.' + job, 'r') as f:
        for line in f:
            if '%DONE' in line:
                ran_ok = True
            else:
                ran_ok = False
except:
    ran_ok = False
# Check if output file finished
try:
    with open('output.' + job, 'r') as f:
        for line in f:
            if 'Search finished.' in line:
                ran_ok = True
            else:
                ran_ok = False
except:
    ran_ok = False
if ran_ok:
    sys.exit()

# Read search_bands.xml for start frequency and band.
search_jobs = ET.parse("../../search_bands.xml").getroot()
jobs = search_jobs.findall(".//search_job")
job = [e for e in jobs if e.find("job").text == j]
freq = job[0].find("freq").text
band = job[0].find("band").text

# Work out other things
sft_glob = config_file.replace("config.xml", "sfts/*.sft")

# Just do it!
os.system(CODE + "/bin/lalapps_ComputeFstatistic_v2 --Alpha=" + ra + " --Delta=" + dec + " --Freq=" + freq + " --FreqBand=" + band + " --DataFiles=" + sft_glob + " --gridType=9 --metricType=1 --metricMismatch=" + mismatch + " --outputFstatHist=histogram.$SLURM_ARRAY_TASK_ID --minStartTime=" + str(start) + " --maxStartTime=" + str(start + span - 1800 + 1) + " --spindownAge=" + age + " --minBraking=" + min_braking + " --maxBraking=" + max_braking + " --timerCount=1800 --RngMedWindow=" + rmw + " --outputSingleFstats=YES")
