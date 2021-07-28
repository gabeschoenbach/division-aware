for epsilon in 0.02 0.05
do
  for steps in 300000 
  do
    for aware in "true" "false"
    do
      for acceptance in "always" "D" "P1" "P2"
      do
        sbatch run_pmc_job.sh $epsilon $steps $aware $acceptance 
      done
    done
  done
done
