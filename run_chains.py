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

#graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")
#munis, nodes_by_muni = get_divisions(graph, "COUSUB_ID")
#counties, nodes_by_county = get_divisions(graph, "COUNTYFP")

@click.command()
@click.option('-epsilon', default=0.05)
@click.option('-steps', default=10)
@click.option('-first_check_division', default=True)
@click.option('-division_aware', default=True)
@click.option('-tuple_type', default="MUNI_PREF")
@click.option('-cousub_type', default="COUSUB_ID")
def run_chain(epsilon, steps, first_check_division, division_aware, tuple_type, cousub_type):

    graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")
    munis, nodes_by_muni = get_divisions(graph, cousub_type)
    counties, nodes_by_county = get_divisions(graph, "COUNTYFP")
    random.seed()
    division_aware = division_aware == "true"
    first_check_division = first_check_division == "true"
    print(f"Running a Markov Chain with:")
    print(f"DIVISION_AWARE = {division_aware}")
    print(f"TUPLE_TYPE = {tuple_type}")
    print(f"COUSUB_TYPE = {cousub_type}")
    print(f"FIRST_CHECK_DIVISION = {first_check_division}")
    print(f"EPSILON = {epsilon}")
    print(f"LENGTH = {steps}")
    run_name = f"{division_aware}_{tuple_type}_{first_check_division}_{cousub_type}_{epsilon}_{steps}"

    POP_COL = "TOTPOP19"
    if tuple_type == "COUNTYFP" or tuple_type == "COUSUB_ID" 
        if tuple_type == "COUNTYFP":
            division_tuples = [(tuple_type, 1)]
        else:
            division_tuples = [(cousub_type, 1)]
    elif tuple_type == "BOTH_EQUAL":
        division_tuples = [("COUNTYFP", 1), (cousub_type, 1)]
    elif tuple_type == "COUNTY_PREF":
        division_tuples = [("COUNTYFP", 2), (cousub_type, 1)]
    elif tuple_type == "MUNI_PREF":
        division_tuples = [("COUNTYFP", 1), (cousub_type, 2)]
    else:
        raise ValueError("ERROR: `tuple_type` needs to be one of 'COUNTYFP', COUSUB_ID', 'BOTH_EQUAL', 'COUNTY_PREF', or 'MUNI_PREF'.")

    initial_partition = make_partition_from_districtr_csv("WI", graph, "WI1")
    ideal_population = sum(initial_partition.population.values()) / len(initial_partition)
    if division_aware:
        proposal = partial(recom,
                           pop_col = POP_COL,
                           pop_target = ideal_population,
                           epsilon = epsilon,
                           method = partial(division_bipartition_tree,
                                           division_tuples=division_tuples,
                                           first_check_division = first_check_division),
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
    split_munis = []
    for i, part in enumerate(chain):
        split_counties.append(num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP"))
        split_munis.append(num_division_splits(graph, part, munis, nodes_by_muni, division_col=cousub_type))
        if i % 1000 == 0:
            print(i)

    df = pd.DataFrame({'split_counties':split_counties, 'split_munis':split_munis})
    print(f"Printing to {run_name}.csv")
    df.to_csv(f"outputs/{run_name}.csv", index_label="step")


if __name__=="__main__":
    run_chain()
