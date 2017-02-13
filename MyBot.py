import hlt, random, time, copy
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Site, opposite_cardinal
myID, game_map = hlt.get_init()
turn_number, moves, val_cache, my_pieces, combat_sites, known_strengths, max_prod, perimeter, perim_values, total_str, total_prod, furthest_site = 1, {}, [[0 for x in range(game_map.width)] for y in range(game_map.height)], set(), [], [], max([s.production for s in game_map]), [], [], 0, 0, 0
hlt.send_init("PythBot#"+str(myID))
current_milli_time = lambda: int(round(time.time() * 1000))
def dyn_max_val(s, mst_cache, children):
    my_val = pow(mst_cache[s.y][s.x][2],1.5)/mst_cache[s.y][s.x][0]
    max_child_val = max([dyn_max_val(c, mst_cache, children) for c in children[s.y][s.x]]) if len(children[s.y][s.x]) > 0 else 0
    val_cache[s.y][s.x] = max(my_val, max_child_val)
    return val_cache[s.y][s.x]
def update_turn():
    global turn_number, moves, val_cache, my_pieces, combat_sites, known_strengths, max_prod, perimeter, total_str, total_prod, furthest_site, perim_values
    turn_number += 1
    moves = {}
    my_pieces = set().union([s for s in game_map if s.owner == myID])
    total_str = sum([site.strength for site in my_pieces])
    total_prod = sum([site.production for site in my_pieces])
    furthest_site = sorted([site for site in my_pieces], key = lambda s: s.dist)[-1]
    perimeter = [site for site in game_map if site.dist == -1]
    # Use dynamic programming to efficiently find costs for every site not owned by me.
    mst_cache, need_cal, children = [[(0, 0, 0) for x in range(game_map.width)] for y in range(game_map.height)], [[True for x in range(game_map.width)] for y in range(game_map.height)], [[[] for x in range(game_map.width)] for y in range(game_map.height)]
    d1_prod_cache = { s: sum([o_s.production/(game_map.get_distance(s, o_s)+1) for o_s in game_map if o_s.owner == myID]) for s in game_map if s.dist == 1 }
    new_perim, finalized = set([s for s in game_map if s.dist == -1]), set()
    time = current_milli_time()
    while len(new_perim) > 0 and current_milli_time() - time < 750:
        lowest_cost, lowest_pair = 99999, None
        for site in new_perim:
            local_lowest_cost, connection = 99999, None
            if need_cal[site.y][site.x]:
                for n in (n for n in game_map.neighbors(site) if n.dist == 1 or n in finalized):
                    n2, prod_acc, counter = n, 0, 1
                    while n2.dist != 1:
                        prod_acc += n2.production / counter
                        n2 = mst_cache[n2.y][n2.x][1]
                        counter += 1
                    prod_acc += d1_prod_cache[n2] / counter
                    cost = 1 + mst_cache[n.y][n.x][0] + site.strength / prod_acc
                    if cost < local_lowest_cost: local_lowest_cost, connection = cost, n
                local_prev_prod_acc = mst_cache[connection.y][connection.x][2] if not need_cal[connection.y][connection.x] else d1_prod_cache[connection]
                mst_cache[site.y][site.x] = (local_lowest_cost, connection, local_prev_prod_acc + site.production)
                need_cal[site.y][site.x] = False
            else: local_lowest_cost, connection = mst_cache[site.y][site.x][0], mst_cache[site.y][site.x][1]
            if local_lowest_cost < lowest_cost: lowest_cost, lowest_pair = local_lowest_cost, (site, connection)
        finalized.add(lowest_pair[0])
        children[lowest_pair[1].y][lowest_pair[1].x].append(lowest_pair[0])
        new_perim.discard(lowest_pair[0])
        for n in (n for n in game_map.neighbors(lowest_pair[0]) if n.dist != 1 and n not in finalized):
            new_perim.add(n)
            need_cal[n.y][n.x] = True
    for s in (s for s in perimeter if mst_cache[s.y][s.x][1].dist == 1):
        dyn_max_val(s, mst_cache, children)
    combat_sites = [ s for s in game_map if s.strength == 0 and s.owner == 0 and len([n for n in game_map.neighbors(s) if n.owner == myID]) != 0 and len([n for n in game_map.neighbors(s, 2) if n.owner != myID and n.owner != 0]) != 0]
    known_strengths = [[0 for x in range(game_map.width)] for y in range(game_map.height)]
