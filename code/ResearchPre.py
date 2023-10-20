#!/usr/bin/python3
# by Ben Owen
# Figure out further look threshold and prepare to rerun those jobs.

import DrillBits
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import numpy
import os
import scipy.stats
import xml.etree.ElementTree as ET
from DrillBits import JOBS_PER_DIR
from matplotlib.axis import Axis

# Read setup parameters
setup = ET.parse("setup.xml").getroot()

# Read config parameters
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
false_alarm = float(config.find("./searches/false_alarm").text)
threshold_KS = float(config.find("./searches/threshold_KS").text)
threshold_CvM = float(config.find('./searches/threshold_CvM').text)

### Loop over search jobs in database

# Make element tree from search bands file
search_jobs = ET.parse("search_bands.xml").getroot()
# Make element tree from scratch for candidates
cand_root = ET.Element('candidates')

# Find total templates and 2F threshold for further look
# Now neglecting correlations between templates
total_templates = 0
jobs = search_jobs.findall("search_job")
for search_job in jobs:
    total_templates += int(search_job.find("templates").text)
# Next bit should be lifted out as a function - chi-square threshold
x = (1 - (1 - false_alarm)**(1.0/total_templates)) / numpy.exp(1)
y = numpy.real(-scipy.special.lambertw(-x, -1))
threshold_2F = 2*y - 1
# write redundant false alarm probability just in case?
ET.SubElement(cand_root, 'templates').text = str(total_templates)
ET.SubElement(cand_root, 'threshold_2F').text = str(threshold_2F)

# Find candidate jobs and make some global plots
c_jobs = ""
candidates = 0
for search_job in jobs:
    
    # Get some info for every job
    job = search_job.find("job").text
    freq = search_job.find("freq").text
    twoF = float(search_job.find("loudest_2F").text)
    KS = float(search_job.find("KS_distance").text)
    CvM = float(search_job.find("CvM_distance").text)
    AD = float(search_job.find("AD_distance").text)

    # Now just look at candidate jobs
    if twoF < threshold_2F:
        continue
    if CvM > threshold_CvM:
        continue

    # Make candidate XML element
    cand = ET.SubElement(cand_root, 'candidate')
    ET.SubElement(cand, 'job').text = job
    ET.SubElement(cand, 'freq').text = freq
    ET.SubElement(cand, 'loudest_2F').text = str(twoF)
    ET.SubElement(cand, 'KS_distance').text = str(KS)
    ET.SubElement(cand, 'CvM_distance').text = str(CvM)
    candidates += 1

    # If we're first on the list, it's easy
    if c_jobs == "":
        c_jobs = job
        continue
    prev = str(int(job)-1)
    if c_jobs.endswith("-" + prev):
        # replace only LAST occurrence of job - be paranoid
        c_jobs = job.join(c_jobs.rsplit(prev, 1))
    elif c_jobs.endswith(prev):
        c_jobs += "-" + job
    else:
        c_jobs += "," + job

DrillBits.indent(cand_root)
ET.ElementTree(cand_root).write('candidates.xml')

# Make global plots
os.makedirs('plots', exist_ok=True)
with open(os.path.join('plots', 'twoF_v_f.dat'), 'w') as f:
    [f.write(e.find("freq").text + " " + e.find("loudest_2F").text + "\n") for e in jobs]
with open(os.path.join('plots', 'KS_v_2F.dat'), 'w') as f:
    [f.write(e.find("loudest_2F").text + " " + e.find("KS_distance").text + "\n") for e in jobs]
with open(os.path.join('plots', 'CvM_v_2F.dat'), 'w') as f:
    [f.write(e.find("loudest_2F").text + " " + e.find("CvM_distance").text + "\n") for e in jobs]
with open(os.path.join('plots', 'CvM_v_f.dat'), 'w') as f:
    [f.write(e.find("freq").text + " " + e.find("CvM_distance").text + "\n") for e in jobs]

# Generate plot data for candidates
for cand in cand_root.findall('candidate'):

    # Read histogram file and put in plots dir for xmgrace
    job = cand.find('job').text
    sub = str(int(int(job) / JOBS_PER_DIR))
    f = open(os.path.join('plots', 'histogram.' + job + '.dat'), 'w')
    for line in open(os.path.join('search', sub, 'histogram.' + job), 'r').readlines():
        field = line.split()
        try:
            x = (float(field[0]) + float(field[1]))/2
        except:
            continue
        y = float(field[2])
        f.write(str(x) + ' ' + str(y) + '\n')
    f.close()

# Write submit file for re-search
