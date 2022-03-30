import re

from nbtlib import File
from dataclasses import dataclass, field
from collections import namedtuple


class NBTFile:
    def __init__(self, filepath, *, lazy=False):
        """
        Opens the NBT file and writes its data to a python values.

        :param filepath: Path to the desired file.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        self.file = filepath

        with open(filepath, 'rb') as f:
            self.raw_nbt = File.load(f, gzipped=True).unpack()

        self.file_format = re.search(r'\w+$', filepath).group()

        match self.file_format:
            case 'litematic':
                self.data = Litematic(nbt=self.raw_nbt, lazy=lazy)
            case 'schem':
                self.data = Schem(nbt=self.raw_nbt, lazy=lazy)
            case 'nbt':
                self.data = Nbt(nbt=self.raw_nbt, lazy=lazy)
            case _: raise FormatError(self.file_format)


Vector = namedtuple('Vector', ['x', 'y', 'z'])


@dataclass()
class Metadata:
    name: str = field(default=None)
    description: str = field(default=None)
    author: str = field(default=None)
    size: Vector = field(default=None)
    region_count: int = field(default=None)
    data_version: int = field(default=None)

    time_created: int = field(default=None)
    time_modified: int = field(default=None)
    total_blocks: int = field(default=None)
    total_volume: int = field(default=None)

    origin: Vector = field(default=None)
    palette_len: int = field(default=None)


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


class ItemList:
    instances = []


@dataclass()
class Item:
    id: str = field(default=None)
    count: int = field(default=None)
    slot: int = field(default=None)
    inventory: list = field(default=None)
    origin: list = field(default=None)

    def list_instance(self):
        ItemList.instances.append(self)


@dataclass()
class Entity:
    id: str = field(default=None)
    position: Vector = field(default=None)
    inventory: list = field(default=None)


class Structure:
    def __init__(self, nbt=None, *, lazy=False):
        if nbt is not None:
            self.lazy_mode = lazy

    @staticmethod
    def nbt_get_items(inv: dict, *, container: list = None) -> list:
        """
        Used for extracting items from inventories recursively.
        For general use get_items. (Not yet)

        :param inv: Inventory dict to look for items in.
                    Usually entries in TileEntities or Entities
        :param container: Optional param for defining path of the item.
        :return: List of Item objects.
        """
        out = []

        def yoink_item(item):
            temp = Item(id=item['id'],
                        count=item['Count'],
                        slot=item['Slot'] if 'Slot' in item else None)
            if container is not None:
                temp.origin = container + [item['id']]

            if 'tag' in item:
                nd = item['tag']
                if 'BlockEntityTag' in nd:
                    nd = nd['BlockEntityTag']
                temp.inventory = Litematic.nbt_get_items(nd, container=temp.origin)
            temp.list_instance()
            return temp

        if 'Items' in inv:
            for i in inv['Items']:
                out.append(yoink_item(i))

        if 'Item' in inv:
            out.append(yoink_item(inv['Item']))

        return out

    @staticmethod
    def get_index(region: Region, coords: list | tuple | Vector) -> int:
        """
        :param region: Region object to use data from.
        :param coords: XYZ values as list, tuple or Vector.
                       Values at index > 2 will be ignored.
        :return: Index of corresponding entry in block_states.
                (Likely will be put as index param in the get_block_state)
        """
        return coords[1] * region.size[0] * region.size[1] + coords[2] * region.size[0] + coords[0]


class Litematic(Structure):
    def __init__(self, nbt=None, *, lazy=False):
        """
        :param nbt: Litematic NBT data converted to dict.
                    If not provided creates empty class.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        super().__init__(nbt, lazy=lazy)
        if nbt is not None:
            self.__get_metadata(nbt)
            self.__get_regions(nbt)

    def __get_metadata(self, nbt):
        """
        Creates metadata for the Litematic.

        :param nbt: Litematic NBT data converted to dict.
        """
        sz = tuple(nbt['Metadata']['EnclosingSize'].values())
        self.metadata = Metadata(size=Vector(sz[0], sz[1], sz[2]),
                                 author=nbt['Metadata']['Author'],
                                 name=nbt['Metadata']['Name'],
                                 description=nbt['Metadata']['Description'],
                                 region_count=nbt['Metadata']['RegionCount'],
                                 time_created=nbt['Metadata']['TimeCreated'],
                                 time_modified=nbt['Metadata']['TimeModified'],
                                 total_blocks=nbt['Metadata']['TotalBlocks'],
                                 total_volume=nbt['Metadata']['TotalVolume'],
                                 data_version=nbt['MinecraftDataVersion'])

    def __get_regions(self, nbt: dict):
        """
        Creates Region objects from nbt dict

        :param nbt: Region NBT data converted to dict.
        """
        self.regions = {}  # name: Region
        for i, v in nbt['Regions'].items():
            temp = Region()
            temp.nbt = v
            if not self.lazy_mode:
                self.set_block_data(temp)
                self.set_tile_entities(temp)
                self.set_entities(temp)

            self.regions[i] = temp

    def set_block_data(self, region: Region):
        """
        Updates region attributes for block data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        sz = tuple(region.nbt['Size'].values())
        region.size = Vector(sz[0], sz[1], sz[2])
        region.block_states = region.nbt['BlockStates']
        region.block_states_data_type = 'litematic'
        region.palette = self.__get_palette(region)
        region.volume = abs(region.size[0] * region.size[1] * region.size[2])
        region.bit_span = int.bit_length(len(region.palette) - 1)
        region.shift = (1 << region.bit_span) - 1

    def set_tile_entities(self, region: Region):
        """
        Updates region attributes for tile_entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.tile_entities = self.__get_tile_entities(region)

    def set_entities(self, region: Region):
        """
        Updates region attributes for entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.entities = self.__get_entities(region)

    @staticmethod
    def __get_palette(region: Region) -> list:
        """
        Converts 'BlockState' values of nbt list into more accessible format.

        :param region: Region object to use data from.
        :return: List of BlockState objects.
        """
        out = []
        for i in region.nbt['BlockStatePalette']:
            temp = BlockState(name=i['Name'],
                              properties=i['Properties'] if 'Properties' in i else None)
            out.append(temp)
        return out

    def __get_tile_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of TileEntity objects.
        """
        te_nbt = region.nbt['TileEntities']
        out = []
        for i in te_nbt:
            temp = TileEntity()
            temp.position = Vector(i['x'], i['y'], i['z'])
            temp.id = region.nbt['BlockStatePalette'][
                self.get_block_state(region, self.get_index(region, temp.position))]['Name']
            temp.inventory = self.nbt_get_items(i, container=[temp, temp.id])
            out.append(temp)
        return out

    def __get_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of Entity objects.
        """
        ent = region.nbt['Entities']
        out = []
        for i in ent:
            temp = Entity(id=i['id'],
                          position=Vector(i['Pos'][0], i['Pos'][1], i['Pos'][2]))
            temp.inventory = self.nbt_get_items(i, container=[temp, i['id']])
            out.append(temp)
        return out

    @staticmethod
    def get_block_state(region: Region, index: int) -> int:
        """
        :param region: Region object to use data from.
        :param index: Index of an entry in block_states.
        :return: Index of corresponding entry in the palette.
        """
        start_offset = index * region.bit_span
        start_array = start_offset >> 6
        start_bit_offset = start_offset & 0x3F
        entry_end = start_offset % 64 + region.bit_span

        try:
            if entry_end < 64:
                out = region.block_states[start_array] >> start_bit_offset & region.shift
            else:
                end_offset = 64 - start_bit_offset
                end_array = ((index + 1) * region.bit_span - 1) >> 6
                out = (abs(region.block_states[start_array] >> start_bit_offset) | region.block_states[
                    end_array] << end_offset) & region.shift
        except IndexError:
            raise BlockOutOfBounds(index)

        return out

    @staticmethod
    def block_iterator(region: Region, *, scan_range: range = None) -> int:
        """
        :param region: Region object to use data from.
        :param scan_range: Optional custom range. By default equals to region volume.
        :return: Index of corresponding entry in the palette.
        """
        if scan_range is None:
            scan_range = range(region.volume)
        elif scan_range[0] < 0 or scan_range[-1] > region.volume:
            raise BlockOutOfBounds(f'({scan_range[0]}, {scan_range[-1]})')

        start_offset = scan_range[0] * region.bit_span
        start_array = start_offset >> 6
        start_bit_offset = start_offset & 0x3F
        entry_end = start_offset % 64 + region.bit_span

        for i in scan_range:
            if entry_end < 64:
                out = region.block_states[start_array] >> start_bit_offset & region.shift
            else:
                end_offset = 64 - start_bit_offset
                end_array = ((i + 1) * region.bit_span - 1) >> 6
                out = (abs(region.block_states[start_array] >> start_bit_offset) | region.block_states[
                    end_array] << end_offset) & region.shift

                start_array += 1
                entry_end -= 64

            start_offset += region.bit_span
            start_bit_offset = start_offset & 0x3F
            entry_end += region.bit_span

            yield out


class Schem(Structure):
    def __init__(self, nbt=None, *, lazy=False):
        """
        :param nbt: WorldEdit .schem NBT data converted to dict.
                    If not provided creates empty class.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        super().__init__(nbt, lazy=lazy)
        if nbt is not None:
            self.__get_metadata(nbt)
            self.__get_regions(nbt)

    def __get_metadata(self, nbt):
        """
        Creates metadata for the Schem.

        :param nbt: Litematic NBT data converted to dict.
        """
        mt = tuple(nbt['Metadata'].values())
        self.metadata = Metadata(origin=Vector(mt[0], mt[1], mt[2]),
                                 size=Vector(nbt['Length'], nbt['Height'], nbt['Width']),
                                 region_count=1,
                                 palette_len=nbt['PaletteMax'],
                                 data_version=nbt['DataVersion'])

    def __get_regions(self, nbt: dict):
        """
        Creates Region objects from nbt dict

        :param nbt: Region NBT data converted to dict.
        """
        temp = Region()
        temp.nbt = nbt
        if not self.lazy_mode:
            self.set_block_data(temp)
            self.set_tile_entities(temp)
            self.set_entities(temp)

        self.regions = {'schematic': temp}

    def set_block_data(self, region: Region):
        """
        Updates region attributes for block data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.size = Vector(region.nbt['Length'], region.nbt['Height'], region.nbt['Width'])
        region.block_states = region.nbt['BlockData']
        region.block_states_data_type = 'schem'
        region.palette = self.__get_palette(region)
        region.volume = abs(region.size[0] * region.size[1] * region.size[2])

    def set_tile_entities(self, region: Region):
        """
        Updates region attributes for tile_entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.tile_entities = self.__get_tile_entities(region)

    def set_entities(self, region: Region):
        """
        Updates region attributes for entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.entities = self.__get_entities(region)

    @staticmethod
    def __get_palette(region: Region) -> list:
        """
        Converts 'BlockState' values of nbt list into more accessible format.

        :param region: Region object to use data from.
        :return: List of BlockState objects.
        """

        def property_yoink(item: str):
            properties = re.findall(r'\w+=\w+', item)
            if properties:
                local_out = {}
                for e in properties:
                    key, value = e.split('=')
                    local_out[key] = value
            else:
                local_out = None
            return local_out

        out = [BlockState()] * region.nbt['PaletteMax']
        for i, v in region.nbt['Palette'].items():
            out[v] = BlockState(name=re.search(r'^\w+:\w+', i).group(),
                                properties=property_yoink(i))
        return out

    def __get_tile_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of TileEntity objects.
        """
        out = []
        for i in region.nbt['BlockEntities']:
            temp = TileEntity(position=Vector(i['Pos'][0], i['Pos'][1], i['Pos'][2]),
                              id=i['Id'])
            temp.inventory = self.nbt_get_items(i, container=[temp, temp.id])
            out.append(temp)
        return out

    def __get_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of Entity objects.
        """
        ent = region.nbt['Entities']
        out = []
        for i in ent:
            temp = Entity(id=i['Id'],
                          position=Vector(i['Pos'][0], i['Pos'][1], i['Pos'][2]))
            temp.inventory = self.nbt_get_items(i, container=[temp, i['Id']])
            out.append(temp)
        return out

    @staticmethod
    def get_block_state(region: Region, index: int) -> int:
        """
        :param region: Region object to use data from.
        :param index: Index of an entry in block_states.
        :return: Index of corresponding entry in the palette.
        """
        return region.block_states[index]

    @staticmethod
    def block_iterator(region: Region, *, scan_range: range = None) -> int:
        """
        :param region: Region object to use data from.
        :param scan_range: Optional custom range. By default equals to region volume.
        :return: Index of corresponding entry in the palette.
        """
        if scan_range is None:
            scan_range = range(region.volume)
        elif scan_range[0] < 0 or scan_range[-1] > region.volume:
            raise BlockOutOfBounds(f'({scan_range[0]}, {scan_range[-1]})')

        for i in scan_range:
            yield region.block_states[i]


class Nbt(Structure):
    def __init__(self, nbt=None, *, lazy=False):
        """
        :param nbt: Structure block NBT data converted to dict.
                    If not provided creates empty class.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        super().__init__(nbt, lazy=lazy)
        if nbt is not None:
            self.__get_metadata(nbt)
            self.__get_regions(nbt)

    def __get_metadata(self, nbt):
        """
        Creates metadata for the Litematic.

        :param nbt: Litematic NBT data converted to dict.
        """
        self.metadata = Metadata(size=Vector(nbt['size'][0], nbt['size'][1], nbt['size'][2]),
                                 data_version=nbt['DataVersion'])

    def __get_regions(self, nbt: dict):
        """
        Creates Region objects from nbt dict

        :param nbt: Region NBT data converted to dict.
        """
        temp = Region()
        temp.nbt = nbt
        if not self.lazy_mode:
            self.set_block_data(temp)
            self.set_tile_entities(temp)
            self.set_entities(temp)

        self.regions = {'structure': temp}

    def set_block_data(self, region: Region):
        """
        Updates region attributes for block data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.size = Vector(region.nbt['size'][0], region.nbt['size'][1], region.nbt['size'][2])
        region.block_states = region.nbt['blocks']
        region.block_states_data_type = 'nbt'
        region.palette = self.__get_palette(region)
        region.volume = abs(region.size[0] * region.size[1] * region.size[2])

    def set_tile_entities(self, region: Region):
        """
        Updates region attributes for tile_entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.tile_entities = self.__get_tile_entities(region)

    def set_entities(self, region: Region):
        """
        Updates region attributes for entity data from nbt dict.
        Should be used manually if lazy_mode is enabled.

        :param region: Region object to use data from.
        """
        region.entities = self.__get_entities(region)

    @staticmethod
    def __get_palette(region: Region) -> list:
        """
        Converts 'BlockState' values of nbt list into more accessible format.

        :param region: Region object to use data from.
        :return: List of BlockState objects.
        """
        out = []
        for i in region.nbt['palette']:
            temp = BlockState(name=i['Name'],
                              properties=i['Properties'] if 'Properties' in i else None)
            out.append(temp)
        return out

    def __get_tile_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of TileEntity objects.
        """
        out = []
        for i in region.nbt['blocks']:
            if 'nbt' not in i:
                continue
            temp = TileEntity(position=Vector(i['pos'][0], i['pos'][1], i['pos'][2]),
                              id=i['nbt']['id'])
            temp.inventory = self.nbt_get_items(i['nbt'], container=[temp, temp.id])
            out.append(temp)
        return out

    def __get_entities(self, region: Region) -> list:
        """
        :param region: Region object to use data from.
        :return: List of Entity objects.
        """
        ent = region.nbt['entities']
        out = []
        for i in ent:
            temp = Entity(id=i['nbt']['id'],
                          position=Vector(i['pos'][0], i['pos'][1], i['pos'][2]))
            temp.inventory = self.nbt_get_items(i['nbt'], container=[temp, i['nbt']['id']])
            out.append(temp)
        return out

    @staticmethod
    def get_block_state(region: Region, index: int) -> int:
        """
        :param region: Region object to use data from.
        :param index: Index of an entry in block_states.
        :return: Index of corresponding entry in the palette.
        """
        return region.nbt[index]['state']

    @staticmethod
    def block_iterator(region: Region, *, scan_range: range = None) -> int:
        """
        :param region: Region object to use data from.
        :param scan_range: Optional custom range. By default equals to region volume.
        :return: Index of corresponding entry in the palette.
        """
        if scan_range is None:
            scan_range = range(region.volume)
        elif scan_range[0] < 0 or scan_range[-1] > region.volume:
            raise BlockOutOfBounds(f'({scan_range[0]}, {scan_range[-1]})')

        for i in scan_range:
            yield region.nbt[i]['state']


class BlockOutOfBounds(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'Trying to get block outside the enclosing box at {self.message}!'


class FormatError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'File format {self.message} is not supported!'
