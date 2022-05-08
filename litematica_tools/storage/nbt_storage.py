from litematica_tools.storage.shared_storage import *
from litematica_tools.errors import BlockOutOfBounds


class NbtRegion(Region):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_metadata(self):
        self.size = Vec3d.from_list(self.region_nbt['size'])
        self.volume = self.size.x * self.size.y * self.size.z

    def parse_block_data(self):
        self.palette = [BlockState(name=i['Name'],
                                   properties=i.get('Properties', None)) for i in self.region_nbt['palette']]
        self.block_states = self.region_nbt['blocks']

    def parse_tile_entities(self):
        self.tile_entities = []
        for i in self.region_nbt['blocks']:
            if 'nbt' not in i:
                continue
            temp = TileEntity()
            temp.nbt = i['nbt']
            temp.position = Vec3d.from_list(i['pos'])
            temp.id = '#UNKNOWN'
            self.set_inventory(temp)
            self.tile_entities.append(temp)

    def parse_entities(self):
        self.entities = []
        for i in self.region_nbt['entities']:
            temp = Entity()
            temp.nbt = i['nbt']
            temp.position = Vec3d.from_list(i['blockPos'])
            self.set_inventory(temp)
            temp.id = i['nbt']['id']
            self.entities.append(temp)

    def get_palette_index(self, index: int) -> int:
        return self.region_nbt['blocks'][index]['state']

    def block_iterator(self, scan_range: range = None) -> int:
        if scan_range is None:
            scan_range = range(self.volume)
        elif scan_range[0] < 0 < self.volume < scan_range[1]:
            raise BlockOutOfBounds(f'Provided range is out of bounds: {scan_range}')

        for i in scan_range:
            yield self.get_palette_index(i)


class NbtMetadata(Metadata):
    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_nbt(cls, nbt: dict):
        temp = cls()
        temp.data_version = nbt['DataVersion']
        temp.region_count = 1
        temp.size = Vec3d.from_list(nbt['size'])
        return temp


class Nbt(Structure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_nbt(cls, nbt: dict, init: bool = True) -> 'Structure':
        """
        Initialize a structure from a NBT dict.
        :param nbt: Dict of NBT data.
        :param init: Tells region parser whether to parse the regions completely.
        (Set to False if you have a big file and don't want to parse all of it)
        :return: Structure object.
        """
        temp = cls()
        temp.raw_nbt = nbt
        temp.parse_metadata(nbt)
        temp.parse_regions(nbt, init)
        return temp

    def parse_metadata(self, nbt):
        self.metadata = NbtMetadata.from_nbt(nbt)
        self.metadata.name = self.name

    def parse_regions(self, nbt, init: bool = True):
        self.regions = {self.name: NbtRegion.from_nbt(nbt, init)}
