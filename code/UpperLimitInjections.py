#!/usr/bin/python3
# by Ben Owen
# Should be called with simple job number

import DrillBits
import math
import numpy
import os
import random
import re
import sys
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from DrillBits import CODE
import numpy as np

# Read setup.xml for parameters.
setup = ET.parse("../../setup.xml").getroot()
age = float(setup.find('age').text)
dec = float(setup.find('dec').text)
ra = float(setup.find('ra').text)
span = int(float(setup.find('span').text) * 86400)
start = int(setup.find('start').text)

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
inj_per_band = int(config.find('upper_limits/inj_per_band').text)
jobs_per_band = int(config.find('upper_limits/jobs_per_band').text)
max_braking = float(config.find('searches/max_braking').text)
min_braking = float(config.find('searches/min_braking').text)
mismatch = float(config.find("searches/mismatch").text)
rmw = config.find('searches/running_median_window').text
scratch = config.find('cluster/scratch').text
try:
    new_uls = config.find("options/new_style_uls").text
except:
    new_uls = None

# Take job number and get old style args
j = int(sys.argv[1])
# job, subjob, h0, injections
job = str(int(j / jobs_per_band))
subjob = str(j % jobs_per_band)

# Read upper limit bands and find which one we are tasked with
ul_root = ET.parse("../../upper_limits.xml").getroot()
ul_jobs = ul_root.findall(".//upper_limit")
ul_job = [e for e in ul_jobs if e.find('job').text == job][0]
h0 = float(ul_job.find('h0').text)
ul_freq = float(ul_job.find('freq').text)
ul_band = float(ul_job.find('band').text)

# Read veto bands and drop the ones not overlapping this ul band
veto_root = ET.parse("../../veto_bands.xml").getroot()
all_veto_bands = veto_root.findall(".//veto_band")
veto_bands = [e for e in all_veto_bands if float(e.find('freq').text) < ul_freq + ul_band and float(e.find('freq').text) + float(e.find('band').text) > ul_freq]

# Check on previous injections
os.system('mkdir -p ' + job)
os.chdir(job)
# Check if output is already done or partially done
outname = 'upper_limit_injections.txt.' + job + '.' + subjob
try:
    outfile = open(outname, "r")
    done = len(outfile.readlines())
    outfile.close()
    outfile = open(outname, "a", buffering=1)
except:
    done = 0
    outfile = open(outname, "w", buffering=1)
if done == int(inj_per_band / jobs_per_band):
    sys.exit()

# Make narrowband SFTs in fast access scratch directory
sft_dir_ob = tempfile.TemporaryDirectory()
sft_dir = sft_dir_ob.name
sft_glob = config.find('data/sft_dir').text + '*.sft'
fast_sft_glob = sft_dir + '/*.sft'
sft_fmin = ul_freq - ul_band
sft_fmax = ul_freq + 2*ul_band
time.sleep(random.randint(0, 100))
cmd = CODE + '/bin/lalapps_ConvertToSFTv2 --inputSFTs=' + sft_glob + ' --fmin=' + str(sft_fmin) + ' --fmax=' + str(sft_fmax) + ' --outputDir=' + sft_dir + ' --minStartTime=' + str(start) + ' --maxStartTime=' + str(start + span - 1800 + 1)
print(cmd + '\n', flush=True)
os.system(cmd)

# Bounding box of metric ellipse
bounding_box = [math.sqrt(1200*mismatch) / math.pi / float(span), math.sqrt(25920*mismatch) / math.pi / pow(span, 2), math.sqrt(100800*mismatch) / math.pi / pow(span, 3)]

