#!/bin/bash

cd search
jobs=`grep 'SBATCH --array=0-' submit.sh | sed 's/#SBATCH --array=0-//'`
maxsub=$(( $jobs/250 ))

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

        # If job is bad, skip
        if [[ ! -s "$sub/histogram.$job" ||
              ! -s "$sub/output.$job" ||
              -s "$sub/error.$job" ||
              ! `tail -1 $sub/histogram.$job | grep %DONE` ]]; then
            continue
        fi

	# Read middle frequency
	freq=`awk 'NR==14{print$8}' $sub/output.$job | awk -F : '{printf("%.4f\n",($1+$2)/2)}'`

	# Check last two lines
	twoF=`tail -2 $sub/histogram.$job | head -1 | awk '{printf("%.1f\n",$2)}'`

	echo $freq " " $twoF

    done # with this subdirectory

done # with all subdirectories
