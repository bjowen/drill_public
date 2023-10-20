#!/usr/bin/python3
# by Ben Owen
# Set up search to meet a computational cost goal with fixed frequency bounds.
# Should be submitted as a batch job.
#
# Could use some restructuring. 3 pieces:
# 1. Finds optimal span for cost target, modulo options
# 2. Estimates sensitivity curve
# 3. Sets up search jobs

import DrillBits
import math
import numpy
import os
import scipy.special as special
import subprocess
import sys
import xml.etree.ElementTree as ET
from DrillBits import CODE
from DrillBits import JOBS_PER_DIR

# Number of template density interpolation bands (points - 1)
ibands = 10
# Fractional error allowed in final cost (modulo SFT boundaries)
cost_tolerance = 0.02

# Read setup.xml for parameters.
setup = ET.parse("setup.xml").getroot()
age = float(setup.find("age").text)
dec = float(setup.find("dec").text)
distance = float(setup.find("distance").text)
fmax = float(setup.find("fmax").text)
fmin = float(setup.find("fmin").text)
ra = setup.find("ra").text
# Convert days to seconds.
span = int(float(setup.find("span").text) * 86400)

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
benchmark = float(config.find("./cluster/benchmark").text)
cost_target = float(config.find("./searches/cost_target").text)
job_hours = int(config.find('./searches/job_hours').text)
#keep = config.find("./searches/keep_threshold").text
max_braking = int(config.find("./searches/max_braking").text)
min_braking = int(config.find("./searches/min_braking").text)
mismatch = config.find("./searches/mismatch").text
p_fa = float(config.find('./searches/false_alarm').text)
p_fd = float(config.find('./upper_limits/false_dismissal').text)
# Check for psd file
try:
    psd_file = config.find('./options/psd_file').text
except:
    pass
rmw = config.find('./searches/running_median_window').text
run_stop = int(config.find("./data/stop").text)
# Check for span target option and convert days to seconds
try:
    span_target = int(float(config.find("./options/span_target").text) * 86400)
except:
    span_target = 0
try:
    start_target = int(config.find("./options/start_target").text)
except:
    start_target = 0
ul_band = float(config.find('./upper_limits/band').text)

# Figure out integer ordinal of band this search covers.
breaks = config.findall(".//band_breaks/freq")
b_freqs = [float(el.text) for el in breaks]
n_band = b_freqs.index(fmin)
# Here are the SFT links.
sft_glob = config_file.replace("config.xml", "sfts/*.sft")

# CHECK PARAMETER INTEGRITY HERE OR AFTER CHANGE?

### Find optimal SFT stretch for cost target.

# Iterate to find span. Also n_sfts, cost, n_tmpl
def find_span():
    global cost, cost_target, n_sfts, n_tmpl, setup, span

    old_span = 0
    # This variable checks for two-value race conditions.
    older_span = 0
    while True:
        iterate_span()
        print("span=" + str(float(span) / 86400) + " sfts=" + str(n_sfts) + " cost=" + str(cost) + " n_tmpl=" + str(n_tmpl), flush=True)
        DrillBits.indent(setup)
        ET.ElementTree(setup).write("setup.xml")

        # Stop if we're close to cost target or stalled
        if old_span == span:
            break
        if cost >= (1-cost_tolerance) * cost_target and cost <= (1+cost_tolerance) * cost_target:
            break

        # If 2-value race, try averaging
        # 3-VALUE RACE CAN HAPPEN! HOW TO BREAK OUT?
        if older_span == span:
            new_span = int((span + old_span)/2)
        # Adjust span assuming flattish scaling.
        else:
            new_span = int(span * pow(cost_target / cost, 0.2))

        older_span = old_span
        old_span = span
        span = new_span