# For each injection
for i in range(done, int(inj_per_band / jobs_per_band)):

    # Choose nuisance parameters of injection
    cosi = -1 + random.random() * 2
    psi = random.random() * 2 * math.pi
    phi = random.random() * 2 * math.pi

    # Choose frequency of injection
    f0 = random.uniform(ul_freq, ul_freq + ul_band)
    # Move on if we're in a vetoed band and doing new style ULs
    if new_uls != None:
        v = [e for e in veto_bands if f0 >= float(e.find('freq').text) and f0 < float(e.find('freq').text) + float(e.find('band').text)]
        if len(v) > 0:
            outfile.write('0\n')
            continue

    # Choose other intrinsic parameters of injection
    f1min = -f0 / (min_braking - 1) / age
    f1max = -f0 / (max_braking - 1) / age
    f1 = f1min + random.random() * (f1max - f1min)
    f2min = min_braking * f1 * f1 / f0
    f2max = max_braking * f1 * f1 / f0
    f2 = f2min + random.random() * (f2max - f2min)

    # Set band for SFTs
    # HARD CODING ORBITAL MOD AND 2*DIRICHLET KERNEL HERE AND FUDGE
    # AND PADDING FACTOR ON END
    fmin = f0 * (1 - 1.0 * span / min_braking / age) * (1 - 1e-4) - 0.4
    fmax = f0 * (1 + 1e-4) + 0.4
    # Round fmin down and fmax up to nearest 0.1 Hz
    fmin = round(fmin - 0.05, 1)
    band = round(fmax + 0.05 - fmin, 1)

    # Inject signal into new SFTs and search
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Search four bounding boxes, random centering
        boxes = 4
        f0min = f0 - (boxes + random.random()) * bounding_box[0]
        f1min = f1 - (boxes + random.random()) * bounding_box[1]
        f2min = f2 - (boxes + random.random()) * bounding_box[2]
        f0band = (boxes * 2 + 1) * bounding_box[0]
        f1band = (boxes * 2 + 1) * bounding_box[1]
        f2band = (boxes * 2 + 1) * bounding_box[2]

        # IFOS ARE HARD CODED FOR NOW!
        # Write injection
        for ifo in ['H1', 'L1', 'V1']:
            cmd = CODE + '/bin/lalapps_Makefakedata_v4 --outSFTbname=' + tmp_dir + ' --IFO=' + ifo + ' --startTime=' + str(start) + 'GPS --duration=' + str(span) + ' --fmin=' + str(fmin) + ' --Band=' + str(band) + ' --window=Tukey --tukeyBeta=0.001 --Alpha=' + str(ra) + ' --Delta=' + str(dec) + ' --Freq=' + str(f0) + ' --f1dot=' + str(f1) + ' --f2dot=' + str(f2) + ' --h0=' + str(h0) + ' --cosi=' + str(cosi) + ' --psi=' + str(psi) + ' --phi=' + str(phi) + ' --noiseSFTs=' + fast_sft_glob + ' --refTime=' + str(start)
            print(cmd + '\n', flush=True)
            os.system(cmd)

        # Search for injection
        loudest_2F = 0
        cmd = CODE + "/bin/lalapps_ComputeFstatistic_v2 --Alpha=" + str(ra) + " --Delta=" + str(dec) + " --Freq=" + str(f0min) + " --FreqBand=" + str(f0band) + " --f1dot=" + str(f1min) + " --f1dotBand=" + str(f1band) + " --f2dot=" + str(f2min) + " --f2dotBand=" + str(f2band) + " --DataFiles=" + tmp_dir + "/*.sft --gridType=8 --metricMismatch=" + str(mismatch) + " --refTime=" + str(start) + " --RngMedWindow=" + rmw + " --outputFstat=/dev/stdout --NumCandidatesToKeep=1 --outputSingleFstats=TRUE --minStartTime=" + str(start) + " --maxStartTime=" + str(start + span - 1800 + 1)
        print(cmd + '\n', flush=True)
        for line in os.popen(cmd).readlines():
            words = line.split()
            if words[0][0] == '%':
                continue
            try:
                twoF = float(words[6])
            except:
                continue
            if twoF > loudest_2F:
                loudest_2F = twoF

        # Write to output file
        outfile.write(str(loudest_2F) + '\n')

# Clean up
outfile.close()
sft_dir_ob.cleanup()
