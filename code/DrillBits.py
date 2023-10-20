#!/usr/bin/python3
# by Ben Owen
# Common library for use with Python scripts in the Drill pipeline

import os

CODE = os.path.dirname(os.path.abspath(__file__))
JOBS_PER_DIR = 250

# from http://stackoverflow.com/questions/749796/pretty-printing-xml-in-python
def indent(elem, level=0):
    """This is a function to make the XML output pretty, with the right level
    of indentation"""
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def write_submit_array(pre, exe, tasks, sfile='submit.sh', time=4):
    """Write file to submit job array to Slurm queue"""
    # Open submit file
    sub = open(sfile, "w")
    # Write universal lines
    sub.write("#!/bin/bash\n")
    sub.write("#SBATCH --export=ALL\n")
    sub.write("#SBATCH --partition=nocona\n")
    sub.write("#SBATCH --nodes=1\n")
    sub.write("#SBATCH --ntasks=1\n")
    sub.write("#SBATCH --account=owen\n")
    sub.write("#SBATCH --time=" + str(time) + ":00:00\n")
    sub.write("#SBATCH --job-name=" + exe.split()[0] + "\n")
    sub.write("#SBATCH --error=/dev/null\n")
    sub.write("#SBATCH --output=/dev/null\n")
    # Write array lines
    if tasks > 1:
        sub.write("#SBATCH --array=0-" + str(tasks - 1) + "\n")
        if pre != None:
            sub.write(pre + "\n")
        sub.write(CODE + "/" + exe + " $SLURM_ARRAY_TASK_ID > output.$SLURM_ARRAY_TASK_ID 2> error.$SLURM_ARRAY_TASK_ID\n")
    # Write single job line
    else:
        if pre != None:
            sub.write(pre + "\n")
        sub.write(CODE + "/" + exe + " > output 2>error\n")
    # Clean up
    sub.close()

def write_submit_job(pre, exe):
    """Write file to submit single job to Slurm queue"""
    write_submit_array(pre, exe, 1)