# Changes span to fall on an SFT boundary.
def iterate_span():
    global all_sfts, config_file, n_band, run_stop, span
    global fmax, fmin, setup, sft_glob
    global best_start, cost, n_sfts, n_tmpl
    global dens

    # Read SFTs from run database.
    db_file = config_file.replace("config.xml", "sft_database.xml")
    sft_db = ET.parse(db_file).getroot()
    all_sfts = sft_db.findall("sft")

    # Find optimal span, unless start_target option is set
    # Loop over all SFTs, which should be ordered by start time.
    best_weight = 1
    for start_sft in all_sfts:

        # Stop if span will overflow the end of the run.
        start = int(start_sft.find("start").text)
        if (start > run_stop - span):
            break

        # Sum weights over those SFTs fully within span after start_sft.
        weight = 0
        my_n_sfts = 0
        here = all_sfts.index(start_sft)
        for sft in all_sfts[here:]:
            sft_start = int(sft.find("start").text)
            if (sft_start > start + span - 1800):
# Uncomment below to emulate legacy code
#            if (sft_start > start + span):
                break
            # Declination weight from Jaranowski, Krolak, & Schutz (1998)
            ifo = sft.find("ifo").text
            if ifo == "H1":
                lat = math.radians(46.45)
                gam = math.radians(171.8)
            if ifo == "L1":
                lat = math.radians(30.56)
                gam = math.radians(243.0)
            if ifo == "V1":
                lat = math.radians(43.63)
                gam = math.radians(116.5)
            j1 = 4 - 20 * math.pow(math.cos(lat), 2) + 35 * math.pow(math.sin(2*gam), 2) * math.pow(math.cos(lat), 4)
            j1 /= 256
            j2 = 68 - 20 * math.pow(math.cos(lat), 2) - 13 * math.pow(math.sin(2*gam), 2) * math.pow(math.cos(lat), 4)
            j2 /= 1024
            j3 = 28 - 44 * math.pow(math.cos(lat), 2) + 5 * math.pow(math.sin(2*gam), 2) * math.pow(math.cos(lat), 4)
            j3 /= 128
            e2 = 4 * j2 - j3 * math.cos(2*dec) + j1 * math.pow(math.cos(2*dec), 2)
            weight += e2/[float(el.text) for el in sft.findall("power")][n_band]
            my_n_sfts += 1
            stop_sft = sft
        weight = 1/weight

        # Hack: set weight=0 if we are on start_target
        if start == start_target:
            weight = 0

        # Update if we have a new winner.
        if weight < best_weight:
            best_weight = weight
            best_start = start
            best_start_sft = start_sft
            n_sfts = my_n_sfts
            best_stop = int(stop_sft.find("start").text) + 1800

    # Record results.
    span = best_stop - best_start
    setup.find("span").text = str(float(span) / 86400)
    setup.find("start").text = str(best_start)
    setup.find("n_sfts").text = str(n_sfts)

    # Calculate interpolation table of template density vs frequency.
    # COULD THIS BE PARALLELIZED?
    logband = math.log(fmax / fmin)
    dens = []
    for f in range(ibands + 1):
        freq = fmin * math.exp(f * logband / ibands)
        band = 1e-4*(100/float(freq))
# CHECK IF METRIC TYPE IS REALLY CORRECT
        with open("cfs_args.txt", "w") as ca:
            ca.write("Alpha=" + ra + "\n")
            ca.write("Delta=" + str(dec) + "\n")
            ca.write("Freq=" + str(freq) + "\n")
            ca.write("FreqBand=" + str(band) + "\n")
            ca.write("DataFiles=" + sft_glob + "\n")
