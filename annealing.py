import gerrychain
from gerrychain import (
    MarkovChain,
    constraints,
    accept
)
from gerrychain.proposals import recom
from gerrychain.tree import recursive_seed_part, bipartition_tree
from functools import partial
from tqdm import tqdm
#import pandas as pd
import os
import click
import random
from division_aware import *
from acceptance import *

@click.command()
@click.option('-epsilon', default=0.02)
@click.option('-steps', default=10)
@click.option('-acceptance', default='D')
@click.option('-problem', default="ASSEMBLY")
def run_chain(epsilon, steps, acceptance, problem):
    threshold_P1 = 0.001
    threshold_P2 = 0.1
    graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")

    COUSUB_TYPE = "COUSUB"
    munis, nodes_by_muni = get_divisions(graph, COUSUB_TYPE)
    counties, nodes_by_county = get_divisions(graph, "COUNTYFP")

    seed_dict = {
        "ASSEMBLY":"WI_seed_0.5pct_plan",
        "SENATE":"WI_seed_state_senate_1pct",
        "CD":"WI_seed_congress_1pct"
    }
    if problem not in seed_dict.keys():
        raise ValueError(f"problem is {problem} and must be in {seed_dict.keys()}")
    
    run_name = f"{problem}_{acceptance}_{epsilon}_{steps}"
    print(f"Kicking off run: {run_name}")
    
    POP_COL = "TOTPOP19"
    initial_partition = make_partition_from_districtr_csv("WI", graph, seed_dict[problem])
    ideal_population = sum(initial_partition.population.values()) / len(initial_partition)

    proposal = partial(recom,
                       pop_col = POP_COL,
                       pop_target = ideal_population,
                       epsilon = epsilon,
                       method = partial(division_bipartition_tree,
                                        division_tuples=[("COUNTYFP", 1), (COUSUB_TYPE, 1)],
                                        first_check_division=True),
                       node_repeats = 2)

    elections = ["GOV18", "SEN18", "PRES16", "SEN16", "GOV14", "PRES12", "SEN12", "GOV12"]
    acceptance_func = guided_acceptance_factory(elections, steps, acceptance)
    
    chain = MarkovChain(
                        proposal = proposal,
                        constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                        accept = acceptance_func,
                        initial_state = initial_partition,
                        total_steps = steps)

    split_counties = []
    split_munis = []
    P1s = []
    P2s = []
    best_score = 1000
    best_part = initial_partition
    best_parts = []
    N = 10
    for i, part in enumerate(chain.with_progress_bar()):
        split_counties.append(num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP"))
        split_munis.append(num_division_splits(graph, part, munis, nodes_by_muni, division_col=COUSUB_TYPE))
        P1_score = P1(part, elections)
        P2_score = P2(part, elections)
        if acceptance == "P1":
            score = P1_score
        elif acceptance == "P2":
            score = P2_score
        else:
            raise ValueError(f"We should only be running acceptance = `P1` or `P2`. You have acceptance = {acceptance}")
        
        if len(best_parts) < N:
            best_parts.append((score, part))
        else:
            best_parts = sorted(best_parts, key=lambda x:x[0])
            if score < best_parts[-1][0]: # if current plan is better than the worst of our 10 saved plans
                best_parts.pop()
                best_parts.append((score, part))

        P1s.append(P1_score)
        P2s.append(P2_score)

        # if P1_score < threshold_P1 or P2_score < threshold_P2:
        #     save_partition_as_districtr_csv(graph, part, "Code-2", f"{acceptance}_{epsilon}_{i}", "annealing_assignments")
    
    for i, (score, plan) in enumerate(sorted(best_parts, key=lambda x:x[0])):
        print(f"Plan {i} has {acceptance} score of: {score:0.4f}")
        if not os.path.exists(f"annealing_assignments/{run_name}/"):
            os.makedirs(f"annealing_assignments/{run_name}/")
        save_partition_as_districtr_csv(graph, plan, "Code-2", f"{run_name}/best_{i}", "annealing_assignments")

    df = pd.DataFrame({'split_counties':split_counties, 
                       'split_munis':split_munis,
                       'P1s':P1s,
                       'P2s':P2s})

    print(f"Printing to {run_name}.csv")

    df.to_csv(f"annealing_outputs/{run_name}.csv", index_label="step")

if __name__=="__main__":
    run_chain()
