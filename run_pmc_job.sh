#!/bin/bash

#SBATCH --job-name="always-pmc"
#SBATCH --time=0-12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --mem=8000

python run_pmc_chains.py -epsilon $1 -steps $2 -aware $3 -acceptance $4 
