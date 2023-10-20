#!/usr/bin/python3
# by Ben Owen
# From Search.py, just output high values of 2F now

import DrillBits
import os
import sys
import xml.etree.ElementTree as ET
from DrillBits import CODE

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
max_braking = config.find("./searches/max_braking").text
min_braking = config.find("./searches/min_braking").text
mismatch = config.find("./searches/mismatch").text
rmw = config.find("./searches/running_median_window").text

# Read search_bands.xml for start frequency and band.
search_jobs = ET.parse("../search_bands.xml").getroot()
# Find the one corresponding to the script argument
j = str(sys.argv[1])
jobs = search_jobs.findall(".//search_job")
job = [e for e in jobs if e.find("job").text == j]
freq = job[0].find("freq").text
band = job[0].find("band").text

# Work out other things
sft_glob = config_file.replace("config.xml", "sfts/*.sft")

# Just do it!
os.system(CODE + "/bin/lalapps_ComputeFstatistic_v2 --Alpha=" + ra + " --Delta=" + dec + " --Freq=" + freq + " --FreqBand=" + band + " --DataFiles=" + sft_glob + " --gridType=9 --metricType=1 --metricMismatch=" + mismatch + " --outputFstatHist=histogram.$SLURM_ARRAY_TASK_ID --minStartTime=" + str(start) + " --maxStartTime=" + str(start + span - 1800 + 1) + " --spindownAge=" + age + " --minBraking=" + min_braking + " --maxBraking=" + max_braking + " --timerCount=1800 --RngMedWindow=" + rmw + " --outputSingleFstats=YES --outputFstat=loudest.$SLURM_ARRAY_TASK_ID --TwoFthreshold=40")
