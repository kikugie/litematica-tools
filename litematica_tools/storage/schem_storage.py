import re

from .shared_storage import *


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
            temp = Entity(id=i['Id'],
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