#            ca.write("TwoFthreshold=" + keep + "\n")
            ca.write("gridType=9\n")
            ca.write("metricType=1\n")
            ca.write("metricMismatch=" + mismatch + "\n")
            ca.write("outputLogFile=/dev/null\n")
            ca.write("outputFstat=/dev/null\n")
            ca.write("outputLoudest=/dev/null\n")
            ca.write("minStartTime=" + str(best_start) + "\n")
            ca.write("maxStartTime=" + str(best_start + span - 1800) + "\n")
            ca.write("countTemplates=TRUE\n")
            ca.write("spindownAge=" + str(age) + "\n")
            ca.write("minBraking=" + str(min_braking) + "\n")
            ca.write("maxBraking=" + str(max_braking) + "\n")
            ca.write("RngMedWindow=" + rmw + "\n")
            ca.write("outputSingleFstats=YES\n")
        for line in subprocess.Popen(args = [CODE + "/bin/lalapps_ComputeFstatistic_v2", "@cfs_args.txt"], stdout = subprocess.PIPE).stdout.readlines():
            words = str(line, 'utf-8').split()
            if words[0] == '%%' and words[1] == 'Number' and words[2] == 'of' and words[3] == 'templates:':
                tmpl_dens = float(words[4]) / band
        dens.append(tmpl_dens)

    # Manually integrate total template count assuming linear density.
    n_tmpl = 0
    for f in range(ibands):
        freq1 = fmin * math.exp(f * logband / ibands)
        freq2 = fmin * math.exp((f+1) * logband / ibands)
        k = math.log( dens[f+1] / dens[f] ) / math.log( freq2 / freq1 )
        n_tmpl += freq1 * (dens[f+1] * freq2 / freq1 - dens[f]) / (k+1)
    # Convert from core-seconds to core-hours.
    cost = n_tmpl * n_sfts * benchmark / 3600

if span_target == 0:
    find_span()
else:
    span = span_target
    iterate_span()
    print("span=" + str(float(span) / 86400) + " sfts=" + str(n_sfts) + " cost=" + str(cost) + " n_tmpl=" + str(n_tmpl), flush=True)
    DrillBits.indent(setup)
    ET.ElementTree(setup).write("setup.xml")

### Estimate sensitivity.

# Compute Karl's rhobar factor.
eta_0 = special.erfcinv(2*p_fa / n_tmpl)
lambda_0 = -special.lambertw(-math.exp(-1 - eta_0*eta_0/2), -1)
lambda_0 = float(lambda_0.real)
eta = eta_0 + math.log(eta_0 / (lambda_0 - 1)) / (2*eta_0)
s_fa = 4*lambda_0
z_fa = (s_fa - 4) / pow(8, 0.5)
q = pow(2, 0.5) * special.erfcinv(2*p_fd)
Q = (4 + z_fa * pow(32, 0.5)) / (2*q*q)
rhobar = pow(8, 0.5) * z_fa
rhobar += 2*q*q * (1 + pow(1 + Q, 0.5))
rhobar = pow(rhobar, 0.5)
print("rhobar=" + str(rhobar))

# Karl's iterative rhohat function
def rhohat(rho0):
    global p_fa, p_fd, rhobar
    xi_1 = math.sqrt(2 * math.sqrt(2 + 0.8*(rhobar / rho0)**2) - 3)
    Gamma = 1 - 1 / math.log(2*p_fd) + 2 / (1 + 2*math.log(2*p_fd))
    Delta = 1 / (1 + 2*math.log(2*p_fd)) + 2 / (1 + 2*math.log(2*p_fd))**2
    Xi = 2 / xi_1 * math.sqrt( -math.log(2*p_fd) / math.pi)
    p_fd1 = p_fd * Xi / pow(2*p_fd * Xi, Delta)
    z_fa1 = z_fa * Gamma
    N_s1 = Gamma**2
# THIS PROBABLY SHOULD CHANGE FOR A DIRECTED SEARCH
    R_0 = math.sqrt(5.0/16)
    q1 = math.sqrt(2) * special.erfcinv(2*p_fd1)
    return 1 / R_0 * pow(8/N_s1, 0.25) * math.sqrt(z_fa1 + q1*math.sqrt(1 + z_fa1*math.sqrt(2/N_s1)) + q1*q1 / math.sqrt(2*N_s1))

# Find rhohat.
rhohatm2 = 1.4 * rhobar
rhohatm1 = rhohat(rhohatm2)
# NEED TO AVERAGE TO DAMP OSCILLATIONS
while True:
    newrhohat = rhohat((rhohatm1 + rhohatm2)/2)
    if abs(newrhohat / rhohatm1 - 1) < 0.01:
        break;
    rhohatm2 = rhohatm1
    rhohatm1 = newrhohat
