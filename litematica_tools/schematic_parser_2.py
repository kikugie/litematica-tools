import re
import numpy as np

from nbtlib import File


class NBTFile:
    def __init__(self, filepath, lazy=True):
        self.file = filepath

        with open(filepath, 'rb') as f:
            self.raw_nbt = File.load(f, gzipped=True).unpack()

        self.file_format = re.search(r'\w+$', filepath).group()
        self.data = Litematic(nbt=self.raw_nbt, lazy=lazy)


class Metadata:
    def __init__(self):
        self.name = None
        self.author = None
        self.size = None
        self.data_version = None


class Region:
    def __init__(self):
        self.shift = None
        self.nbt = None
        self.palette = None  # list of BlockState objects
        self.block_states = None
        self.block_states_data_type = None
        self.entities = None
        self.tile_entities = None
        self.position = None
        self.size = None
        self.volume = None
        self.bit_span = None


class BlockState:
    def __init__(self):
        self.name = None
        self.properties = {}


class TileEntity:
    def __init__(self):
        self.id = None
        self.position = None
        self.inventory = []


class Item:
    instances = []

    def __init__(self):
        self.id = None
        self.count = None
        self.slot = None
        self.inventory = []  # list of Item()
        self.origin: list | None = None

    def list_instance(self):
        if self.instances is None:
            self.instances = {
                'tile_entity': [],
                'entity': []
            }
        self.instances[self.origin[0]].append(self)

    def __repr__(self):
        return f'(id: {self.id}, count: {self.count}, slot: {self.slot})'


class Entity:
    def __init__(self):
        self.id = None
        self.inventory = []
        self.position = None


class Litematic:
    def __init__(self, nbt=None, lazy=True):
        self.__lazy = lazy
        if nbt is not None:
            self.__get_metadata(nbt)
            self.__get_regions(nbt)

    def __get_metadata(self, nbt):
        self.metadata = Metadata
        self.metadata.size = tuple(i for i in nbt['Metadata']['EnclosingSize'])
        self.metadata.author = nbt['Metadata']['Author']
        self.metadata.name = nbt['Metadata']['Name']
        self.metadata.data_version = nbt['MinecraftDataVersion']

    def __get_regions(self, nbt):
        self.regions = {}  # name: Region
        for i, v in nbt['Regions'].items():
            temp = Region()
            temp.nbt = v
            if not self.__lazy:
                self.set_block_data(temp)
                self.set_tile_entities(temp)
                self.set_entities(temp)

            self.regions[i] = temp

    def set_block_data(self, region: Region):
        region.size = tuple(j for j in region.nbt['Size'].values())
        region.block_states = region.nbt['BlockStates']
        region.block_states_data_type = 'litematic'
        region.palette = self.__get_palette(region)
        region.volume = abs(region.size[0] * region.size[1] * region.size[2])
        region.bit_span = int.bit_length(len(region.palette) - 1)
        region.shift = (1 << region.bit_span) - 1

    def set_tile_entities(self, region: Region):
        region.tile_entities = self.__get_tile_entities(region)

    def set_entities(self, region: Region):
        region.entities = self.__get_entities(region)

    @staticmethod
    def __get_palette(region: Region) -> list:
        out = []
        for i in region.nbt['BlockStatePalette']:
            temp = BlockState()
            temp.name = i['Name']
            if 'Properties' in i:
                temp.properties = i['Properties']
            out.append(temp)
        return out

    def __get_tile_entities(self, region: Region) -> list:
        te_nbt = region.nbt['TileEntities']
        out = []
        for i in te_nbt:
            temp = TileEntity()
            temp.position = (i['x'], i['y'], i['z'])
            # temp.id = region.nbt['BlockStatePalette'][self.get_block_state(region, self.get_index(region, temp.position))]['Name']
            temp.id = 'some_block'
            temp.inventory = self.__get_items(i, ('tile_entity', temp.id))

            out.append(temp)
        return out

    def __get_entities(self, region: Region) -> list:
        ent = region.nbt['Entities']
        out = []
        for i in ent:
            temp = Entity()
            temp.id = i['id']
            temp.position = tuple(j for j in i['Pos'])
            temp.inventory = self.__get_items(i, ('entity', temp.id))

            out.append(temp)
        return out

    def __get_items(self, inv, origin: tuple = None) -> list:
        out = []

        def yoink(item):
            temp = Item()
            temp.id = item['id']
            temp.count = item['Count']
            if 'Slot' in item:
                temp.slot = item['Slot']
            if 'tag' in item:
                dr = item['tag']
                if 'BlockEntityTag' in dr:
                    dr = dr['BlockEntityTag']
                temp.inventory = self.__get_items(dr, origin)
            temp.origin = origin
            temp.list_instance()
            return temp

        if 'Items' in inv:
            for i in inv['Items']:
                out.append(yoink(i))

        if 'Item' in inv:
            out.append(yoink(inv['Item']))

        return out

    @staticmethod
    def get_index(region: Region, *coords: list | tuple) -> int:
        return coords[1] * region.size[0] * region.size[1] + coords[2] * region.size[0] + coords[0]

    @staticmethod
    def get_block_state(region: Region, index: int) -> int:

        start_offset = index * region.bit_span
        start_array = start_offset >> 6
        start_bit_offset = start_offset & 0x3F
        entry_end = start_offset % 64 + region.bit_span

        if entry_end < 64:
            out = np.right_shift(region.block_states[start_array], np.bitwise_and(start_bit_offset, region.shift))
        else:
            end_offset = 64 - start_bit_offset
            end_array = ((index + 1) * region.bit_span - 1) >> 6
            out = (abs(region.block_states[start_array] >> start_bit_offset) | region.block_states[
                end_array] << end_offset) & region.shift
        return out

        # def calculations(index, bit_span, block_states):
        #     start_offset = index * bit_span
        #     start_arr_index = start_offset >> 6
        #     end_arr_index = ((index + 1) * bit_span - 1) >> 6
        #     start_bit_offset = start_offset & 0x3F
        #     shift = (1 << bit_span) - 1
        #
        #     if start_arr_index == end_arr_index:
        #         out = block_states[start_arr_index] >> start_bit_offset & shift
        #     else:
        #         end_offset = 64 - start_bit_offset
        #         out = (abs(block_states[start_arr_index] >> start_bit_offset) | block_states[
        #             end_arr_index] << end_offset) & shift
        #     return out
        #
        # return calculations(ind, region.bit_span, region.block_states)


class BlockOutOfBounds(Exception):
    def __init__(self, index):
        self.index = index
        super.__init__(self.index)

    def __str__(self):
        return f'Trying to get block outside the enclosing box at index {self.index}!'
