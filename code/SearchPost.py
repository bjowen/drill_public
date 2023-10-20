#!/usr/bin/python3
# by Ben Owen
# Collate results in search bands and UL bands, do KS test. This is the
# discontinuous two-sample test, so we don't use SciPy but write our own code.

import DrillBits
import math
import numpy
import os
import scipy.stats
import xml.etree.ElementTree as ET
from DrillBits import JOBS_PER_DIR

# Read setup parameters
setup = ET.parse("setup.xml").getroot()
fmax = float(setup.find("fmax").text)
fmin = float(setup.find("fmin").text)

# Read config parameters
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
false_alarm = float(config.find("./searches/false_alarm").text)
threshold_CvM = float(config.find('./searches/threshold_CvM').text)
ul_band = float(config.find("./upper_limits/band").text)

basedir = os.getcwd()

### Loop over search jobs in database, create UL bands at same time

# Prep UL stuff for loop
ul_root = ET.Element("upper_limits")
upper_limit = ET.SubElement(ul_root, "upper_limit")
ET.SubElement(upper_limit, "freq").text = str(fmin)
ET.SubElement(upper_limit, "band").text = str(ul_band)
ET.SubElement(upper_limit, "job").text = "0"
ul_job = 0
loudest_ul_2F = 0

# Prep veto stuff for loop
loudest_nonvetoed_2F = 0
frac_vetoed = 0
veto_fmin = 0
veto_fmax = 0
veto_root = ET.Element("veto_bands")

# Prep search stuff for loop
search_jobs = ET.parse("search_bands.xml").getroot()
bad_jobs = ""

