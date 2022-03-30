import re
import numpy as np

from nbtlib import File
from dataclasses import dataclass, field
from collections import namedtuple


class NBTFile:
    def __init__(self, filepath, lazy=True):
        self.file = filepath

        with open(filepath, 'rb') as f:
            self.raw_nbt = File.load(f, gzipped=True).unpack()

        self.file_format = re.search(r'\w+$', filepath).group()

        self.data = Litematic(nbt=self.raw_nbt, lazy=lazy)


Vector = namedtuple('Vector', ['x', 'y', 'z'])


@dataclass()
class Metadata:
    name: str = field(default=None)
    description: str = field(default=None)
    author: str = field(default=None)
    size: Vector = field(default=None)
    region_count: int = field(default=None)
    time_created: int = field(default=None)
    time_modified: int = field(default=None)
    total_blocks: int = field(default=None)
    total_volume: int = field(default=None)


@dataclass()
class Region:
    # block state data
    palette: list = field(default=None)
    block_states: list = field(default=None)
    block_states_data_type: str = field(default=None)

    shift: int = field(default=None)
    bit_span: int = field(default=None)

    # entities
    tile_entities: list = field(default=None)
    entities: list = field(default=None)

    # other
    nbt: dict = field(default=None)
    position: Vector = field(default=None)
    size: Vector = field(default=None)
    volume: int = field(default=None)


@dataclass()
class BlockState:
    name: str = field(default=None)
    properties: dict = field(default=None)


@dataclass()
class TileEntity:
    id: str = field(default=None)
    position: Vector = field(default=None)
    inventory: list = field(default=None)


@dataclass()
class Item:
    id: str = field(default=None)
    count: int = field(default=None)
    slot: int = field(default=None)
    inventory: list = field(default=None)
    origin: list = field(default=None)


@dataclass()
class Entity:
    id: str = field(default=None)
    position: Vector = field(default=None)
    inventory: list = field(default=None)


class Litematic:
    def __init__(self, nbt=None, *, lazy=True):
        self.__lazy_mode = lazy
        if nbt is not None:
            self.__get_metadata(nbt)
            self.__get_regions(nbt)

    def __get_metadata(self, nbt):
        sz = tuple(i for i in nbt['Metadata']['EnclosingSize'])
        self.metadata = Metadata(size=Vector(sz[0], sz[1], sz[2]),
                                 author=nbt['Metadata']['Author'],
                                 name=nbt['Metadata']['Name'])

    def __get_regions(self, nbt):
        self.regions = {}  # name: Region
        for i, v in nbt['Regions'].items():
            temp = Region()
            temp.nbt = v
            if not self.__lazy_mode:
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
            temp = BlockState(name=i['Name'],
                              properties=i['Properties'] if 'Properties' in i else None)
            out.append(temp)
        return out

    def __get_tile_entities(self, region: Region) -> list:
        te_nbt = region.nbt['TileEntities']
        out = []
        for i in te_nbt:
            temp = TileEntity(position=Vector(i['x'], i['y'], i['z']),
                              inventory=self.__get_items(i),
                              id='#UNKNOWN')
            # temp.id = region.nbt['BlockStatePalette'][self.get_block_state(region, self.get_index(region, temp.position))]['Name']
            out.append(temp)
        return out

    def __get_entities(self, region: Region) -> list:
        ent = region.nbt['Entities']
        out = []
        for i in ent:
            pos = tuple(j for j in i['Pos'])
            temp = Entity(id=i['id'],
                          position=Vector(pos[0], pos[1], pos[2]),
                          inventory=self.__get_items(i))
            out.append(temp)
        return out

    def __get_items(self, inv) -> list:
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
                temp.inventory = self.__get_items(dr)
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
