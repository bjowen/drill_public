#!/usr/bin/python3

import DrillBits
import os
import subprocess
import xml.etree.ElementTree as ET

# Read setup file
setup = ET.parse("setup.xml").getroot()
# Convert days to seconds.
span = int(float(setup.find("span").text) * 86400)
start = int(setup.find("start").text)

# Read config.xml for parameters.
config_file = setup.find("config_file").text
config = ET.parse(config_file).getroot()

# Read SFTs from run database.
db_file = config_file.replace("config.xml", "sft_database.xml")
sft_db = ET.parse(db_file).getroot()
all_sfts = sft_db.findall("sft")

# Make links to only the SFTs we need
subprocess.run(args=['rm', '-rf', 'sfts'])
subprocess.run(args=['mkdir', '-p', 'sfts'])
for sft in all_sfts:
    if int(sft.find('start').text) < start:
        continue
    if int(sft.find('start').text) > start + span - 1800:
        continue
    subprocess.run(args=['ln', '-s', sft.find('path').text, 'sfts'])

# Write array submit file
upper = ET.parse("upper_limits.xml").getroot()
jobs = upper.findall(".//upper_limit")
n=len(jobs)
subprocess.run(args=["mkdir", "-p", "upper"])
os.chdir("upper")
DrillBits.write_submit_array(None, "UpperLimit.py", n)