def get_val(site):
    assert(site.owner != myID)
    return val_cache[site.y][site.x]
def make_move(site, move):
    global moves
    assert(site not in moves)
    target = game_map.get_target(site, move)
    known_strengths[target.y][target.x] += site.strength + site.production if move == STILL else site.strength
    if known_strengths[target.y][target.x] > 255: known_strengths[target.y][target.x] = 255
    moves[site] = move
def send_moves(moves):
    hlt.send_frame(moves)
while True:
    game_map.get_frame()
    update_turn()
    for site in (s for s in game_map if s.owner == myID and s.strength == 0): make_move(site, STILL)
    # Route 75% of strength towards combat sites.
    accrued_strength, border, dc = 0, set(combat_sites), 0
    dists = { site: 101 for site in game_map }
    while len(border) > 0 and accrued_strength < 3*total_str/4:
        for site in border:
            dists[site] = dc
            accrued_strength += site.strength
        new_border = set()
        for site in border:
            new_border.update([n for n in game_map.neighbors(site) if n.owner == myID and dists[n] == 101])
        border = new_border
        dc += 1
    if len(combat_sites) > 0:
        for site in sorted([s for s in my_pieces if s not in moves and s.strength > 5*s.production and dists[s] != 101], key = lambda s: dists[s]):
            if dists[site] == 1:
                make_move(site, sorted([(d, n) for d, n in enumerate(game_map.neighbors(site)) if dists[n] == 0], key = lambda p: game_map.get_e_distance(furthest_site, p[1]))[-1][0])
            else:
                best_dir, best_val = STILL, 0
                for dir, neighbor in ((d, n) for d, n in enumerate(game_map.neighbors(site)) if dists[n] != 101 and dists[site] > dists[n]):
                    new_val = 255 - (site.strength + known_strengths[neighbor.y][neighbor.x])
                    if new_val >= best_val: best_dir, best_val = dir, new_val
                make_move(site, best_dir)
    new_perim = sorted(perimeter, key=get_val)
    while len(new_perim) > 0:
        target = new_perim.pop()
        route = [{}]
        required = 1 + target.strength
        can_move = True
        for d, n in sorted([(d, n) for d, n in enumerate(game_map.neighbors(target)) if n.owner == myID and n not in moves], key=lambda p:1/(1+p[1].strength)):
            route[0][n] = opposite_cardinal(d)
            required -= n.strength
            if required <= 0:
                break
        while required > 0 and len(route[-1]) > 0:
            for stage in route:
                required -= sum([site.production for site in stage])
            if required <= 0:
                can_move = False
                break
            new_sites = {}
            for site in route[-1]:
                new_sites.update({ n: opposite_cardinal(d) for d, n in enumerate(game_map.neighbors(site)) if n.owner == myID and n.dist <= site.dist and n not in moves and (len(route) < 2 or n not in route[-2]) })
            route.append(new_sites)
            required -= sum([site.strength for site in route[-1]])
        if len(route[-1]) == 0: route.pop()
        if required <= 0 and can_move:
            for site, move in route.pop().items():
                make_move(site, move)
        for stage in route:
            for site in stage:
                make_move(site, STILL)
    for s in sorted([s for s in game_map if s.dist > 1 and s.strength > 8 * s.production and s not in moves], key = lambda s: 1 / s.strength):
        best_card, best_neighbor = sorted([(d, n) for d, n in enumerate(game_map.neighbors(s)) if n.dist < s.dist], key = lambda p: known_strengths[p[1].y][p[1].x])[0]
        if known_strengths[best_neighbor.y][best_neighbor.x] + s.strength <= 290: make_move(s, best_card)
        else: make_move(s, STILL)
    send_moves(moves)