# Loop over search bands
os.chdir("search")
for search_job in search_jobs.findall("search_job"):
    job = search_job.find("job").text

    # Change to appropriate subdirectory
    subdir = str(int(int(job) / JOBS_PER_DIR))
    os.chdir(subdir)

    # Read number of templates
    for line in open("output." + job, "r").readlines():
        field = line.split()
        try:
            templates = float(field[5].split("/")[1])
        except:
            continue

    # Read 2F histogram from file and make cdf, statistical tests
    count = 0
    maxdev = 0
    CvM = 0 # Cramer-von Mises statistic
    AD = 0 # Anderson-Darling statistic
    chi2 = 0 # Chi-square test
    # Get number of histogram bins
    nbins = 0
    for line in open('histogram.' + job, 'r').readlines():
        # Skip comment lines
        field = line.split()
        try:
            low = float(field[0])
        except ValueError:
            continue
        nbins += 1
    # Loop over lines in histogram file
    for line in open("histogram." + job, "r").readlines():
        # Skip comment lines
        field = line.split()
        try:
            low = float(field[0])
        except ValueError:
            continue
        # Use top of bin for twoF value
        twoF = float(field[1])
        obs = int(field[2])
        count += obs
        edf = count/templates
        c = scipy.stats.chi2.cdf(twoF, df=4)
        b = scipy.stats.chi2.cdf(low, df=4)
        # For Kolmogorov-Smirnov distance
        dev = abs(edf - c)
        if dev > maxdev:
            maxdev = dev
        # For quadratic empirical distribution function statistics
        foo = dev*dev*scipy.stats.chi2.pdf(twoF, df=4)*(twoF-low)
        # For Cramer-von Mises
        CvM += foo
        # For Anderson-Darling
        # BREAKS WHEN c IS TOO CLOSE TO 1
        AD += foo/c/(1-c)
        # For chi-square
        expect = templates*(c-b)
        chi2 += (obs - expect)**2 / expect**2

    # Record loudest 2F (bin) in search job
    el = search_job.find("loudest_2F")
    if el == None:
        el = ET.SubElement(search_job, "loudest_2F")
    el.text = str(twoF)
    
    # Record KS distance of search job
    el = search_job.find("KS_distance")
    if el == None:
        el = ET.SubElement(search_job, "KS_distance")
    el.text = str(maxdev)

    # Record CvM distance of search job
    CvM = math.sqrt(CvM)
    el = search_job.find("CvM_distance")
    if el == None:
        el = ET.SubElement(search_job, "CvM_distance")
    el.text = str(CvM)

    # Record AD distance of search job
    el = search_job.find("AD_distance")
    if el == None:
        el = ET.SubElement(search_job, "AD_distance")
    el.text = str(math.sqrt(AD))

    # Record chi square of search job
    el = search_job.find("chi2")
    if el == None:
        el = ET.SubElement(search_job, "chi2")
    el.text = str(chi2)

    # Record number of templates in search job
    el = search_job.find("templates")
    if el == None:
        el = ET.SubElement(search_job, "templates")
    el.text = str(int(templates))

    # Update ul band(s) overlapping this search band
    # First find frequency bounds
    ul_fmin = float(upper_limit.find('freq').text)
    ul_fmax = ul_fmin + float(upper_limit.find('band').text)
    sj_fmin = float(search_job.find('freq').text)
    sj_fmax = sj_fmin + float(search_job.find('band').text)
    # If search job starts in this ul band - IS THIS ALWAYS TRUE NOW?
    if sj_fmin >= ul_fmin and sj_fmin < ul_fmax:
        # Update loudest 2F of this UL band
        if loudest_ul_2F < twoF:
            loudest_ul_2F = twoF
        # Update vetoed fraction of this UL band if search band is bad
        if CvM > threshold_CvM:
            extra = min(sj_fmax, ul_fmax) - sj_fmin
            extra /= ul_fmax - ul_fmin
            frac_vetoed += extra
            # Start a new veto band if needed
            if veto_fmax < sj_fmin:
                veto_fmin = sj_fmin
                veto_band = ET.SubElement(veto_root, "veto_band")
                ET.SubElement(veto_band, "freq").text = str(sj_fmin)
                ET.SubElement(veto_band, "band").text = str(sj_fmax - sj_fmin)
            veto_fmax = sj_fmax
            veto_band.find("band").text = str(sj_fmax - veto_fmin)
        # Or update loudest nonvetoed if this search band is good
        else:
            if loudest_nonvetoed_2F < twoF:
                loudest_nonvetoed_2F = twoF
    # While this upper limit band ends within the search band
    # (this can happen if the search covers a large dynamic range)
    while sj_fmax > ul_fmax:
        # Set loudest 2F for this upper limit band
        ET.SubElement(upper_limit, 'loudest_2F').text = str(loudest_ul_2F)
        ET.SubElement(upper_limit, 'loudest_nonvetoed_2F').text = str(loudest_nonvetoed_2F)
        ET.SubElement(upper_limit, 'fraction_vetoed').text = str(frac_vetoed)
        # Make a new upper limit band
        upper_limit = ET.SubElement(ul_root, "upper_limit")
        ul_fmin = ul_fmax
        ul_fmax = ul_fmin + ul_band
        ul_job += 1
        ET.SubElement(upper_limit, "freq").text = str(ul_fmin)
        ET.SubElement(upper_limit, "band").text = str(ul_band)
        ET.SubElement(upper_limit, "job").text = str(ul_job)
        # New UL band has loudest 2F of this search job
        loudest_ul_2F = twoF
        frac_vetoed = 0
        # If this search job is vetoed, set vetoed band appropriately
        # ALMOST COPYPASTA
        if CvM > threshold_CvM:
            frac_vetoed = min(sj_fmax, ul_fmax) - max(sj_fmin, ul_fmin)
            frac_vetoed /= ul_fmax - ul_fmin
            loudest_nonvetoed_2F = 0
            # Start a new veto band if needed
            if veto_fmax < sj_fmin:
                veto_fmin = sj_fmin
                veto_band = ET.SubElement(veto_root, "veto_band")
                ET.SubElement(veto_band, "freq").text = str(sj_fmin)
                ET.SubElement(veto_band, "band").text = str(sj_fmax - sj_fmin)
            veto_fmax = sj_fmax
            veto_band.find("band").text = str(sj_fmax - veto_fmin)
        else:
            loudest_nonvetoed_2F = twoF

    # Get out of job subdirectory
    os.chdir("..")
    if int(job) % 100 == 0:
        print(job, flush=True)

# Set loudest event in last upper limit band
ET.SubElement(upper_limit, 'loudest_2F').text = str(loudest_ul_2F)
ET.SubElement(upper_limit, 'loudest_nonvetoed_2F').text = str(loudest_nonvetoed_2F)
ET.SubElement(upper_limit, 'fraction_vetoed').text = str(frac_vetoed)

# Rewrite search bands file
DrillBits.indent(search_jobs)
ET.ElementTree(search_jobs).write(basedir + '/search_bands.xml')

# Write upper limit bands file
DrillBits.indent(ul_root)
ET.ElementTree(ul_root).write(basedir + '/upper_limits.xml')

# Write veto bands file
DrillBits.indent(veto_root)
ET.ElementTree(veto_root).write(basedir + '/veto_bands.xml')