print("rhohat=" + str(newrhohat))

# DO ONE IFO AT A TIME?
# RECORD PSDS IN FILES?
# FORCES INTEGER FMIN AND FMAX, ASSUMES FMAX-FMIN IS MULTIPLE OF 5
# Estimate sensitivity with psd file if it exists
try:
    pf = open(config_file.replace('config.xml', psd_file), 'r')
    for line in pf.readlines():
    # body of this for loop is mostly copypasta from below
        words = line.split()
        if words[0] == "%%":
            continue
        freq = float(words[0])
        if freq < fmin or freq > fmax:
            continue
# INCLUDE DEC SOME TIME
        h0 = 2.5*newrhohat * math.sqrt(float(words[1]) / n_sfts / 1800)
        eps = h0 / numpy.power(2*math.pi * freq, 2) * distance / 1e45
        eps *= numpy.power(2.99792458e10, 5) / 6.67e-8
        a = 0.028 * h0 / 1e-24 * distance / 1.029e11 * numpy.power(100 / freq, 3)
        print(str(freq) + " " + str(h0) + " " + str(eps) + " " + str(a))
# Else estimate sensitivity with stretch SFTs
except:
    step = 5
    for freq in range(int(fmin), int(fmax), step):
        with open("cpsd_args.txt", "w") as ca:
            ca.write("inputData=" + sft_glob + "\n")
            ca.write("startTime=" + str(best_start) + "\n")
            ca.write("endTime=" + str(best_start + span - 1800) + "\n")
            ca.write("outputPSD=/dev/stdout\n")
            ca.write("Freq=" + str(freq) + "\n")
            ca.write("FreqBand=" + str(step) + "\n")
            ca.write("binSizeHz=" + str(ul_band) + "\n")
        for line in subprocess.Popen(args = [CODE + "/bin/lalapps_ComputePSD", "@cpsd_args.txt"], stdout = subprocess.PIPE).stdout.readlines():
            words = str(line, 'utf-8').split()
            if words[0] == "%%":
                continue
            freq = float(words[0])
# INCLUDE DEC SOME TIME
            h0 = 2.5*newrhohat * math.sqrt(float(words[1]) / n_sfts / 1800)
            print(str(freq) + " " + str(h0))
    print(sft_glob)

# Print age-based indirect limit
print(str( math.sqrt(5e45/8*6.674e-8/29979245800**5/age) / distance))

# Use last template density interpolation table to set up search jobs
templates_per_job = job_hours * 3600 / benchmark / n_sfts

def density(ff, xx, yy):
    logf = numpy.log10(ff)
    logx = numpy.log10(xx)
    logy = numpy.log10(yy)
    return numpy.power(10.0, numpy.interp(logf, logx, logy))

# THIS IS COPYPASTA
logband = math.log(fmax / fmin)
# RECREATE ARRAY OF DENS FREQUENCIES, SHOULD MERGE
freqs = []
for i in range(ibands + 1):
    freqs.append(fmin * math.exp(i * logband / ibands))

# Set up search bands database
f = fmin
root_job = ET.Element('search_jobs')
n = 0
while f < fmax:
    df = templates_per_job / density(f, freqs, dens)
    if f + df > fmax:
        df = fmax - f
    # Write info to search
    job = ET.SubElement(root_job, 'search_job')
    ET.SubElement(job, 'job').text = str(n)
    ET.SubElement(job, 'freq').text = str(f)
    ET.SubElement(job, 'band').text = str(df)
    f += df
    n += 1
# Write it out
DrillBits.indent(root_job)
ET.ElementTree(root_job).write('search_bands.xml')

# Write search submit file
subprocess.run(args=["mkdir", "-p", "search"])
os.chdir("search")
for d in range(1 + int( (n-1) / JOBS_PER_DIR )):
    subprocess.run(args=["mkdir", "-p", str(d)])
DrillBits.write_submit_array("Dir=$(( $SLURM_ARRAY_TASK_ID / " + str(JOBS_PER_DIR) + " ))\ncd $Dir", "Search.py", n, time=job_hours)
