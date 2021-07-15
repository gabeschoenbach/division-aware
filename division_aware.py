from networkx.algorithms import tree
from gerrychain import Graph, Election, Partition
from gerrychain.updaters import Tally
from gerrychain.tree import (
    PopulatedGraph,
    predecessors,
    successors,
    # contract_leaves_until_balanced_or_none,
    find_balanced_edge_cuts_memoization,
    Cut,
)
from collections import deque
import random
import pandas as pd
import os

def division_random_spanning_tree(graph, division_tuples=[("COUNTYFP10", 1)]):
    """
    Generates a spanning tree that discourages edges that cross divisions (counties, municipalities, etc).
    We probabilistically assign weights to every edge, and then draw a minumum spanning
    tree over the graph. This means that edges with lower weights will be preferred as the tree is drawn.

    Parameters:
    ----------
    graph: GerryChain Graph object
        The region upon which to draw the spanning tree (usually two districts merged together)
    division_tuples: list of (str, float)
        A list of tuples where the first element is the division column and the second element is
        the weight penalty added to any edge that spans two divisions of that type.
    """
    weights = {edge:1 for edge in graph.edges}
    for edge in graph.edges:
        for (division_col, penalty) in division_tuples:
            if graph.nodes[edge[0]][division_col] != graph.nodes[edge[1]][division_col]:
                weights[edge] += penalty
        graph.edges[edge]["weight"] = weights[edge] + random.random()

    spanning_tree = tree.minimum_spanning_tree(
        graph, algorithm="kruskal", weight="weight"
    )
    return spanning_tree

# def split_tree_at_division(h, choice=random.choice, division_col="COUNTYFP10"):
#     root = choice([x for x in h if h.degree(x) > 1])
#     # BFS predecessors for iteratively contracting leaves
#     pred = predecessors(h.graph, root)

#     leaves = deque(x for x in h if h.degree(x) == 1)
#     while len(leaves) > 0:
#         leaf = leaves.popleft()
#         parent = pred[leaf]
#         if h.graph.nodes[parent][division_col] != h.graph.nodes[leaf][division_col] and h.has_ideal_population(leaf):
#             return h.subsets[leaf]
#         # Contract the leaf:
#         h.contract_node(leaf, parent)
#         if h.degree(parent) == 1 and parent != root:
#             leaves.append(parent)
#     return None

def division_find_balanced_edge_cuts_memoization(h, choice=random.choice, division_col=None):
    root = choice([x for x in h if h.degree(x) > 1])
    pred = predecessors(h.graph, root)
    succ = successors(h.graph, root)
    total_pop = h.tot_pop
    subtree_pops = {}
    stack = deque(n for n in succ[root])
    while stack:
        next_node = stack.pop()
        if next_node not in subtree_pops:
            if next_node in succ:
                children = succ[next_node]
                if all(c in subtree_pops for c in children):
                    subtree_pops[next_node] = sum(subtree_pops[c] for c in children)
                    subtree_pops[next_node] += h.population[next_node]
                else:
                    stack.append(next_node)
                    for c in children:
                        if c not in subtree_pops:
                            stack.append(c)
            else:
                subtree_pops[next_node] = h.population[next_node]
    cuts = []
    for node, tree_pop in subtree_pops.items():
        def part_nodes(start):
            nodes = set()
            queue = deque([start])
            while queue:
                next_node = queue.pop()
                if next_node not in nodes:
                    nodes.add(next_node)
                    if next_node in succ:
                        for c in succ[next_node]:
                            if c not in nodes:
                                queue.append(c)
            return nodes

        is_balanced_A = abs(tree_pop - h.ideal_pop) <= h.ideal_pop * h.epsilon
        is_balanced_B = abs((total_pop - tree_pop) - h.ideal_pop) <= h.ideal_pop * h.epsilon # is_balanced_A <=> is_balanced_B ??

        parent = pred[node]
        if division_col is not None:
            is_balanced_A = (h.graph.nodes[parent][division_col] != h.graph.nodes[node][division_col]) and is_balanced_A
            is_balanced_B = (h.graph.nodes[parent][division_col] != h.graph.nodes[node][division_col]) and is_balanced_B

        if is_balanced_A:
            cuts.append(Cut(edge=(node, pred[node]), subset=part_nodes(node)))
        elif is_balanced_B:
            cuts.append(Cut(edge=(node, pred[node]), subset=set(h.graph.nodes) - part_nodes(node)))

    return cuts

