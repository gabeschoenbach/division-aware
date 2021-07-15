from gerrychain.updaters import Tally, cut_edges
from gerrychain.proposals import recom
from gerrychain import (
    Graph,
    Partition,
    Election,
    MarkovChain,
    constraints,
    accept
)
import pandas as pd
from functools import partial
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import click
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import  LineString, mapping
from gerrychain.tree import PopulatedGraph, recursive_tree_part, recursive_seed_part, predecessors, bipartition_tree, find_balanced_edge_cuts_memoization #  contract_leaves_until_balanced_or_none, 
from networkx.algorithms import tree
from collections import deque, namedtuple
import random
import math

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

def proportionality_score(partition, election):
    """
    Calculate the proportionality score of a given districting plan, election pair.

    Parameters:
    ----------
    partition: GerryChain Partition
        The districting plan on the state
    election: str
        The name of the election to be analyzed, from `states[state]["elections"]`
    """
    num_dists = len(partition)
    vote_share = partition[election].percent("Rep")
    seat_share = partition[election].wins("Rep") / num_dists
    return seat_share - vote_share

def is_proportional(partition, election, threshold=0.07):
    """
    Return True if the proportionality score has smaller magnitude than `threshold`.

    Parameters:
    ----------
    partition: GerryChain Partition
        The districting plan on the state
    election: str
        The name of the election to be analyzed, from `states[state]["elections"]`
    threshold: float
        The maximum allowed magnitude of proportionality score to be considered proportional
        default = 0.07 (per S.1. draft) 
    """
    return abs(proportionality_score(partition, election)) <= threshold

def is_proportional_score(partition, elections, threshold=0.07):
    """
    Return the number of elections on which this partition is proportional, relative to threshold.

    Parameters:
    ----------
    partition: GerryChain Partition
        The districting plan on the state
    elections: list of str
        The names of the elections to be analyzed, from `states[state]["elections"]`
    threshold: float
        The maximum allowed magnitude of proportionality score to be considered proportional
        default = 0.07 (per S.1. draft)
    """
    score = 0
    for election in elections:
        if is_proportional(partition, election, threshold):
            score += 1
    return score

def proportionality_vector(partition, elections):
    """
    Calculate the proportionality vector of a given districting plan.

    Parameters:
    ----------
    partition: GerryChain Partition
        The districting plan on the state
    elections: list of str
        The names of the elections to be analyzed, from `states[state]["elections"]`
    """
    v = []
    for elec in elections:
        v.append(proportionality_score(partition, elec))
    return v