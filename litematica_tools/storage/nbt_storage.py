from .shared_storage import *


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
            temp.inventory = self.nbt_get_items(i['nbt'], container=[region, temp])
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
            if not i['nbt']:
                continue
            temp = Entity(id=i['nbt']['id'],
                          position=Vector(i['pos'][0], i['pos'][1], i['pos'][2]))
            temp.inventory = self.nbt_get_items(i['nbt'], container=[region, temp])
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
        default_range = range(len(region.nbt['blocks']))
        if scan_range is None:
            scan_range = default_range
        elif scan_range[0] < 0 or scan_range[-1] > default_range[-1]:
            raise BlockOutOfBounds(f'({scan_range[0]}, {scan_range[-1]})')

        for i in scan_range:
            yield region.nbt['blocks'][i]['state']
