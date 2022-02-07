import json
import os

import python_nbt.nbt as nbt
from bitstring import BitStream, BitArray, InterpretError

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_path, 'name_references.json'), 'r') as f:
    name_references = json.load(f)
with open(os.path.join(dir_path, 'block_items.json'), 'r') as f:
    block_items = json.load(f)


def increment_dict(dictionary, index, value=1):
    if type(index) == list:
        for i in index:
            dictionary = increment_dict(dictionary, i)
    else:
        try:
            dictionary[index] += value
        except KeyError:
            dictionary[index] = value
    return dictionary


class Litematic:
    def __init__(self, file: str):
        self.raw_schem = nbt.NBTTagCompound.json_obj(nbt.read_from_nbt_file(file), full_json=False)
        self.metadata = self.raw_schem['Metadata']
        self.regions = {}
        for i, v in self.raw_schem['Regions'].items():
            self.regions[i] = Region(v)

    def block_count(self):
        return sum([region.block_count() for region in self.regions.values()], MaterialList())

    def inventory_count(self):
        return sum([region.inventory_count() for region in self.regions.values()], MaterialList())

    def entity_count(self):
        return sum([region.entity_count() for region in self.regions.values()], MaterialList())

    def total_count(self):
        return sum([region.total_count() for region in self.regions.values()], MaterialList())

    def write_json(self, file):
        with open(file, 'w') as f:
            json.dump(self.raw_schem, f, indent=2)


class Region:
    def __init__(self, data):
        self.dimensions = {k: abs(v) for k, v in data['Size'].items()}
        self.volume = self.dimensions['x'] * self.dimensions['y'] * self.dimensions['z']
        self.palette = data['BlockStatePalette']
        self.block_states = BitStream()
        for i in reversed(data['BlockStates']):
            self.block_states.append(BitArray(int=i, length=64))
        self.entities = data['Entities']
        self.tile_entities = data['TileEntities']

    def get_id_span(self):
        return int.bit_length(len(self.palette) - 1)

    def block_count(self):
        block_counts = {}
        for block in self.block_iterator():
            item = self.get_block_item(block)
            if item:
                block_counts = increment_dict(block_counts, item)
        return MaterialList(block_counts)

    def inventory_count(self):
        tile_entity_items = self.item_count(self.tile_entities)
        entity_items = self.item_count(self.entities)
        return tile_entity_items + entity_items

    def entity_count(self):
        entities = {}
        for i in self.entities:
            entities = increment_dict(entities, i['id'])
        return MaterialList(entities)

    def total_count(self):
        return self.block_count() + self.inventory_count() + self.entity_count()

    def get_block(self, x, y, z):
        id_span = self.get_id_span()
        pos = x
        pos += z * self.dimensions['x']
        pos += y * self.dimensions['x'] * self.dimensions['z']

        try:
            self.block_states.pos = self.block_states.len - (pos + 1) * id_span
            return self.palette[self.block_states.peek(f'uint:{id_span}')]
        except InterpretError:
            return OutOfBoundsError("Block location outside of region boundaries.")

    def block_iterator(self):
        id_span = self.get_id_span()
        try:
            for i in range(self.volume):
                pos = self.block_states.len - (i + 1) * id_span
                block_num = self.block_states[pos:pos + id_span].uint
                yield self.get_block_from_num(block_num)
        except InterpretError:
            return []

    def get_block_from_num(self, block_num):
        return self.palette[block_num]  # this is here so we can replace it with a method to generate a BlockState later

    @staticmethod
    def get_block_item(block):
        global block_items
        block = block['Name']
        try:
            return block_items[block]
        except KeyError:
            return block

    @staticmethod
    def item_count(data: dict):
        results = []
        keys = 'id', 'Count'

        def decode_dict(a_dict):
            temp = []
            try:
                for i in keys:
                    temp.append(a_dict[i])
                results.append(temp)
            except KeyError:
                pass
            return a_dict

        json_repr = json.dumps(data)  # Convert to JSON format.
        json.loads(json_repr, object_hook=decode_dict)  # Return value ignored.

        out = {}
        for i in results:
            try:
                out[i[0]] += i[1]
            except KeyError:
                out[i[0]] = i[1]

        if 'minecraft:air' in out:
            del out['minecraft:air']

        return MaterialList(out)


class MaterialList:
    def __init__(self, values: dict = None):
        if values is None:
            values = {}
        self.raw_counts = values
        self.keys = []
        self.values = []
        self.names = []
        self.stack_sizes = []

    def __add__(self, other):
        res = self.raw_counts
        for i, v in other.raw_counts.items():
            try:
                res[i] += v
            except KeyError:
                res[i] = v
        return MaterialList(res)

    def __str__(self):
        if not self.raw_counts:
            return ""
        spacing = max(len(self.get_item_name(k)) for k in self.raw_counts.keys()) + 1
        result = ""
        for k, v in self.sorted_counts().items():
            result += "{:<{s}} {}\n".format(self.get_item_name(k) + ":", v, s=spacing)
        return result

    def sorted_counts(self):
        return {k: v for k, v in sorted(self.raw_counts.items(), key=lambda item: item[1], reverse=True)}

    @staticmethod
    def get_item_name(item_id):
        global name_references
        try:
            return name_references[item_id]
        except KeyError:
            return item_id


class OutOfBoundsError(Exception):
    def __init__(self, *params):
        self.msg = params[0] if params else ''
        self.params = params[1:]

    def __str__(self):
        if self.params:
            return self.msg.format(*self.params)
        return self.msg