def division_bipartition_tree(
    graph,
    pop_col,
    pop_target,
    epsilon,
    division_tuples=[("COUNTYFP10", 1)],
    first_check_division=False,
    node_repeats=1,
    spanning_tree=None,
    choice=random.choice,
    attempts_before_giveup = 100):

    if first_check_division and len(division_tuples) == 0:
        raise ValueError("first_check_division is True but no divisions are provided in division_tuples.")

    populations = {node: graph.nodes[node][pop_col] for node in graph}

    possible_cuts = []
    if spanning_tree is None:
        spanning_tree = division_random_spanning_tree(graph, division_tuples=division_tuples)
    restarts = 0
    counter = 0
    while len(possible_cuts) == 0 and counter < attempts_before_giveup:
        # print(counter)
        if restarts == node_repeats:
            spanning_tree = division_random_spanning_tree(graph, division_tuples=division_tuples)
            restarts = 0
            counter +=1
        h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
        if len(division_tuples) > 0 and first_check_division and restarts == 0:
            sorted_division_tuples = sorted(division_tuples, key=lambda x:x[1])
            preferred_division_col = sorted_division_tuples[-1][0]
            possible_cuts = division_find_balanced_edge_cuts_memoization(h, choice=choice, division_col=preferred_division_col)
        if len(possible_cuts) == 0:
            h = PopulatedGraph(spanning_tree, populations, pop_target, epsilon)
            possible_cuts = division_find_balanced_edge_cuts_memoization(h, choice=choice, division_col=None)
        restarts += 1

    if counter >= attempts_before_giveup:
        return set()
    return choice(possible_cuts).subset


def get_divisions(graph, division_col):
    divisions = set([graph.nodes[n][division_col] for n in graph.nodes])
    nodes_by_division = {
            division:[n for n in graph.nodes if graph.nodes[n][division_col] == division] \
            for division in divisions
    }
    return divisions, nodes_by_division

def num_division_splits(graph, partition, divisions, nodes_by_division, division_col="COUNTYFP"):
    """
    How many times a division (county) is touches multiple districts.
    SLOW!
    """
    splits = 0
    assignment = dict(partition.assignment)
    for division in divisions:
        districts = set()
        for node in nodes_by_division[division]:
            districts.add(assignment[node])
            if len(districts) > 1:
                splits += 1
                break
    return splits

def num_district_splits(graph, partition, division_col="COUNTYFP"):
    """
    How many times a district touches multiple divisions (counties).
    FAST!
    """
    splits = 0
    for (district, nodes) in partition.parts.items():
        divisions = set()
        for node in nodes:
            divisions.add(graph.nodes[node][division_col])
        if len(divisions) > 1:
            splits += 1
    return splits

VAP_COLUMNS = ["VAP", "HVAP", "WVAP", "BVAP", "AMINVAP", "ASIANVAP", "NHPIVAP", "OTHERVAP", "2MOREVAP"]

states = {
    "WI": {
        "elections": {
            "GOV18":["GOV18D", "GOV18R"],
            "SOS18":["SOS18D", "SOS18R"],
            "TRE18":["TRE18D", "TRE18R"],
            "SEN18":["SEN18D", "SEN18R"],
            "PRES16":["PRES16D", "PRES16R"],
            "SEN16":["SEN16D", "SEN16R"],
            "GOV14":["GOV14D", "GOV14R"],
            "SOS14":["SOS14D", "SOS14R"],
            "TRE14":["TRE14D", "TRE14R"],
            "AG14":["AG14D", "AG14R"],
            "GOV12":["GOV12D", "GOV12R"],
            "PRES12":["PRES12D", "PRES12R"],
            "SEN12":["SEN12D", "SEN12R"],
        },
        "POP_COL": "TOTPOP19",
        "ENACTED_COL": ["CD"],
    },
}

def make_partition_from_districtr_csv(state, graph, file, unit_col="Code-2"):
    df = pd.read_csv(f"assignments/{file}.csv", header=None)
    df.columns = [unit_col, "district"]
    unit_to_node = {graph.nodes[n][unit_col]:n for n in graph.nodes}
    unit_to_dist = dict(zip(df[unit_col], df["district"]))
    assignment = {unit_to_node[unit]:unit_to_dist[unit] for unit in unit_to_dist.keys()}
    
    POP_COL = states[state]["POP_COL"]
    elections = states[state]["elections"]
    updaters = {}
    updaters["population"] = Tally(POP_COL, alias="population")
    for VAP_COL in VAP_COLUMNS:
        updaters[VAP_COL] = Tally(VAP_COL)
    updaters["NH_WHITE"] = Tally("NH_WHITE")
    updaters["TOTPOP"] = Tally("TOTPOP")
    updaters["WHITE19"] = Tally("WHITE19")
    for elec in elections.keys():
        updaters[elec] = Election(elec,{"Dem":elections[elec][0], "Rep":elections[elec][1]})

    partition = Partition(graph, assignment=assignment, updaters=updaters)
    return partition

def save_partition_as_districtr_csv(graph, partition, unit_col, filename):
    unit_to_node = {graph.nodes[i][unit_col]:i for i in graph.nodes}
    assignment = partition.assignment
    csv = {}
    for n in graph.nodes:
        unit = graph.nodes[n][unit_col]
        unit_node = unit_to_node[unit]
        csv[unit] = partition.assignment[unit_node]
    
    if not os.path.exists("assignments/"):
        os.makedirs("assignments/")
    with open(f"assignments/{filename}.csv", "w") as f:
        for key in csv.keys():
            f.write(f"{key},{csv[key]}\n")
    f.close()
    return
