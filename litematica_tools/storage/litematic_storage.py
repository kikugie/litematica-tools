from .shared_storage import *


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
            temp.inventory = self.nbt_get_items(i, container=[region, temp])
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
            temp.inventory = self.nbt_get_items(i, container=[region, temp])
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
                end_array = start_array + 1
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
