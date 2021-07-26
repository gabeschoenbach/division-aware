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
@click.option('-aware', default=False)
@click.option('-acceptance', default='D')
def run_chain(epsilon, steps, aware, acceptance):
    graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")

    COUSUB_TYPE = "COUSUB"
    munis, nodes_by_muni = get_divisions(graph, COUSUB_TYPE)
    counties, nodes_by_county = get_divisions(graph, "COUNTYFP")

    run_name = f"{aware}_{acceptance}_{epsilon}_{steps}"
    print(f"Kicking off run: {run_name}")
    
    aware = aware == "true"
    POP_COL = "TOTPOP19"
    initial_partition = make_partition_from_districtr_csv("WI", graph, "WI1")
    ideal_population = sum(initial_partition.population.values()) / len(initial_partition)
    if aware:
        proposal = partial(recom,
                           pop_col = POP_COL,
                           pop_target = ideal_population,
                           epsilon = epsilon,
                           method = partial(division_bipartition_tree,
                                           division_tuples=[("COUNTYFP", 1), (COUSUB_TYPE, 1)],
                                           first_check_division=True),
                           node_repeats = 2)
    else:
        proposal = partial(recom,
                           pop_col=POP_COL,
                           pop_target=ideal_population,
                           epsilon=epsilon,
                           node_repeats=2)

    elections = ["GOV18", "SEN18", "PRES16", "SEN16", "GOV14", "PRES12", "SEN12", "GOV12"]
    acceptance_func = guided_acceptance_factory(elections, acceptance)
    if acceptance == "D":
        optimizing_func = D
    elif acceptance == "P1":
        optimizing_func = P1
    elif acceptance == "P2":
        optimizing_func = P2
    else:
        optimizing_func = len 
    
    chain = MarkovChain(
                        proposal = proposal,
                        constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                        accept = acceptance_func,
                        initial_state = initial_partition,
                        total_steps = steps)

    split_counties = []
    split_counties = []
    split_munis = []
    P1s = []
    P2s = []
    Ds = []
    best_score = optimizing_func(initial_partition, elections)
    best_plan = initial_partition
    for i, part in enumerate(chain):
        split_counties.append(num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP"))
        split_munis.append(num_division_splits(graph, part, munis, nodes_by_muni, division_col=COUSUB_TYPE))
        P1s.append(P1(part, elections))
        P2s.append(P2(part, elections))
        Ds.append(D(part, elections))

        if acceptance != "always":
            if optimizing_func(part, elections) <= best_score:
                best_score = optimizing_func(part, elections)
                best_plan = part
        
        if i % 1000 == 0:
            print(i)
    
    df = pd.DataFrame({'split_counties':split_counties, 
                       'split_munis':split_munis,
                       'P1s':P1s,
                       'P2s':P2s,
                       'Ds':Ds})
    print(f"Printing to {run_name}.csv")

    df.to_csv(f"outputs/{run_name}.csv", index_label="step")

    save_partition_as_districtr_csv(graph, best_plan, "Code-2", f"{run_name}_best")

if __name__=="__main__":
    run_chain()