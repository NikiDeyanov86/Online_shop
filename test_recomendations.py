import importlib
import random
from math import sqrt

from pprint import pprint

import data
from generate_data import generate_data


BOUGHT = 2
BROWSED = 1
DID_NOT_BUY = 0

users = data.USERS

if users == {}:
    generate_data(u=5, p=10, my_user=True)
    importlib.reload(data)
    users = data.USERS

pprint(users)


# Returns the Pearson correlation coefficient for p1 and p2
def sim_pearson(prefs, p1, p2):
    # Get the list of mutually rated items
    si = {}
    for item in prefs[p1]:
        if item in prefs[p2]:
            si[item] = 1

    # Find the number of elements
    n = len(si)

    # if they are no ratings in common, return 0
    if n == 0:
        return 0

    # Add up all the preferences
    sum1 = sum([prefs[p1][it] for it in si])
    sum2 = sum([prefs[p2][it] for it in si])

    # Sum up the squares
    sum1_sq = sum([pow(prefs[p1][it], 2) for it in si])
    sum2_sq = sum([pow(prefs[p2][it], 2) for it in si])

    # Sum up the products
    p_sum = sum([prefs[p1][it]*prefs[p2][it] for it in si])

    # Calculate Pearson score
    num = p_sum-(sum1*sum2/n)
    den = sqrt((sum1_sq-pow(sum1, 2)/n)*(sum2_sq-pow(sum2, 2)/n))

    if den == 0:
        return 0

    r = num/den

    return r


# Returns the best matches for person from the prefs dictionary.
# Number of results and similarity function are optional params.
def top_matches(prefs, person, n=5, similarity=sim_pearson):
    scores = [(similarity(prefs, person, other), other)
              for other in prefs if other != person]

    # Sort the list so the highest scores appear at the top
    scores.sort()
    scores.reverse()
    return scores[0:n]


# Gets recommendations for a person by using a weighted average
# of every other user's rankings
def get_recommendations(prefs, person, similarity=sim_pearson):
    totals = {}
    sim_sums = {}

    for other in prefs:
        # don't compare me to myself
        if other == person:
            continue
        sim = similarity(prefs, person, other)

        # ignore scores of zero or lower
        if sim <= 0:
            continue

        for item in prefs[other]:
            # only score movies I haven't seen yet
            if item not in prefs[person] or prefs[person][item] == 0:
                # Similarity * Score
                totals.setdefault(item, 0)
                totals[item] += prefs[other][item] * sim

                # Sum of similarities
                sim_sums.setdefault(item, 0)
                sim_sums[item] += sim

    # Create the normalized list
    rankings = [(total / sim_sums[item], item)
                for item, total in totals.items()]
    # Return the sorted list
    rankings.sort()
    rankings.reverse()
    return rankings


# Transform from user-products to product-users
def transform_prefs(prefs):
    result = {}

    for person in prefs:
        for item in prefs[person]:
            result.setdefault(item, {})

            # Flip item and person
            result[item][person] = prefs[person][item]

    return result
