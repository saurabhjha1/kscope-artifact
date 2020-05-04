#!/bin/bash
module unload boost
module load bwpy
module load PrgEnv-gnu
module load automake
module load autoconf


echo "Running probes on ${ALPS_APP_PE}"
python3 setup.py --init --config config --odir results
python3 setup.py --threads 64 --epoch_time 60 --total_runs 18 --config config  --odir results

