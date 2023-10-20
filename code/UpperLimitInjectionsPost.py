#!/usr/bin/python3

import DrillBits
import os
import xml.etree.ElementTree as ET

# Get injections per band
setup = ET.parse("setup.xml").getroot()
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
inj_per_band = int(config.find('upper_limits/inj_per_band').text)
try:
    new_uls = config.find("options/new_style_uls").text
except:
    new_uls = None

# Read upper limit bands
ul_root = ET.parse("upper_limits.xml").getroot()
ul_jobs = ul_root.findall(".//upper_limit")

# For each upper limit band
os.chdir('upper')
for job in ul_jobs:
    j = job.find('job').text
    # CHANGE TO READ RATHER THAN WRITE H0 VALUE
    try:
        f = open('upper_limit.txt.' + j, 'r')
        for line in f.readlines():
            for word in line.split():
                fields = word.split('=')
                if fields[0] == 'h0':
                    h0 = fields[1]
        if line != '%DONE\n':
            h0 = '0'
        else:
            print(job.find('freq').text + ' ' + h0)
        f.close()
    except:
        h0 = '0'
        continue

    if new_uls != None:
        loudest_2F = float(job.find('loudest_nonvetoed_2F').text)
    else:
        loudest_2F = float(job.find('loudest_2F').text)
    inj_found = 0
    inj_lost = 0
    for line in os.popen('cat injections/' + j + '/upper_limit_injections.txt.*').readlines():
        try:
            twoF = float(line)
        except:
            print('bad line ' + line)
        if twoF > loudest_2F:
            inj_found += 1
        else:
            inj_lost += 1
    if inj_found + inj_lost != inj_per_band:
        # SCREAM BLOODY MURDER INSTEAD
        fdr = 0
    else:
        fdr = inj_lost / float(inj_found + inj_lost)
    try:
        job.find('injections_fdr').text = str(fdr)
    except:
        ET.SubElement(job, 'injections_fdr').text = str(fdr)

# Write upper limit bands
os.chdir('..')
DrillBits.indent(ul_root)
ET.ElementTree(ul_root).write('upper_limits.xml')
