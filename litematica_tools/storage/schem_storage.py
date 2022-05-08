from litematica_tools.storage.shared_storage import *
from litematica_tools.errors import BlockOutOfBounds


class SchemRegion(Region):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse_metadata(self):
        self.size = Vec3d(self.region_nbt['Width'], self.region_nbt['Height'], self.region_nbt['Length'])
        self.volume = self.size.x * self.size.y * self.size.z

    def parse_block_data(self):
        self.palette = self._parse_palette()
        self.block_states = self.region_nbt['BlockData']

    def _parse_palette(self):
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

        out = [BlockState()] * self.region_nbt['PaletteMax']
        for i, v in self.region_nbt['Palette'].items():
            out[v] = BlockState(name=re.search(r'^\w+:\w+', i).group(),
                                properties=property_yoink(i))
        return out

    def parse_tile_entities(self):
        self.tile_entities = []
        for i in self.region_nbt['BlockEntities']:
            temp = TileEntity()
            temp.nbt = i
            temp.position = Vec3d.from_list(i['Pos'])
            temp.id = i['Id']
            self.set_inventory(temp)
            self.tile_entities.append(temp)

    def parse_entities(self):
        self.entities = []
        for i in self.region_nbt['Entities']:
            temp = Entity()
            temp.nbt = i
            temp.position = Vec3d.from_list(i['Pos'])
            self.set_inventory(temp)
            temp.id = i['Id']
            self.entities.append(temp)

    def get_palette_index(self, index: int) -> int:
        return self.block_states[index]

    def block_iterator(self, scan_range: range = None) -> int:
        if scan_range is None:
            scan_range = range(self.volume)
        elif scan_range[0] < 0 < self.volume < scan_range[1]:
            raise BlockOutOfBounds(f'Provided range is out of bounds: {scan_range}')

        for i in scan_range:
            yield self.block_states[i]


class SchemMetadata(Metadata):
    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_nbt(cls, nbt: dict):
        temp = cls()
        temp.data_version = nbt['DataVersion']
        temp.region_count = 1
        temp.size = Vec3d(nbt['Width'], nbt['Height'], nbt['Length'])
        return temp


class Schem(Structure):
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
        self.metadata = SchemMetadata.from_nbt(nbt)
        self.metadata.name = self.name

    def parse_regions(self, nbt, init: bool = True):
        self.regions = {self.name: SchemRegion.from_nbt(nbt, init)}
