import sys
import random
from math import ceil
from Model import Constants



class AI():
    DIRECTIONS = Constants.DIRECTIONS[:]
    REVERSE_DIRECTIONS = {
        Constants.Directions.NORTH: Constants.Directions.SOUTH,
        Constants.Directions.SOUTH: Constants.Directions.NORTH,
        Constants.Directions.NORTH_EAST: Constants.Directions.SOUTH_WEST,
        Constants.Directions.SOUTH_WEST: Constants.Directions.NORTH_EAST,
        Constants.Directions.NORTH_WEST: Constants.Directions.SOUTH_EAST,
        Constants.Directions.SOUTH_EAST: Constants.Directions.NORTH_WEST
    }

    MIN_ATTACK_VALUE = 20
    MAX_ATTACK_VALUE = 35
    AVERAGE_ATTACK_VALUE = (20 + 35) / 2

    # MAX_TURNS_TO_KILL = 5

    class Node:

        def __init__(self, block, parent_block, direction):
            self.block = block
            self.parent = parent_block
            self.direction = direction

        def __str__(self):
            return str(self.block.pos["x"]) + " " + str(self.block.pos["y"])

        def __eq__(self, other):
            return self.block == other.block

        def __hash__(self):
            return hash((self.block.pos["x"], self.block.pos["y"], self.direction))

    @staticmethod
    def get_average_attack_value(world):
        if world.turn < 50:
            return AI.AVERAGE_ATTACK_VALUE
        elif world.turn < 250:
            return (AI.AVERAGE_ATTACK_VALUE + (world.turn - 50) * ((AI.MAX_ATTACK_VALUE - 5) - AI.AVERAGE_ATTACK_VALUE) / 200)
        else:
            return (AI.MAX_ATTACK_VALUE - 5)

    def random_walk(self, world, cell, fully_random=False):
        #print("== random_walk()")
        my_cell_poses = {
            (my_cell.pos['x'], my_cell.pos['y']) for my_cell in world.my_cells.values()}
        random.shuffle(AI.DIRECTIONS)

        for direction in Constants.DIRECTIONS:
            next_pos = world.map.get_next_pos(direction, cell.pos)
            if (next_pos['x'], next_pos['y']) in my_cell_poses:
                continue

            if not AI.is_in_bounds(world, next_pos) or not AI.get_next_to_pos(world, cell, world.map.at(next_pos), world.map.at(cell.pos)):
                continue

            if (fully_random or
                not self.visited[next_pos['x']][next_pos['y']]) \
                    and AI.is_move_possible(world.map.at(cell.pos), world.map.at(next_pos), cell):

                cell.move(direction)
                return

    @staticmethod
    def get_cells_by_type(world, cell_type):
        cells = []
        for x in world.map.blocks:
            for y in x:
                if y.type == cell_type:
                    cells.append(y)
        return cells

    def __init__(self):
        self.visited = {}
        self.cells = {}

    @staticmethod
    def is_in_bounds(world, pos):
        return  world.map_size["width"]  > pos['x'] >= 0 \
            and world.map_size["height"] > pos['y'] >= 0

    @staticmethod
    def is_move_possible(start, end, my_cell, cells=None, current_height=None, next_height=None):
        if not end or end.type == Constants.BLOCK_TYPE_IMPASSABLE:
            return False

        if cells:
            for cell in cells:
                if cell.id != my_cell.id and cell.pos == end.pos:
                    return False

        next_height = next_height or end.height
        current_height = current_height or start.height

        diff = next_height - current_height
        if diff > my_cell.jump:
            return False

        return True

    @staticmethod
    def get_reverse_direction(direction):
        return AI.REVERSE_DIRECTIONS[direction]

    @staticmethod
    def get_next_to_pos(world, cell, start, end):
        visited = set([])
        q = [AI.Node(start, None, None)]
        visited.add(start)

        while len(q) != 0:
            cur = q.pop(0)
            if cur.block == end:
                if cur.parent:
                    while cur.parent.parent:
                        cur = cur.parent
                    return cur
                else:
                    return None

            random.shuffle(AI.DIRECTIONS)
            for direction in AI.DIRECTIONS:
                next_pos = world.map.get_next_pos(direction, cur.block.pos)

                if not AI.is_in_bounds(world, next_pos):
                    continue

                i = AI.Node(world.map.at(next_pos), cur, direction)

                if i.block \
                        and AI.is_move_possible(cur.block, i.block, cell,
                                                cells=world.all_cells.values()) \
                        and i.block.type != Constants.BLOCK_TYPE_NONE \
                        and i.block not in visited:

                    q.append(i)
                    visited.add(i.block)

        return None

    @staticmethod
    def get_next_to_type(world, cell, start, block_type):
        visited = set([])
        q = [AI.Node(start, None, None)]
        visited.add(start)

        while len(q) != 0:
            cur = q.pop(0)

            end_block = cur.block
            if cur.block.type == block_type \
                    and (end_block.pos['x'], end_block.pos['y']) not in AI.targets \
                    and (block_type != Constants.BLOCK_TYPE_RESOURCE or AI.should_gain_resource(world, cell, cur.block)):

                if block_type == Constants.BLOCK_TYPE_RESOURCE:
                    is_target_empty = True

                    for world_cell in world.all_cells.values():
                        if world_cell.pos == end_block.pos:
                            is_target_empty = False
                            break

                    if not is_target_empty:
                        continue

                if cur.parent:
                    while cur.parent.parent:
                        cur = cur.parent
                    return cur, end_block
                else:
                    return None, None

            random.shuffle(AI.DIRECTIONS)
            for direction in AI.DIRECTIONS:
                next_pos = world.map.get_next_pos(direction, cur.block.pos)

                if not AI.is_in_bounds(world, next_pos):
                    continue

                i = AI.Node(world.map.at(next_pos), cur, direction)

                if i.block \
                        and AI.is_move_possible(cur.block, i.block, cell, cells=None) \
                        and (i.block.type != Constants.BLOCK_TYPE_NONE or block_type == Constants.BLOCK_TYPE_NONE) \
                        and i.block not in visited:

                    q.append(i)
                    visited.add(i.block)

        return None, None

    @staticmethod
    def win_probability(world, me, enemy):
        my_turns_to_kill = ceil((enemy.energy + 1) / me.attack_value)
        enemy_turns_to_kill = ceil(
            (me.energy + 1) / AI.get_average_attack_value(world))

        #print("my_turns_to_kill:", my_turns_to_kill)
        #print("enemy_turns_to_kill:", enemy_turns_to_kill)

        return enemy_turns_to_kill - my_turns_to_kill

    @staticmethod
    def should_do_attack(world, cell):
        for enemy_cell in world.enemy_cells.values():
            for direction in AI.DIRECTIONS:
                if world.map.get_next_pos(direction,
                                          cell.pos) == enemy_cell.pos:
                    win_prob = AI.win_probability(world, cell, enemy_cell)
                    #print("Win Prob:", win_prob)
                    if win_prob >= -1:
                        return direction
        return None

    @staticmethod
    def should_gain_resource(world, cell, block=None):
        block = block or world.map.at(cell.pos)

        if block.resource == 0:
            return False

        new_height = min(
            9, block.min_height + max(0, block.resource - cell.gain_rate) / 50)

        for direction in AI.DIRECTIONS:
            next_pos = world.map.get_next_pos(direction, block.pos)
            if not AI.is_in_bounds(world, next_pos):
                continue

            next_block = world.map.at(next_pos)

            if next_block and next_block.type not in [Constants.BLOCK_TYPE_IMPASSABLE, Constants.BLOCK_TYPE_NONE] \
                    and AI.is_move_possible(world.map.at(block.pos), next_block, cell, current_height=new_height):
                return True

        return False

    @staticmethod
    def walk_away(world, cell):
        visited = set([])
        for direction in AI.DIRECTIONS:
            next_pos = world.map.get_next_pos(direction, cell.pos)
            if (next_pos['x'], next_pos['y']) not in visited:
                visited.add((next_pos['x'], next_pos['y']))
                for enemy_cell in world.enemy_cells.values():
                    if enemy_cell.pos == next_pos:
                        return AI.get_reverse_direction(direction)
            for direction_of_direction in AI.DIRECTIONS:
                next_next = world.map.get_next_pos(
                    direction_of_direction, next_pos)
                if (next_next['x'], next_next['y']) not in visited:
                    visited.add((next_next['x'], next_next['y']))
                    for enemy_cell in world.enemy_cells.values():
                        if enemy_cell.pos == next_next:
                            return AI.get_reverse_direction(direction_of_direction)

        return None

    def do_turn(self, world):
        #print("Remaining resources: {}".format(
        #    sum([x.resource for x in AI.get_cells_by_type(world, Constants.BLOCK_TYPE_RESOURCE)])))

        if not self.visited:
            #print('world.map_size =', world.map_size)

            self.visited = [[False for i in range(world.map_size["height"])]
                            for j in range(world.map_size["width"])]

        AI.targets = set()

        for cell_id, cell in world.my_cells.items():
            block = world.map.at(cell.pos)
            #print(">>> #{}: @{}, ${}, h={}".format(
            #    cell.id, cell.pos, cell.energy, block.height))

            # UNCOMMENT THIS ******************************************
            # self.random_walk(world, cell, fully_random=True)

            attack_direction = AI.should_do_attack(world, cell)
            if attack_direction:
                #print('== attack({}).'.format(attack_direction))
                cell.attack(attack_direction)
                continue

            if cell.id not in self.cells:
                self.cells[cell.id] = {
                    'last_action': None,
                    'last_pos': None,
                    'current_pos': cell.pos,
                }
            else:
                self.cells[cell.id]['last_pos'] = self.cells[
                    cell.id]['current_pos']
                self.cells[cell.id]['current_pos'] = cell.pos

            if self.cells[cell.id]['last_pos'] == \
                self.cells[cell.id]['current_pos'] \
                    and self.cells[cell.id]['last_action'] == 'move':
                self.random_walk(world, cell, fully_random=True)
                continue

            self.visited[cell.pos['x']][cell.pos['y']] = True

            self.cells[cell.id]['last_action'] = 'move'

            dir_to_flee = AI.walk_away(world, cell)
            if dir_to_flee:
                #print(">>> walking away")
                cell.move(dir_to_flee)
                continue

            # MITOSIS cell
            elif cell.energy >= Constants.CELL_MIN_ENERGY_FOR_MITOSIS:
                if block.type == Constants.BLOCK_TYPE_MITOSIS:
                    #print("== mitosis()")
                    cell.mitosis()
                    self.cells[cell.id]['last_action'] = 'mitosis'
                    continue
                else:
                    go_block, goal = AI.get_next_to_type(
                        world, cell, block, Constants.BLOCK_TYPE_MITOSIS)
                    if go_block and \
                            go_block.direction:
                        next_to_mitos = AI.get_next_to_pos(
                            world, cell, goal, world.map.at(cell.pos))
                        next_to_me = AI.get_next_to_pos(
                            world, cell, go_block.block, world.map.at(cell.pos))

                        if next_to_me and next_to_mitos:
                            AI.targets.add((goal.pos['x'], goal.pos['y']))
                            cell.move(go_block.direction)
                            continue

            # RESOURCE cell
            elif cell.energy < Constants.CELL_MAX_ENERGY:
                if block.type == Constants.BLOCK_TYPE_RESOURCE and \
                        AI.should_gain_resource(world, cell):
                    #print(
                    #    "== gain_resource() --> h={}, ${}".format(block.height, block.resource))
                    cell.gain_resource()
                    self.cells[cell.id]['last_action'] = 'gain'
                    continue
                else:
                    # not in a resource block
                    go_block, goal = AI.get_next_to_type(
                        world, cell, block, Constants.BLOCK_TYPE_RESOURCE)

                    if go_block \
                            and go_block.direction:
                        next_to_res = AI.get_next_to_pos(
                            world, cell, goal, world.map.at(cell.pos))
                        next_to_me = AI.get_next_to_pos(
                            world, cell, go_block.block, world.map.at(cell.pos))

                        if next_to_res and next_to_me:
                            AI.targets.add((goal.pos['x'], goal.pos['y']))
                            cell.move(go_block.direction)
                            continue

            #print("Couldn't find a resource or mitosis block. Exploring...")
            go_block, goal = AI.get_next_to_type(
                world, cell, block, Constants.BLOCK_TYPE_NONE)

            if go_block and go_block.direction and \
                    AI.get_next_to_pos(world, cell,
                                       go_block.block, world.map.at(cell.pos)):

                AI.targets.add((goal.pos['x'], goal.pos['y']))
                cell.move(go_block.direction)
                continue

            else:
                self.random_walk(world, cell)

        #print("==========================")
