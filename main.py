import json
from itertools import chain
from bitstring import BitStream, BitArray
import python_nbt.nbt as nbt

import pprint

class Schematic:
    def __init__(self, file: str):
        self.raw_schem = nbt.NBTTagCompound.json_obj(nbt.read_from_nbt_file(file), full_json=False)
        self.metadata = self.raw_schem['Metadata']
        self.regions = {}
        for i, v in self.raw_schem['Regions'].items():
            self.regions[i] = Region(v)

    def write_json(self, file):
        with open(file, 'w') as f:
            json.dump(self.raw_schem, f, indent=2)


class Region:
    def __init__(self, data):
        self.raw_region = data
        self.dimensions = {'x': abs(data['Size']['x']), 'y': abs(data['Size']['y']), 'z': abs(data['Size']['z'])}
        self.volume = self.dimensions['x'] * self.dimensions['y'] * self.dimensions['z']
        self.palette = data['BlockStatePalette']
        self.block_states = data['BlockStates']
        self.entities = data['Entities']
        self.tile_entities = data['TileEntities']

    def block_count(self):
        palette = [i['Name'] for i in self.palette]
        id_span = int.bit_length(len(palette) - 1)
        bit_stream = BitStream()
        for i in reversed(self.block_states):
            bit_stream.append(BitArray(int = i, length = 64))
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
            try: entities[i['id']] += 1
            except KeyError: entities[i['id']] = 1
        return MaterialList(entities)

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
            try: out[i[0]] += i[1]
            except KeyError: out[i[0]] = i[1]

        return MaterialList(out)

class MaterialList:
    def __init__(self, values: dict):
        self.raw_counts = values
        self.keys = []
        self.values = []
        self.names = []
        self.stack_sizes = []

    def __add__(self, other):
        res = self.raw_counts
        for i, v in other.raw_counts.items():
            try: res[i] += v
            except KeyError: res[i] = v
        return MaterialList(res)

    def sorted_counts(self):
        return {k: v for k, v in sorted(self.raw_counts.items(), key=lambda item: item[1], reverse=True)}





schem = Schematic('CCS Raid Full.litematic')
schem.write_json('test.json')

rg = 'daisy_pig_6x_Shulker_Box_Loader'

blocks = schem.regions[rg].block_count()
items = schem.regions[rg].inventory_count()
entities = schem.regions[rg].entity_count()
total = blocks + items + entities

print(f"Blocks: {blocks.raw_counts}\n")
print(f"Items: {items.raw_counts}\n")
print(f"Entities: {entities.raw_counts}\n")
print(f"Total: {total.raw_counts}")


with open(f'blocks.json', 'w') as f:
    json.dump(blocks.sorted_counts(), f, indent=2)
with open('items.json', 'w') as f:
    json.dump(items.sorted_counts(), f, indent=2)
with open('entities.json', 'w') as f:
    json.dump(entities.sorted_counts(), f, indent=2)
with open('total.json', 'w') as f:
    json.dump(total.sorted_counts(), f, indent=2)