for epsilon in 0.005 0.01 0.02
do
  for steps in 1500000 
  do
    for acceptance in "P1" "P2"
    do
      sbatch run_annealing_job.sh $epsilon $steps $acceptance 
    done
  done
done
