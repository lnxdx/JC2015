import time


class Model():
    def __init__(self, queue):
        self.turn_timeout = 0.4
        self.turn_start_time = 0
        self.world = None
        self.queue = queue

    def handle_init_message(self, message):
        init_info = message[Constants.KEY_ARGS][0]
        map_data = message[Constants.KEY_ARGS][1]
        map1 = Map(init_info[Constants.INFO_KEY_MAP_SIZE], map_data)
        self.world = World(self, init_info, map1)

    def handle_turn_message(self, message):
        self.turn_start_time = time.time()
        self.world.turn = message[Constants.KEY_ARGS][0]
        turn_data = message[Constants.KEY_ARGS][1]
        for static_data in turn_data[Constants.KEY_STATICS]:
            self.world.set_static_change(static_data)
        for dynamic_data in turn_data[Constants.KEY_DYNAMICS]:
            self.world.set_dynamic_change(dynamic_data)

    def turn_remaining_time(self):
        passed = time.time() - self.turn_start_time
        return self.turn_timeout - passed


class World():
    def __init__(self, model, init_info, map1):
        self.model = model
        self.teams = init_info[Constants.INFO_KEY_TEAMS]
        self.my_name = init_info[Constants.INFO_KEY_YOUR_INFO][Constants.KEY_NAME]
        self.my_id = init_info[Constants.INFO_KEY_YOUR_INFO][Constants.KEY_ID]
        self.map_size = init_info[Constants.INFO_KEY_MAP_SIZE]
        Block.block_coefficient = init_info[Constants.INFO_KEY_BLOCK_COEFFICIENT]
        self.map = map1
        self.turn = init_info[Constants.KEY_TURN]
        self.all_cells = {}
        self.my_cells = {}
        self.enemy_cells = {}
        self.all_visited_cells = {}
        self.invisible_cells = {}

    def add_cell(self, cell):
        self.all_cells[cell.id] = cell
        self.all_visited_cells[cell.id] = cell
        if cell.team_id == self.my_id:
            self.my_cells[cell.id] = cell
        else:
            self.enemy_cells[cell.id] = cell

    def visible_cell(self, cell):
        if cell.id not in self.all_cells:
            self.add_cell(cell)
        self.invisible_cells.pop(cell.id)

    def invisible_cell(self, cell):
        self.invisible_cells[cell.id] = cell
        if cell.id in self.all_cells:
            self.all_cells.pop(cell.id)
        if cell.id in self.my_cells:
            self.my_cells.pop(cell.id)
        if cell.id in self.enemy_cells:
            self.enemy_cells.pop(cell.id)

    def kill_cell(self, cell):
        if cell.id in self.all_visited_cells:
            self.all_visited_cells.pop(cell.id)
        if cell.id in self.all_cells:
            self.all_cells.pop(cell.id)
        if cell.id in self.my_cells:
            self.my_cells.pop(cell.id)
        if cell.id in self.enemy_cells:
            self.enemy_cells.pop(cell.id)
        if cell.id in self.invisible_cells:
            self.invisible_cells.pop(cell.id)

    def set_static_change(self, static_data):
        self.map.set_change(static_data)

    def set_dynamic_change(self, dynamic_data):
        cell_id = dynamic_data[Constants.GAME_OBJECT_KEY_ID]
        cell = self.all_visited_cells.get(cell_id)
        if cell is None:
            cell = Cell(self.model, dynamic_data)
            self.add_cell(cell)
        else:
            if dynamic_data.get(Constants.GAME_OBJECT_KEY_TYPE) == Constants.GAME_OBJECT_TYPE_DESTROYED:
                self.kill_cell(cell)
            elif not cell.team_id == self.my_id:
                vis = dynamic_data.get(Constants.CELL_KEY_VISIBLE)
                if vis is not None:
                    if vis == 0:
                        self.invisible_cell(cell)
                    else:
                        self.visible_cell(cell)
                        cell.set_change(dynamic_data)
                else:
                    cell.set_change(dynamic_data)
            else:
                cell.set_change(dynamic_data)


