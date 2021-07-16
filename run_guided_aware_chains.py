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
import pandas as pd
import os
import click
import random
from division_aware import *
import matplotlib.pyplot as plt
from utilities import *

graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")
munis, nodes_by_muni = get_divisions(graph, "COUSUB_ID")
counties, nodes_by_county = get_divisions(graph, "COUNTYFP")

epsilon = 0.02
steps = 200000 
first_check_division = True
POP_COL = "TOTPOP19"
division_tuples = [("COUNTYFP", 2), ("COUSUB_ID", 1)]
    
def L1(vec):
    return sum(abs(v) for v in vec)

def guided_acceptance_factory(elections):

    def accept_more_proportional(partition):
        parent = partition.parent
        child_v = proportionality_vector(partition, elections)
        parent_v = proportionality_vector(parent, elections)
        child_score = L1(child_v)
        parent_score = L1(parent_v)
        probability = min([1*math.exp(30*(parent_score - child_score)), 1])
        if random.random() < probability:
            return True
        else:
            return False
    return accept_more_proportional

def anti_guided_acceptance_factory(elections):

    def accept_less_proportional(partition):
        parent = partition.parent
        child_v = proportionality_vector(partition, elections)
        parent_v = proportionality_vector(parent, elections)
        child_score = L1(child_v)
        parent_score = L1(parent_v)
        probability = min([1*math.exp(-30*(parent_score - child_score)), 1])
        if random.random() < probability:
            return True
        else:
            return False
    return accept_less_proportional


initial_partition = make_partition_from_districtr_csv("WI", graph, "WI1")
ideal_population = sum(initial_partition.population.values()) / len(initial_partition)

proposal = partial(recom,
                   pop_col = POP_COL,
                   pop_target = ideal_population,
                   epsilon = epsilon,
                   method = partial(division_bipartition_tree,
                                   division_tuples=division_tuples,
                                   first_check_division = first_check_division),
                   node_repeats = 2)

elections = states["WI"]["elections"].keys()
pro_acceptance = guided_acceptance_factory(elections)
anti_acceptance = anti_guided_acceptance_factory(elections)

neutral_chain = MarkovChain(
                    proposal = proposal,
                    constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                    accept = accept.always_accept,
                    initial_state = initial_partition,
                    total_steps = steps)

guided_pro_chain = MarkovChain(
                    proposal = proposal,
                    constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                    accept = pro_acceptance,
                    initial_state = initial_partition,
                    total_steps = steps)

guided_anti_chain = MarkovChain(
                    proposal = proposal,
                    constraints = [constraints.within_percent_of_ideal_population(initial_partition, epsilon)],
                    accept = anti_acceptance,
                    initial_state = initial_partition,
                    total_steps = steps)

split_counties = []
split_munis = []
proportionality_L1s = []
best_neutral_plan = None
lowest_L1 = None
for i, part in enumerate(neutral_chain.with_progress_bar()):
    num_split_counties = num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP")
    num_split_munis = num_division_splits(graph, part, munis, nodes_by_muni, division_col="COUSUB_ID")
    proportionality_L1 = L1(proportionality_vector(part, elections))
    split_counties.append(num_split_counties)
    split_munis.append(num_split_munis)
    proportionality_L1s.append(proportionality_L1)
    if lowest_L1 is None or proportionality_L1 <= lowest_L1:
        lowest_L1 = proportionality_L1
        best_neutral_plan = part
df = pd.DataFrame(proportionality_L1s)
df.to_csv('./chain_proportionalities/neutral_L1s.csv', index=False)
df = pd.DataFrame(split_counties)
df.to_csv('./chain_proportionalities/neutral_split_counties.csv', index=False)
df = pd.DataFrame(split_munis)
df.to_csv('./chain_proportionalities/neutral_split_munis.csv', index=False)
save_partition_as_districtr_csv(graph, best_neutral_plan, "Code-2", "best_neutral_plan")

split_counties = []
split_munis = []
proportionality_L1s = []
best_pro_plan = None
lowest_L1 = None
for i, part in enumerate(guided_pro_chain.with_progress_bar()):
    num_split_counties = num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP")
    num_split_munis = num_division_splits(graph, part, munis, nodes_by_muni, division_col="COUSUB_ID")
    split_counties.append(num_split_counties)
    split_munis.append(num_split_munis)
    proportionality_L1 = L1(proportionality_vector(part, elections))
    proportionality_L1s.append(proportionality_L1)
    if lowest_L1 is None or proportionality_L1 <= lowest_L1:
        lowest_L1 = proportionality_L1
        best_pro_plan = part
df = pd.DataFrame(proportionality_L1s)
df.to_csv('./chain_proportionalities/pro_L1s.csv', index=False)
df = pd.DataFrame(split_counties)
df.to_csv('./chain_proportionalities/pro_split_counties.csv', index=False)
df = pd.DataFrame(split_munis)
df.to_csv('./chain_proportionalities/pro_split_munis.csv', index=False)    
save_partition_as_districtr_csv(graph, best_pro_plan, "Code-2", "best_pro_plan")
    
split_counties = []
split_munis = []
proportionality_L1s = []
worst_anti_plan = None
highest_L1 = None
for i, part in enumerate(guided_anti_chain.with_progress_bar()):
    num_split_counties = num_division_splits(graph, part, counties, nodes_by_county, division_col="COUNTYFP")
    num_split_munis = num_division_splits(graph, part, munis, nodes_by_muni, division_col="COUSUB_ID")
    split_counties.append(num_split_counties)
    split_munis.append(num_split_munis)
    proportionality_L1 = L1(proportionality_vector(part, elections))
    proportionality_L1s.append(proportionality_L1)
    if highest_L1 is None or proportionality_L1 >= highest_L1:
        highest_L1 = proportionality_L1
        worst_anti_plan = part
df = pd.DataFrame(proportionality_L1s)
df.to_csv('./chain_proportionalities/anti_L1s.csv', index=False)
df = pd.DataFrame(split_counties)
df.to_csv('./chain_proportionalities/anti_split_counties.csv', index=False)
df = pd.DataFrame(split_munis)
df.to_csv('./chain_proportionalities/anti_split_munis.csv', index=False)

save_partition_as_districtr_csv(graph, worst_anti_plan, "Code-2", "worst_anti_plan")
