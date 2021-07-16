#!/bin/bash

#SBATCH --job-name="guided-aware"
#SBATCH --time=0-20:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --mem=16000

python run_guided_aware_chains.py