class Cell():
    def __init__(self, model, data):
        self.model = model
        self.id = data[Constants.GAME_OBJECT_KEY_ID]
        self.team_id = data[Constants.GAME_OBJECT_KEY_TEAM_ID]
        self.pos = None
        self.energy = 0
        self.depth_of_field = 0
        self.jump = 0
        self.gain_rate = 0
        self.attack_value = 0
        self.set_change(data)

    def set_change(self, data):
        pos = data.get(Constants.GAME_OBJECT_KEY_POSITION)
        if pos is not None:
            self.pos = pos
        energy = data.get(Constants.CELL_KEY_ENERGY)
        if energy is not None:
            self.energy = energy
        depth_of_field = data.get(Constants.CELL_KEY_DEPTH_OF_FIELD)
        if depth_of_field is not None:
            self.depth_of_field = depth_of_field
        jump = data.get(Constants.CELL_KEY_JUMP)
        if jump is not None:
            self.jump = jump
        gain_rate = data.get(Constants.CELL_KEY_GAIN_RATE)
        if gain_rate is not None:
            self.gain_rate = gain_rate
        attack_value = data.get(Constants.CELL_KEY_ATTACK)
        if attack_value is not None:
            self.attack_value = attack_value

    def move(self, direction):
        event = Event(Event.TYPE_MOVE, self.id, self.team_id)
        event.add_arg(direction)
        self.model.queue.put(event.to_message())

    def gain_resource(self):
        event = Event(Event.TYPE_GAIN_RESOURCE, self.id, self.team_id)
        self.model.queue.put(event.to_message())

    def mitosis(self):
        event = Event(Event.TYPE_MITOSIS, self.id, self.team_id)
        self.model.queue.put(event.to_message())

    def attack(self, direction):
        event = Event(Event.TYPE_ATTACK, self.id, self.team_id)
        event.add_arg(direction)
        self.model.queue.put(event.to_message())


class Map():
    def __init__(self, map_size, map_data):
        self.blocks = [[None for i in range(map_size[Constants.MAP_SIZE_WIDTH])] for j in
                       range(map_size[Constants.MAP_SIZE_HEIGHT])]
        self.all_blocks = {}
        for data in map_data:
            if Block.is_block_type(data[Constants.BLOCK_KEY_TYPE]):
                block = Block(data)
                pos = block.pos
                self.blocks[pos["y"]][pos["x"]] = block
                self.all_blocks[block.id] = block

    def set_change(self, data):
        block_id = data[Constants.GAME_OBJECT_KEY_ID]
        block = self.all_blocks.get(block_id)
        if block is not None:
            block.set_change(data)
        return True

    def at(self, pos):
        return self.blocks[pos["y"]][pos["x"]]

    def get_next_pos(self, direction, pos):
        x = pos["x"]
        y = pos["y"]
        if x % 2 == 1:
            if direction == Constants.Directions.NORTH:
                return {"x": x, "y": y + 1}
            elif direction == Constants.Directions.SOUTH:
                return {"x": x, "y": y - 1}
            elif direction == Constants.Directions.NORTH_EAST:
                return {"x": x + 1, "y": y}
            elif direction == Constants.Directions.NORTH_WEST:
                return {"x": x - 1, "y": y}
            elif direction == Constants.Directions.SOUTH_EAST:
                return {"x": x + 1, "y": y - 1}
            elif direction == Constants.Directions.SOUTH_WEST:
                return {"x": x - 1, "y": y - 1}
            else:
                return None
        else:
            if direction == Constants.Directions.NORTH:
                return {"x": x, "y": y + 1}
            elif direction == Constants.Directions.SOUTH:
                return {"x": x, "y": y - 1}
            elif direction == Constants.Directions.NORTH_EAST:
                return {"x": x + 1, "y": y + 1}
            elif direction == Constants.Directions.NORTH_WEST:
                return {"x": x - 1, "y": y + 1}
            elif direction == Constants.Directions.SOUTH_EAST:
                return {"x": x + 1, "y": y}
            elif direction == Constants.Directions.SOUTH_WEST:
                return {"x": x - 1, "y": y}
            else:
                return None


