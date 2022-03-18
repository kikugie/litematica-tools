import re
import nbtlib as nbt
from mezmorize import Cache
from hashlib import md5

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR='cache')

class NBT_File:
    def __init__(self, filepath):
        self.file = filepath

        with open(filepath, 'rb') as f:
            self.raw_nbt = nbt.File.load(f, gzipped=True).unpack()

        self.file_format = re.search('((?!\.)[^.]+)$', filepath).group()
        self.data = {}
        match self.file_format:
            case 'litematic':
                self.data = Litematic(self.raw_nbt)
            case 'schem':
                name = self.file.replace(' ', '_')
                name = re.search('\w+(?=\.schem$)', name).group()
                self.data = Schem(self.raw_nbt, name)
            case _:
                raise ValueError('Unsupported file format')


class Structure:
    def __init__(self, nbt: dict):
        self.hash = md5(str(nbt).encode('utf-8')).hexdigest()
        self.regions = {}


class Litematic(Structure):
    def __init__(self, nbt: dict):
        super().__init__(nbt)

        for i, v in nbt['Regions'].items():
            self.regions[i] = LitematicRegion(i, v)


class Schem(Structure):
    def __init__(self, nbt: dict, name):
        super().__init__(nbt)
        self.regions[name] = SchemRegion(name, nbt)  # actual name later


class Region:
    def __init__(self, name):
        self.name = name
        self.block_state_palette = []
        self.block_states = []
        self.tile_entities = []
        self.entities = []
        self.volume = 0
        self.bit_span = 0


class LitematicRegion(Region):
    def __init__(self, i, v):
        super().__init__(i)
        self.block_state_palette = v['BlockStatePalette']
        self.block_states = v['BlockStates']
        self.tile_entities = v['TileEntities']
        self.entities = v['Entities']
        self.volume = abs(v['Size']['x'] * v['Size']['y'] * v['Size']['z'])
        self.bit_span = int.bit_length(len(self.block_state_palette) - 1)

    def get_block_state(self, index):
        start_offset = index * self.bit_span
        start_arr_index = start_offset >> 6
        end_arr_index = ((index + 1) * self.bit_span - 1) >> 6
        start_bit_offset = start_offset & 0x3F
        shift = (1 << self.bit_span) - 1

        if start_arr_index == end_arr_index:
            out = self.block_states[start_arr_index] >> start_bit_offset & shift
        else:
            end_offset = 64 - start_bit_offset
            out = (abs(self.block_states[start_arr_index] >> start_bit_offset) | self.block_states[
                end_arr_index] << end_offset) & shift
        return out


class SchemRegion(Region):
    def __init__(self, i, v):
        super().__init__(i)
        self.block_state_palette = self.__convert_palette(v['Palette'])
        self.block_states = v['BlockData']
        if 'BlockEntities' in v:
            self.tile_entities = v['BlockEntities']
        if 'Entities' in v:
            self.entities = v['Entities']
        self.volume = v['Length'] * v['Height'] * v['Width']
        self.bit_span = int.bit_length(len(self.block_state_palette) - 1)

    @staticmethod
    def __convert_palette(data: dict):
        out = [None] * len(data)
        for i, v in data.items():
            res = {'Name': re.search('^\w+:\w+', i).group()}
            properties = re.findall('\w+=\w+', i)
            if properties:
                res['Properties'] = {}
                for entry in properties:
                    key, value = entry.split('=')
                    res['Properties'][key] = value

            out[v] = res
        return out

    def get_block_state(self, index):
        return self.block_states[index]
