import re
import nbtlib as nbt

def snake_case(text):
    return '_'.join([k.lower() for k in re.split('(?=[A-Z])\B', text)])

class Schematic:
    def __init__(self, file: str):
        self.file = file
        self.file_format = self.get_file_format()
        with open(self.file, 'rb') as f:
            self.nbt = nbt.File.load(f, gzipped=True).unpack()
        self.metadata = self.get_metadata()
        self.data_version = self.nbt['MinecraftDataVersion']
        self.version = self.nbt['Version']

        self.regions = {}
        for i, v in self.nbt['Regions'].items():
            self.regions[i] = Region(v)

    def get_file_format(self):
        format = re.search('((?!\.)[^.]+)$', self.file).group()
        match format:
            case 'litematic':
                return format
            case _:
                raise ValueError('File format not supported')

    def get_metadata(self):
        mdata = self.nbt['Metadata']
        format_mdata = {}
        for i, v in mdata.items():
            format_mdata[snake_case(i)] = v
        return format_mdata


class Region:
    def __init__(self, data):
        self.nbt = data
        self.dimensions = tuple(abs(int(i)) for i in self.nbt['Size'].values())
        self.volume = self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
        self.bit_width = int.bit_length(len(self.nbt['BlockStatePalette']) - 1)

    def get_block_state(self, index):
        start_offset = index * self.bit_width
        start_arr_index = start_offset >> 6
        end_arr_index = ((index + 1) * self.bit_width - 1) >> 6
        start_bit_offset = start_offset & 0x3F
        shift = (1 << self.bit_width) - 1

        if start_arr_index == end_arr_index:
            out = self.nbt['BlockStates'][start_arr_index] >> start_bit_offset & shift
        else:
            end_offset = 64 - start_bit_offset
            out = (abs(self.nbt['BlockStates'][start_arr_index] >> start_bit_offset) | self.nbt['BlockStates'][end_arr_index] << end_offset) & shift
        return out