class Block():
    block_coefficient = 0
    BLOCK_TYPES = [
        "n",
        "o",
        "m",
        "r",
        "i",
    ]

    def __init__(self, data):
        #print(data)
        self.id = data[Constants.GAME_OBJECT_KEY_ID]
        self.type = None
        self.pos = None
        self.min_height = 0
        self.resource = 0
        self.turn = 0
        self.jump_improvement_amount = 0
        self.attack_improvement_amount = 0
        self.depth_of_field_improvement_amount = 0
        self.gain_improvement_amount = 0
        self.set_change(data)

    def set_change(self, data):
        type1 = data.get(Constants.GAME_OBJECT_KEY_TYPE)
        if type1 is not None:
            self.type = type1
        pos = data.get(Constants.GAME_OBJECT_KEY_POSITION)
        if pos is not None:
            self.pos = pos
        min_height = data.get(Constants.BLOCK_KEY_MIN_HEIGHT)
        if min_height is not None:
            self.min_height = min_height
        resource = data.get(Constants.BLOCK_KEY_RESOURCE)
        if resource is not None:
            if self.type == Constants.BLOCK_TYPE_RESOURCE:
                self.resource = resource
            else:
                self.resource = 0
        turn = data.get(Constants.BLOCK_KEY_TURN)
        if turn is not None:
            self.turn = turn
        jump_imp = data.get(Constants.BLOCK_KEY_JUMP_IMP)
        if jump_imp is not None:
            if self.type == Constants.BLOCK_TYPE_MITOSIS:
                self.jump_improvement_amount = jump_imp
            else:
                self.jump_improvement_amount = 0
        attack_imp = data.get(Constants.BLOCK_KEY_ATTACK_IMP)
        if attack_imp is not None:
            if self.type == Constants.BLOCK_TYPE_MITOSIS:
                self.attack_improvement_amount = attack_imp
            else:
                self.attack_improvement_amount = 0
        depth_of_field_imp = data.get(Constants.BLOCK_KEY_DEPTH_OF_FIELD_IMP)
        if depth_of_field_imp is not None:
            if self.type == Constants.BLOCK_TYPE_MITOSIS:
                self.depth_of_field_improvement_amount = depth_of_field_imp
            else:
                self.depth_of_field_improvement_amount = 0
        gain_rate_imp = data.get(Constants.BLOCK_KEY_GAIN_RATE_IMP)
        if gain_rate_imp is not None:
            if self.type == Constants.BLOCK_TYPE_MITOSIS:
                self.gain_improvement_amount = gain_rate_imp
            else:
                self.gain_improvement_amount = 0

    def __eq__(self, other):
        if not isinstance(other, Block):
            return False
        if self.pos["x"] == other.pos["x"] and self.pos["y"] == other.pos["y"]:
            return True
        return False

    def __hash__(self):
        return hash((self.pos['x'], self.pos['y']))

    @property
    def height(self):
        height = self.min_height + self.resource / Block.block_coefficient
        if height > Constants.BLOCK_MAX_HEIGHT:
            height = Constants.BLOCK_MAX_HEIGHT
        return height

    @classmethod
    def is_block_type(cls, type1):
        if type1 in Block.BLOCK_TYPES:
            return True
        else:
            return False


class Event():
    TYPE_MOVE = "move"
    TYPE_ATTACK = "attack"
    TYPE_MITOSIS = "mitosis"
    TYPE_GAIN_RESOURCE = "gainResource"

    def __init__(self, type1, id1, team_id):
        self.type = type1
        self.id = id1
        self.args = []
        self.team_id = team_id

    def add_arg(self, arg):
        self.args.append(arg)

    def to_message(self):
        return {
            Constants.KEY_TYPE: self.type,
            Constants.GAME_OBJECT_KEY_OBJECT_ID: self.id,
            Constants.KEY_ARGS: self.args,
            Constants.KEY_TEAM_ID: self.team_id
        }


