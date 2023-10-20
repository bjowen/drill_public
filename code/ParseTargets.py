#!/usr/bin/python3
# by Ben Owen
# Parse astro target list and do basic prep of subdirectories

import DrillBits
import math
import os
import xml.etree.ElementTree as ET

cfg_file = os.path.abspath("config.xml")
cfg = ET.parse(cfg_file).getroot()

# Read astro targets file - only last line for now!
for line in open("astro-targets-converted.dat", "r").readlines():
    # Skip commented lines
    if line[0] == "#":
        continue
    field = line.split()

    # Read info
    name = field[0]

    # Read sky position and convert to radians
    rah = float(field[2])
    ram = float(field[3])
    ras = float(field[4])
    ra = math.radians(15*(rah + ram/60.0 + ras/3600.0))
    decd = float(field[5])
    decm = float(field[6])
    decs = float(field[7])
    dec = abs(decd) + decm/60.0 + decs/3600.0
    if decd < 0:
        dec = -dec
    dec = math.radians(dec)

    dkpc = float(field[8])
    akyr = float(field[9])

    # Go to that directory
    os.system("mkdir -p " + name)
    os.chdir(name)

    # Fill a subdirectory for each big band
    breaks = cfg.findall(".//band_breaks/freq")
    b_freqs = [el.text for el in breaks]
    for i in range(len(breaks)-1):
        band = b_freqs[i] + "-" + b_freqs[i+1] + "Hz"
        os.system("mkdir -p " + band)
        os.chdir(band)

        # Start setup file with a pointer back here
        setup = ET.Element("setup")
        ET.SubElement(setup, "config_file").text = cfg_file
        ET.SubElement(setup, "name").text = name

        # Write sky position in radians
        foo = ET.SubElement(setup, "ra")
        foo.text = str(ra)
        foo.set("comment", "radians")
        foo = ET.SubElement(setup, "dec")
        foo.text = str(dec)
        foo.set("comment", "radians")

        foo = ET.SubElement(setup, "distance")
        foo.text = str(dkpc * 1000 * 102927133.01)
        foo.set("comment", "seconds")
        foo = ET.SubElement(setup, "age")
        foo.text = str(akyr * 1000 * 365 * 86400)
        foo.set("comment", "seconds")

        foo = ET.SubElement(setup, "fmin")
        foo.text = b_freqs[i]
        foo.set("comment", "Hz")
        foo = ET.SubElement(setup, "fmax")
        foo.text = b_freqs[i+1]
        foo.set("comment", "Hz")

        # Make the span too short; it will be stepped up later.
        foo = ET.SubElement(setup, "span")
        foo.text = str(1.1)
        foo.set("comment", "days")
        foo = ET.SubElement(setup, "start")
        foo.text = "0"
        foo.set("comment", "GPS seconds")
        foo = ET.SubElement(setup, "n_sfts")
        foo.text = "0"

        # Write setup.xml
        DrillBits.indent(setup)
        ET.ElementTree(setup).write("setup.xml")

        os.chdir(os.path.pardir)

    os.chdir(os.path.pardir)
