for epsilon in 0.02 0.05
do
  for steps in 1000 
  do
    for first_check_division in "true" "false"
    do
      for division_aware in "true" "false"
      do
        for tuple_type in "COUNTYFP" "COUSUB_ID" "BOTH_EQUAL" "COUNTY_PREF" "MUNI_PREF"
        do
          sbatch run_job.sh $epsilon $steps $first_check_division $division_aware $tuple_type
        done
      done
    done
  done
done