class Constants():
    class Directions:
        NORTH = "NORTH"
        NORTH_EAST = "NORTH_EAST"
        SOUTH_EAST = "SOUTH_EAST"
        SOUTH = "SOUTH"
        SOUTH_WEST = "SOUTH_WEST"
        NORTH_WEST = "NORTH_WEST"

    DIRECTIONS = [
        Directions.NORTH, Directions.NORTH_EAST, Directions.SOUTH_EAST,
        Directions.SOUTH, Directions.SOUTH_WEST, Directions.NORTH_WEST,
    ]

    KEY_ID = "id"
    KEY_TURN = "turn"
    KEY_ARGS = "args"
    KEY_NAME = "name"
    KEY_OTHER = "other"
    KEY_TYPE = "type"
    KEY_TEAM_ID = "teamId"
    KEY_STATICS = "statics"
    KEY_DYNAMICS = "dynamics"
    KEY_TRANSIENTS = "transients"

    BLOCK_TYPE_NONE = "n"
    BLOCK_TYPE_NORMAL = "o"
    BLOCK_TYPE_MITOSIS = "m"
    BLOCK_TYPE_RESOURCE = "r"
    BLOCK_TYPE_IMPASSABLE = "i"

    BLOCK_KEY_TURN = "t"
    BLOCK_KEY_TYPE = "y"
    BLOCK_KEY_JUMP_IMP = "j"
    BLOCK_KEY_HEIGHT = "h"
    BLOCK_KEY_ATTACK_IMP = "a"
    BLOCK_KEY_RESOURCE = "r"
    BLOCK_KEY_MIN_HEIGHT = "m"
    BLOCK_KEY_DEPTH_OF_FIELD_IMP = "d"
    BLOCK_KEY_GAIN_RATE_IMP = "g"

    CELL_KEY_JUMP = "j"
    CELL_KEY_ENERGY = "e"
    CELL_KEY_ATTACK = "a"
    CELL_KEY_VISIBLE = "v"
    CELL_KEY_DEPTH_OF_FIELD = "d"
    CELL_KEY_GAIN_RATE = "g"

    GAME_OBJECT_TYPE_CELL = "c"
    GAME_OBJECT_TYPE_DESTROYED = "d"

    GAME_OBJECT_KEY_OBJECT_ID = "objectId"
    GAME_OBJECT_KEY_ID = "i"
    GAME_OBJECT_KEY_TURN = "t"
    GAME_OBJECT_KEY_TYPE = "y"
    GAME_OBJECT_KEY_OTHER = "o"
    GAME_OBJECT_KEY_TEAM_ID = "ti"
    GAME_OBJECT_KEY_DURATION = "d"
    GAME_OBJECT_KEY_POSITION = "p"

    INFO_KEY_TURN = "turn"
    INFO_KEY_TEAMS = "teams"
    INFO_KEY_VIEWS = "views"
    INFO_KEY_YOUR_INFO = "yourInfo"
    INFO_KEY_MAP_SIZE = "mapSize"
    INFO_KEY_BLOCK_COEFFICIENT = "blockCoefficient"

    MESSAGE_TYPE_EVENT = "event"
    MESSAGE_TYPE_INIT = "init"
    MESSAGE_TYPE_SHUTDOWN = "shutdown"
    MESSAGE_TYPE_TURN = "turn"

    CONFIG_KEY_IP = "ip"
    CONFIG_KEY_PORT = "port"
    CONFIG_KEY_TOKEN = "token"

    MAP_SIZE_HEIGHT = "height"
    MAP_SIZE_WIDTH = "width"

    BLOCK_MAX_HEIGHT = 9

    CELL_MAX_DEPTH_OF_FIELD = 5
    CELL_MAX_GAIN_RATE = 45
    CELL_MAX_ATTACK = 35
    CELL_MAX_JUMP = 5
    CELL_MIN_ENERGY_FOR_MITOSIS = 80
    CELL_MAX_ENERGY = 100