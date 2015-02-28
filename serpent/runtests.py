#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This software (Augur) allows buying and selling event options in Ethereum.

Copyright (c) 2014 Chris Calderon, Joey Krug, Scott Leonard, Alan Lu, Jack Peterson

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Questions?  Please contact jack@tinybike.net or joeykrug@gmail.com.

"""
from __future__ import division
import sys
import json
from pprint import pprint
import numpy as np
import pandas as pd
try:
    from colorama import Fore, Style, init
except ImportError:
    pass
from pyethereum import tester as t

# np.set_printoptions(linewidth=500)
np.set_printoptions(linewidth=225,
                    suppress=True,
                    formatter={"float": "{: 0.6f}".format})

pd.set_option("display.max_rows", 25)
pd.set_option("display.width", 1000)
pd.set_option('display.float_format', lambda x: '%.8f' % x)

# max_iterations: number of blocks required to complete PCA
max_iterations = 5
tolerance = 1e-12
init()

# true=1, false=-1, indeterminate=0.5, no response=0
# reports = np.array([[  1,  1, -1,  0],
#                     [  1, -1, -1, -1],
#                     [  1,  1, -1, -1],
#                     [  1,  1,  1, -1],
#                     [  0, -1,  1,  1],
#                     [ -1, -1,  1,  1]])
# reports = np.array([[  1,  1, -1,  1],
#                     [  1, -1, -1, -1],
#                     [  1,  1, -1, -1],
#                     [  1,  1,  1, -1],
#                     [  1, -1,  1,  1],
#                     [ -1, -1,  1,  1]])
# reputation = [2, 10, 4, 2, 7, 1]

# reports = np.array([[ 1,  1, -1, -1 ],
#                     [ 1, -1, -1, -1 ],
#                     [ 1,  1, -1, -1 ],
#                     [ 1,  1,  1, -1 ],
#                     [-1, -1,  1,  1 ],
#                     [-1, -1,  1,  1 ]])

reports = np.array([[ 1,  1, -1, -1, 233, 16027.59],
                    [ 1, -1, -1, -1, 199,     0.  ],
                    [ 1,  1, -1, -1, 233, 16027.59],
                    [ 1,  1,  1, -1, 250,     0.  ],
                    [-1, -1,  1,  1, 435,  8001.00],
                    [-1, -1,  1,  1, 435, 19999.00]])
reputation = [1, 1, 1, 1, 1, 1]

# pyconsensus bounds format:
#     event_bounds = [
#         {"scaled": True, "min": 0.1, "max": 0.5},
#         {"scaled": True, "min": 0.2, "max": 0.7},
#         {"scaled": False, "min": 0, "max": 1},
#         {"scaled": False, "min": 0, "max": 1},
#     ]
scaled = [0, 0, 0, 0, 1, 1]
scaled_max = [1, 1, 1, 1, 435, 20000]
scaled_min = [-1, -1, -1, -1, 0, 8000]
# scaled = [1, 1, 0, 0]
# scaled_max = [0.5, 0.7, 1, 1]
# scaled_min = [0.1, 0.2, -1, -1]
# scaled = [0, 0, 0, 0]
# scaled_max = [1, 1, 1, 1]
# scaled_min = [-1, -1, -1, -1]

# num_players = 25
# num_events = 25
# reports = np.random.randint(-1, 2, (num_players, num_events))
# reputation = np.random.randint(1, 100, num_players)
# scaled = np.random.randint(0, 2, num_events).tolist()
# scaled_max = np.ones(num_events)
# scaled_min = -np.ones(num_events)
# for i in range(num_events):
#     if scaled[i]:
#         scaled_max[i] = np.random.randint(1, 100)
#         scaled_min[i] = np.random.randint(0, scaled_max[i])
# scaled_max = scaled_max.astype(int).tolist()
# scaled_min = scaled_min.astype(int).tolist()

def BR(string): # bright red
    return "\033[1;31m" + str(string) + "\033[0m"

def BB(string): # bright blue
    return Fore.BLUE + Style.BRIGHT + str(string) + Style.RESET_ALL

def BW(string): # bright white
    return Fore.WHITE + Style.BRIGHT + str(string) + Style.RESET_ALL

def BG(string): # bright green
    return Fore.GREEN + Style.BRIGHT + str(string) + Style.RESET_ALL

def blocky(*strings, **kwds):
    colored = kwds.get("colored", True)
    width = kwds.get("width", 108)
    bound = width*"#"
    fmt = "#{:^%d}#" % (width - 2)
    lines = [bound]
    for string in strings:
        lines.append(fmt.format(string))
    lines.append(bound)
    lines = "\n".join(lines)
    if colored:
        lines = BR(lines)
    return lines

def fix(x):
    return int(x * 0x10000000000000000)

def unfix(x):
    return x / 0x10000000000000000

def fold(arr, num_cols):
    folded = []
    num_rows = len(arr) / float(num_cols)
    if num_rows != int(num_rows):
        raise Exception("array length (%i) not divisible by %i" % (len(arr), num_cols))
    num_rows = int(num_rows)
    for i in range(num_rows):
        row = []
        for j in range(num_cols):
            row.append(arr[i*num_cols + j])
        folded.append(row)
    return folded

def display(arr, description=None, show_all=None, refold=False):
    if description is not None:
        print(BW(description))
    if refold and type(refold) == int:
        num_rows = len(arr) / float(refold)
        if num_rows == int(num_rows) and len(arr) > refold:
            print(np.array(fold(map(unfix, arr), refold)))
        else:
            refold = False
    if not refold:
        if show_all is not None:
            print(pd.DataFrame({
                'result': arr,
                'base 16': map(hex, arr),
                'base 2^64': map(unfix, arr),
            }))
        else:
            print(json.dumps(map(unfix, arr), indent=3, sort_keys=True))

def serpent_function(s, c, name, signature, args=[]):
    sys.stdout.write("  " + BG(name) + " ")
    sys.stdout.flush()
    # profile = s.profile(t.k0, c, 0, name, signature, args)
    # print "%i gas (%d seconds)" % (profile['gas'], profile['time'])
    # return s.call(t.k0, c, 0, name, signature, args)

def test_contract(contract):
    """
    To run consensus, you should call the Serpent functions in consensus.se
    in this order:
    
    interpolate
    center
    pca_loadings (this should be called once for each PCA iteration --
                  in tests, it seems that 5 iterations is sufficient.
                  each iteration takes the previous iteration's
                  loading_vector output as its input.)
    pca_scores
    calibrate_sets
    calibrate_wsets
    pca_adjust
    smooth
    consensus
    participation

    Refer to the function signatures (in serpent_function, which are passed
    to s.call() below for the arguments you need to pass to each function).

    Final results (event outcomes and updated reputation values) are returned
    as fixed-point (base 2^64) values from the participation function.

    """
    s = t.state()
    filename = contract + ".se"
    print BB("Testing contract:"), BG(filename)
    c = s.abi_contract(filename, sender=t.k0)

    num_players = len(reputation)
    num_events = len(reports[0])
    v_size = num_players * num_events

    reputation_fixed = map(fix, reputation)
    reports_fixed = map(fix, reports.ravel())
    scaled_max_fixed = map(fix, scaled_max)
    scaled_min_fixed = map(fix, scaled_min)

    arglist = [reports_fixed, reputation_fixed, scaled, scaled_max_fixed, scaled_min_fixed]
    result = c.interpolate(*arglist)
    result = np.array(result)
    reports_filled = result[0:v_size].tolist()
    reports_mask = result[v_size:].tolist()
    del result

    display(reports_filled, "reports (filled):", refold=num_events, show_all=True)

    # center and initiate multistep pca loading vector
    arglist = [reports_filled, reputation_fixed, scaled,
               scaled_max_fixed, scaled_min_fixed, max_iterations]
    result = c.center(*arglist)
    result = np.array(result)
    weighted_centered_data = result[0:v_size].tolist()
    loading_vector = result[v_size:].tolist()

    arglist = [loading_vector, weighted_centered_data, reputation_fixed, num_players, num_events]
    while loading_vector[num_events] > 0:
        loading_vector = c.pca_loadings(*arglist)
        arglist[0] = loading_vector
        # display(loading_vector, "Loadings %i:" % loading_vector[num_events], show_all=True)

    arglist = [loading_vector, weighted_centered_data, num_players, num_events]
    scores = c.pca_scores(*arglist)

    arglist = [scores, num_players, num_events]
    result = c.calibrate_sets(*arglist)
    result = np.array(result)
    set1 = result[0:num_players].tolist()
    set2 = result[num_players:].tolist()
    assert(len(set1) == len(set2))
    assert(len(result) == 2*num_players)
    del result

    # display(set1, "set1:", show_all=True)
    # display(set2, "set2:", show_all=True)

    arglist = [set1, set2, reputation_fixed, reports_filled, num_players, num_events]
    result = c.calibrate_wsets(*arglist)
    result = np.array(result)
    old = result[0:num_events].tolist()
    new1 = result[num_events:(2*num_events)].tolist()
    new2 = result[(2*num_events):].tolist()
    assert(len(result) == 3*num_events)
    assert(len(old) == len(new1) == len(new2))
    del result

    # display(old, "old:", show_all=True)
    # display(new1, "new1:", show_all=True)
    # display(new2, "new2:", show_all=True)

    arglist = [old, new1, new2, set1, set2, scores, num_players, num_events]
    adjusted_scores = c.pca_adjust(*arglist)

    # display(adjusted_scores, "adjusted_scores:", show_all=True)

    arglist = [adjusted_scores, reputation_fixed, num_players, num_events]
    smooth_rep = c.smooth(*arglist)

    # display(reports_filled, "reports_filled:", show_all=True)
    # display(reports_filled,"reports_filled:",refold=num_events, show_all=True)
    # display(smooth_rep, "smooth_rep:", show_all=True)

    arglist = [smooth_rep, reports_filled, scaled, scaled_max_fixed,
               scaled_min_fixed, num_players, num_events]
    result = c.consensus(*arglist)

    result = np.array(result)
    outcomes_final = result[0:num_events].tolist()
    consensus_reward = result[num_events:].tolist()
    assert(len(outcomes_final) == len(consensus_reward))
    del result

    arglist = [outcomes_final, consensus_reward, smooth_rep, reports_mask, num_players, num_events]
    reporter_bonus = c.participation(*arglist)

    display(loading_vector, "Loadings:", show_all=True)
    display(adjusted_scores, "Adjusted scores:")
    display(scores, "Scores:")
    display(smooth_rep, "Updated reputation:")
    display(outcomes_final, "Outcomes (final):")
    display(reporter_bonus, "Reporter bonus:")

def main():
    global s
    print BR("Forming new test genesis block")
    s = t.state()
    contracts = [
        "consensus",
    ]
    for contract in contracts:
        test_contract(contract)

if __name__ == "__main__":
    main()