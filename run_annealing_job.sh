#!/bin/bash

#SBATCH --job-name="anneal-pmc"
#SBATCH --time=6-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --mem=8000

python annealing.py -epsilon $1 -steps $2 -acceptance $3 
