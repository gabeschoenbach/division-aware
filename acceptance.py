import math
from gerrychain import accept
import numpy as np
import random

def L1(vec):
    return sum(abs(v) for v in vec)

def P1(partition, elections):
    num_dists = len(partition)
    num_R_seats = 0
    for election in elections:
        num_R_seats += partition[election].wins('Rep')
    average_R_vote_share = np.mean([partition[election].percent('Rep') for election in elections])
    average_R_seat_share = num_R_seats / (num_dists * len(elections))
    return abs(average_R_seat_share - average_R_vote_share)

def P2(partition, elections):
    num_dists = len(partition)
    proportionality_vector = []
    for election in elections:
        vote_share = partition[election].percent("Rep")
        seat_share = partition[election].wins("Rep") / num_dists
        proportionality_vector.append(seat_share - vote_share)
    return L1(proportionality_vector)

def D(partition, elections):
    num_dists = len(partition)
    num_R_seats = 0
    for election in elections:
        num_R_seats += partition[election].wins('Rep')
    seat_share = num_R_seats / (num_dists * len(elections))
    return seat_share

def guided_acceptance_factory(elections, steps, acceptance='D'):
    
    def accept_more_P1(partition):
        if partition.step % int(steps / 5) in range(int(steps / 25)):
            return True
        else:
            C = 1800
        parent = partition.parent
        child_P1 = P1(partition, elections)
        parent_P1 = P1(parent, elections)
        probability = min([math.exp(C*(parent_P1 - child_P1)), 1])
        if random.random() < probability:
            return True
        else:
            return False

    def accept_more_P2(partition):
        if partition.step % int(steps / 5) in range(int(steps / 25)):
            return True
        else:
            C = 800
        parent = partition.parent
        child_P2 = P2(partition, elections)
        parent_P2 = P2(parent, elections)
        probability = min([math.exp(C*(parent_P2 - child_P2)), 1])
        if random.random() < probability:
            return True
        else:
            return False
        
    def accept_more_D(partition):
        if partition.step % int(steps / 5) in range(int(steps / 25)):
            return True
        else:
            C = 1800
        parent = partition.parent
        child_D = D(partition, elections)
        parent_D = D(parent, elections)
        probability = min([math.exp(C*(parent_D - child_D)), 1])
        if random.random() < probability:
            return True
        else:
            return False
        
    if acceptance == 'P1':
        return accept_more_P1
    elif acceptance == 'P2':
        return accept_more_P2
    elif acceptance == 'D':
        return accept_more_D
    else:
        return accept.always_accept
