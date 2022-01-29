import json

import python_nbt.nbt as nbt
from bitstring import BitStream, BitArray


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
        self.block_states = data['BlockStates']
        self.entities = data['Entities']
        self.tile_entities = data['TileEntities']

    def block_count(self):
        if not self.block_states or self.block_states == [0]:
            return MaterialList()
        palette = [i['Name'] for i in self.palette]
        id_span = int.bit_length(len(palette) - 1)
        bit_stream = BitStream()
        for i in reversed(self.block_states):
            bit_stream.append(BitArray(int=i, length=64))
        bit_stream.pos = bit_stream.len
        block_counts = {i: 0 for i in palette}
        for i in range(self.volume):
            bit_stream.pos -= id_span
            block_counts[palette[bit_stream.peek(f'uint:{id_span}')]] += 1
        if 'minecraft:air' in block_counts:
            del block_counts['minecraft:air']
        return MaterialList(block_counts)

    def inventory_count(self):
        tile_entity_items = self.item_count(self.tile_entities)
        entity_items = self.item_count(self.entities)
        return tile_entity_items + entity_items

    def entity_count(self):
        entities = {}
        for i in self.entities:
            try:
                entities[i['id']] += 1
            except KeyError:
                entities[i['id']] = 1
        return MaterialList(entities)

    def total_count(self):
        return self.block_count() + self.inventory_count() + self.entity_count()

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

    # TODO: add __str__ function to return formatted list

    def sorted_counts(self):
        return {k: v for k, v in sorted(self.raw_counts.items(), key=lambda item: item[1], reverse=True)}
