#!/usr/bin/python3

import DrillBits
import os
import xml.etree.ElementTree as ET

# Read upper limit bands
setup = ET.parse("setup.xml").getroot()
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()
jobs_per_band = int(config.find("./upper_limits/jobs_per_band").text)
ul_band = float(config.find("./upper_limits/band").text)
ul_root = ET.parse("upper_limits.xml").getroot()
ul_jobs = ul_root.findall(".//upper_limit")

# Read upper limit results files
os.chdir('upper')
for job in ul_jobs:
    j = job.find('job').text
    try:
        f = open('upper_limit.txt.' + j, 'r')
        for line in f.readlines():
            for word in line.split():
                fields = word.split('=')
                if fields[0] == 'h0':
                    h0 = fields[1]
        if line != '%DONE\n':
            h0 = '0'
        f.close()
    except:
        h0 = '0'
        continue
    try:
        job.find('h0').text = h0
    except:
        ET.SubElement(job, 'h0').text = h0

# Write injections submission file
os.system('mkdir -p injections')
DrillBits.write_submit_array(None, 'UpperLimitInjections.py', len(ul_jobs) * jobs_per_band, sfile='injections/submit_inj.sh', time=8)

# Write upper limit bands file
os.chdir('..')
DrillBits.indent(ul_root)
ET.ElementTree(ul_root).write('upper_limits.xml')
