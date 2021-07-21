for epsilon in 0.02 0.05
do
  for steps in 100000 500000 
  do
    for first_check_division in "true" "false"
    do
      for division_aware in "true" "false"
      do
        for tuple_type in "COUSUB_ID" # "COUNTYFP" "COUSUB_ID" "BOTH_EQUAL" "COUNTY_PREF" "MUNI_PREF"
        do
          for cousub_type in "COUSUB" # "COUSUB_ID"
          do
            sbatch run_job.sh $epsilon $steps $first_check_division $division_aware $tuple_type $cousub_type
          done
        done
      done
    done
  done
done
