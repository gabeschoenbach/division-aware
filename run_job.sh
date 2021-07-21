#!/bin/bash

#SBATCH --job-name="division"
#SBATCH --time=1-12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --mem=24000

python run_chains.py -epsilon $1 -steps $2 -first_check_division $3 -division_aware $4 -tuple_type $5 -cousub_type $6
