#!/usr/bin/env python3

import sys
from division_aware import *
import math
from acceptance import P1, P2, D

def get_seat_shares(partition, elections):
    return [partition[election].wins("Rep") / len(partition) for election in elections]

def get_vote_shares(partition, elections):
    return [partition[election].percent("Rep") for election in elections]

def num_POCVAP(partition, threshold=0.4):
    wvap_pcts = {d:partition["WHITE19"][d]/partition["population"][d] for d in partition["population"].keys()}
    return len([p for p in wvap_pcts.values() if p < (1-threshold)])

graph = Graph.from_json("shapes/wisconsin2020_graph_cousub.json")
munis, nodes_by_muni = get_divisions(graph, "COUSUB")
counties, nodes_by_county = get_divisions(graph, "COUNTYFP")
elections = ["GOV12", "SEN12", "PRES12", "GOV14", "SEN16", "PRES16", "GOV18", "SEN18"]

enacted_plan = make_partition_from_districtr_csv("WI", graph, "WI_enacted")
R_vote_share = sum(get_vote_shares(enacted_plan, elections))/len(elections)
proportional_R_seats = R_vote_share * (len(elections) * len(enacted_plan))

for arg in sys.argv[1:]:
    partition = make_partition_from_districtr_csv("WI", graph, arg)
    cut_edges = len(partition.cut_edges)
    split_counties = num_division_splits(graph, partition, counties, nodes_by_county, division_col='COUNTYFP')
    split_munis = num_division_splits(graph, partition, munis, nodes_by_muni, division_col='COUSUB')
    R_won_seats = sum([partition[election].wins("Rep") for election in elections])
    R_excess_seats = R_won_seats - proportional_R_seats
    
    abs_excess_seats = [abs(partition[election].wins("Rep") - (partition[election].percent("Rep") * len(partition))) for election in elections]
    abs_excess_over_8 = sum(abs_excess_seats)
    abs_ave_excess = abs_excess_over_8 / len(abs_excess_seats)
    
    num_POC_dists = num_POCVAP(partition)
    
    my_P1 = P1(partition, elections)
    my_P2 = P2(partition, elections)
    my_D = D(partition, elections)
    
    # print(f"\n{arg}\n  Cut edges: {cut_edges}\n  Split counties: {split_counties}\n  Split munis: {split_munis}\n  R-won seats: {R_won_seats}\n  R excess seats over proportionality: {round(R_excess_seats)}\n  Average absolute excess seats in one election: {round(abs_ave_excess)}\n  Absolute excess seats over 8 elections: {round(abs_excess_over_8)}\n  Number of districts with >40% POC: {num_POC_dists}\n  P1: {my_P1:.3f}\n  P2: {my_P2:.3f}\n  D: {my_D:.3f}")

    print(f"\n{arg}\n  R-won seats: {R_won_seats}\n  R excess seats over proportionality: {round(R_excess_seats)}\n  Average absolute excess seats in one election: {round(abs_ave_excess)}\n  Absolute excess seats over 8 elections: {round(abs_excess_over_8)}")

    ideal_pop = sum(partition.population.values()) / len(partition)
    max_dev = max({d:abs(partition.population[d] - ideal_pop) / ideal_pop for d in partition.population.keys()}.values())
    print(f"  max. pop. dev = {100*max_dev:0.2f}")
    seats_by_election = [partition[election].wins("Rep") for election in elections]
    print(f"  R seats by election: {seats_by_election}")
    
    assignment = dict(partition.assignment)
    county_pieces = 0
    for county in counties:
        districts = set()
        for node in nodes_by_county[county]:
            districts.add(assignment[node])
        county_pieces += len(districts)
        
    muni_pieces = 0
    for muni in munis:
        districts = set()
        for node in nodes_by_muni[muni]:
            districts.add(assignment[node])
        muni_pieces += len(districts)
    
    print(f"  county pieces: {county_pieces}\n  muni pieces: {muni_pieces}")
