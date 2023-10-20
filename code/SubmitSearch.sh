#!/bin/bash
# by Ben Owen
# Instead of a simple sbatch, this checks for bad jobs and includes them in the
# list to run. USE ONLY WHEN NO JOBS ARE RUNNING!

cd search
jobs=`grep 'SBATCH --array=0-' submit.sh | sed 's/#SBATCH --array=0-//'`
jobs=$(( jobs+1 ))
maxsub=$(( $jobs/250 ))

# Initialize list of bad jobs
list=""
badjobs=0
# For each subdirectory of 250 jobs (250 is hard coded)
for sub in `ls | grep "^[0-9]\+$" | sort -n`; do

    # Figure out which jobs should be in this subdirectory
    minjob=$(( $sub*250 ))
    if [[ $sub -eq $maxsub ]]; then
        maxjob=$(( jobs-1 ))
    else
        maxjob=$(( $sub*250+249 ))
    fi

    # For each job in this subdirectory
    for job in `seq $minjob $maxjob`; do

        # If job is good, skip
        if [[ -s "$sub/histogram.$job" &&
              -s "$sub/output.$job" &&
              ! -s "$sub/error.$job" &&
              `tail -1 $sub/histogram.$job | grep %DONE` ]]; then
            continue
        fi
	# Else add one to bad job counter
	((++badjobs))

        # If this is the first bad job, start list
        if [[ $list == "" ]]; then
            list="$job"
            continue
        fi

        # Format list. Must end with a number which we'll compare to previous
        prev=$(($job-1))
        rx="$prev$"
        # If list does not end with previous job number
        if [[ ! $list =~ $rx ]]; then
            # Append comma then this job
            list="$list,$job"
        else
            # If list ends with dash then previous job number
            rx="-$prev$"
            if [[ $list =~ $rx ]]; then
                # Replace previous job with this job
                list=`echo $list | sed "s/$prev/$job/"`
            # Else list ends with comma previous or just previous
            else
                # Append dash then this job
                list="$list-$job"
            fi
        fi

    # Don't submit too many bad jobs at once
    if [[ $badjobs -gt 1995 ]]; then
	# NEED TO CLEAN UP END OF STRING FIRST!
	break 2
    fi

    done # with this subdirectory

done # with all subdirectories

# If there are any bad jobs submit an array job for this subdirectory
if [[ $badjobs -gt 0 ]]; then
    echo "total $badjobs " $list
#    sbatch --array=$list submit.sh
fi
