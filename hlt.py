"""
A Python-based Halite starter-bot framework.

This module contains a Pythonic implementation of a Halite starter-bot framework.
In addition to a class (GameMap) containing all information about the game world
and some helper methods, the module also imeplements the functions necessary for
communicating with the Halite game environment.
"""

import sys
from collections import namedtuple
from itertools import chain, zip_longest
from math import sqrt

myID = 0

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

# Because Python uses zero-based indexing, the cardinal directions have a different mapping in this Python starterbot
# framework than that used by the Halite game environment.  This simplifies code in several places.  To accommodate
# this difference, the translation to the indexing system used by the game environment is done automatically by
# the send_frame function when communicating with the Halite game environment.

NORTH, EAST, SOUTH, WEST, STILL = range(5)

def opposite_cardinal(direction):
    "Returns the opposing cardinal direction."
    return (direction + 2) % 4 if direction != STILL else STILL


Site = namedtuple('Site', 'x y owner strength production dist')

class GameMap:
    def __init__(self, size_string, production_string, map_string=None):
        self.width, self.height = tuple(map(int, size_string.split()))
        self.production = tuple(tuple(map(int, substring)) for substring in grouper(production_string.split(), self.width))
        self.contents = None
        self.max_dist = 0
        self.get_frame(map_string)
        self.starting_player_count = len(set(site.owner for site in self)) - 1

    def get_frame(self, map_string=None):
        "Updates the map information from the latest frame provided by the Halite game environment."
        if map_string is None:
            map_string = get_string()
        split_string = map_string.split()
        owners = list()
        while len(owners) < self.width * self.height:
            counter = int(split_string.pop(0))
            owner = int(split_string.pop(0))
            owners.extend([owner] * counter)
        assert len(owners) == self.width * self.height
        assert len(split_string) == self.width * self.height
        self.contents = [[Site(x, y, owner, strength, production, 0)
                          for x, (owner, strength, production)
                          in enumerate(zip(owner_row, strength_row, production_row))]
                         for y, (owner_row, strength_row, production_row)
                         in enumerate(zip(grouper(owners, self.width),
                                          grouper(map(int, split_string), self.width),
                                          self.production))]
        dists = [[0 for x in range(0, self.width)] for y in range(0, self.height)]
        perimeter, dc = [site for site in self if site.owner == myID and len([n for n in self.neighbors(site) if n.owner != myID]) != 0], 1
        while len(perimeter) > 0:
            my_new_perimeter = []
            for site in perimeter:
                dists[site.y][site.x] = dc
            for site in perimeter:
                my_new_perimeter.extend([n for n in self.neighbors(site) if n.owner == myID and dists[n.y][n.x] == 0])
            perimeter, dc = list(set(my_new_perimeter)), dc+1
        self.max_dist = dc-1
        perimeter, dc = [site for site in self if site.owner != myID and len([n for n in self.neighbors(site) if n.owner == myID]) != 0], -1
        while len(perimeter) > 0:
            op_new_perimeter = []
            for site in perimeter:
                dists[site.y][site.x] = dc
            for site in perimeter:
                op_new_perimeter.extend([n for n in self.neighbors(site) if n.owner != myID and dists[n.y][n.x] == 0])
            perimeter, dc = list(set(op_new_perimeter)), dc-1
        self.contents = [[Site(x, y, owner, strength, production, dists[y][x])
                          for x, (owner, strength, production)
                          in enumerate(zip(owner_row, strength_row, production_row))]
                         for y, (owner_row, strength_row, production_row)
                         in enumerate(zip(grouper(owners, self.width),
                                          grouper(map(int, split_string), self.width),
                                          self.production))]

    def __iter__(self):
        "Allows direct iteration over all sites in the GameMap instance."
        return chain.from_iterable(self.contents)

    def neighbors(self, site, n=1, include_self=False, diagonals = False):
        "Iterable over the n-distance neighbors of a given site.  For single-step neighbors, the enumeration index provides the direction associated with the neighbor."
        assert isinstance(include_self, bool)
        assert isinstance(n, int) and n > 0
        if n == 1:
            if diagonals: combos = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0), (-1, -1), (-1, 1), (1, -1), (1, 1))   # NORTH, EAST, SOUTH, WEST, STILL ... matches indices provided by enumerate(game_map.neighbors(site))
            else: combos = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))   # NORTH, EAST, SOUTH, WEST, STILL ... matches indices provided by enumerate(game_map.neighbors(site))
        else:
            if diagonals: combos = ((dx, dy) for dy in range(-n, n+1) for dx in range(-n, n+1))
            else: combos = ((dx, dy) for dy in range(-n, n+1) for dx in range(-n, n+1) if abs(dx) + abs(dy) <= n)
        return (self.contents[(site.y + dy) % self.height][(site.x + dx) % self.width] for dx, dy in combos if include_self or dx or dy)

    def get_target(self, site, direction):
        "Returns a single, one-step neighbor in a given direction."
        dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))[direction]
        return self.contents[(site.y + dy) % self.height][(site.x + dx) % self.width]

    def get_distance(self, sq1, sq2):
        "Returns Manhattan distance between two sites."
        dx = min(abs(sq1.x - sq2.x), sq1.x + self.width - sq2.x, sq2.x + self.width - sq1.x)
        dy = min(abs(sq1.y - sq2.y), sq1.y + self.height - sq2.y, sq2.y + self.height - sq1.y)
        return dx + dy

    def get_e_distance(self, sq1, sq2):
        "Returns Manhattan distance between two sites."
        dx = min(abs(sq1.x - sq2.x), sq1.x + self.width - sq2.x, sq2.x + self.width - sq1.x)
        dy = min(abs(sq1.y - sq2.y), sq1.y + self.height - sq2.y, sq2.y + self.height - sq1.y)
        return sqrt(dx*dx + dy*dy)

#####################################################################################################################
# Functions for communicating with the Halite game environment (formerly contained in separate module networking.py #
#####################################################################################################################


def send_string(s):
    sys.stdout.write(s)
    sys.stdout.write('\n')
    sys.stdout.flush()


def get_string():
    return sys.stdin.readline().rstrip('\n')


def get_init():
    global myID
    myID = int(get_string())
    m = GameMap(get_string(), get_string())
    return myID, m


def send_init(name):
    send_string(name)


def translate_cardinal(direction):
    "Translate direction constants used by this Python-based bot framework to that used by the official Halite game environment."
    # Cardinal indexing used by this bot framework is
    #~ NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3, STILL = 4
    # Cardinal indexing used by official Halite game environment is
    #~ STILL = 0, NORTH = 1, EAST = 2, SOUTH = 3, WEST = 4
    #~ >>> list(map(lambda x: (x+1) % 5, range(5)))
    #~ [1, 2, 3, 4, 0]
    return (direction + 1) % 5


def send_frame(moves):
    send_string(' '.join(str(site.x) + ' ' + str(site.y) + ' ' + str(translate_cardinal(direction)) for site, direction in moves.items()))
