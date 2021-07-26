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

@click.command()
@click.option('-epsilon', default=0.01)
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
    
    chain = MarkovChain(
                        proposal = proposal,
                        constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                        accept = accept.always_accept,
                        initial_state = initial_partition,
                        total_steps = steps)

    split_counties = []
    split_counties = []
    split_munis = []
    for i, part in enumerate(chain):
        split_counties.append(num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP"))
        split_munis.append(num_division_splits(graph, part, munis, nodes_by_muni, division_col=COUSUB_TYPE))
        if i % 1000 == 0:
            print(i)
    
    df = pd.DataFrame({'split_counties':split_counties, 'split_munis':split_munis})
    print(f"Printing to {run_name}.csv")
    df.to_csv(f"outputs/{run_name}.csv", index_label="step")

    if __name__=="__main__":
        run_chain()