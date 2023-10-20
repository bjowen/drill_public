#!/bin/bash
# by Ben Owen
# Run this as the main script for CW drill code.

# Remember code directory.
CODE=`dirname $0`

# Echo and then execute a command
cmd() {
	echo $1
	$1
}

# Submits a no-argument Python script to the queue. Arguments are for sbatch
# only.
# Prolog and epilog are disabled on nocona, so do manually.
submit() {
    b=`basename $1`
    cat <<EOF > $b.sub
#!/bin/bash
#SBATCH --export=ALL
#SBATCH --partition=nocona
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --account=owen
#SBATCH --time=24:00:00
#SBATCH --error=error
#SBATCH --output=output
EOF
    for i in `seq 2 $#`; do
	echo "#SBATCH" ${!i} >>$b.sub
    done
    echo "#SBATCH --job-name=$b" >>$b.sub
    echo $1 >>$b.sub
    echo "sbatch $b.sub"
    sbatch $b.sub
}

# If no arguments, list steps and ask for one.
echo ""
if [ $# == 0 ]; then
    echo "Guide to the drill:"
    echo ""
    echo "Step 0 installs LAL software etc"
    echo "Step 1 scans the science run or whatever your SFT directory covers"
    echo "Step 2 runs a benchmark"
    echo "Step 3 parses the target list and preps subdirectories"
    echo "Step 4 sets up a search with the budgeted computing cost"
    echo "Step 5 runs, checks up on, or reruns a search"
    echo "Step 6 collates search results and writes vetoes"
    echo "Step 7 writes candidates and prepares to re-search them"
    echo "Step 8 runs upper limits"
    echo "Step 9 runs injections to test the upper limits"
    echo "Step 10 collates that and finishes up"
    echo "Step 11 computes noise PSD and sensitivity depth"
    echo ""
    read -p "Which step would you like to run? " step
    echo ""
else
    step=$1
fi

case $step in
    0)
        $CODE/InstallLALSuite.sh
        ;;
    1)
	# This makes jobs/ScanRun after checking config.xml.
	cmd "$CODE/ScanRunPre.py"
	# Pre must run w/o batch so that directory will surely exist.
	cmd "cd jobs/ScanRun"
	echo "sbatch --parsable submit.sh"
        job=`sbatch --parsable submit.sh`
	# ADAPT SUBMIT FOR THIS? OR HAVE PRE WRITE POST SUBMIT?
	cmd "sbatch --dependency=afterok:$job --export=ALL --partition=nocona --nodes=1 --ntasks=1 $CODE/ScanRunPost.py"
        ;;
    2)
	submit $CODE/Benchmark.py
	;;
    3)
        cmd "$CODE/ParseTargets.py"
        ;;
    4)
	HERE=$PWD
	for d in $(find . -name 'setup.xml' | xargs dirname)
	do
	    cd $d
            submit $CODE/SetupSearch.py
	    cd $HERE
	done
        ;;
    5)
	cd search && sbatch submit.sh
	;;
    6)
	submit $CODE/SearchPost.py
	;;
    7)
	submit $CODE/ResearchPre.py
	;;
    8)
	$CODE/UpperLimitPre.py
	cd upper && sbatch submit.sh
	;;
    9)
        $CODE/UpperLimitPost.py
	cd upper/injections && sbatch submit_inj.sh
	;;
    10)
    	$CODE/UpperLimitInjectionsPost.py
	;;
    11)
	submit $CODE/SensitivityDepth.py
	;;
    *)
        echo "What step was that?"
esac
echo ""
