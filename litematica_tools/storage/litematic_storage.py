from litematica_tools.storage.shared_storage import *
from litematica_tools.errors import BlockOutOfBounds


class LitematicRegion(Region):
    """
    Region structure:
    - palette: list (BlockState() objects)
    - block_states: np.ndarray (int64 values)
    - entities: list (Entity() objects)
    - tile_entities: list (TileEntity() objects)
    - position: Vec3d
    - size: Vec3d
    
    Private properties:
    - _shift: int (bits that will be taken from the array value)
    - _bit_span: int (bit length of each entry from the palette)
    _ _items: list (all Item() objects in the region)
    """

    def __init__(self, *args, **kwargs):
        self._shift = None
        self._bit_span = None
        super().__init__(*args, **kwargs)

    def parse_metadata(self):
        self.size = Vec3d.from_dict(self.region_nbt['Size'])
        self.position = Vec3d.from_dict(self.region_nbt['Position'])
        self.volume = abs(self.size.x * self.size.y * self.size.z)

    def parse_block_data(self):
        self.palette = [BlockState(name=i['Name'],
                                   properties=i.get('Properties', None)) for i in self.region_nbt['BlockStatePalette']]
        self.block_states = self.region_nbt['BlockStates']
        self._bit_span = int.bit_length(len(self.palette) - 1)
        self._shift = (1 << self._bit_span) - 1

    def parse_tile_entities(self):
        self.tile_entities = []
        for i in self.region_nbt['TileEntities']:
            temp = TileEntity()
            temp.nbt = i
            temp.position = Vec3d.from_dict(i)
            self.set_inventory(temp)
            # TODO: Uh make this work
            # try:
            #     temp.id = self.palette[
            #         self.get_palette_index(
            #             self.get_index(
            #                 temp.position))].name
            # except Exception as e:
            #     logging.error(f'Attempted to get data from uninitialized palette.\nException stacktrace:{e}')
            temp.id = '#UNKNOWN'
            self.tile_entities.append(temp)

    def parse_entities(self):
        self.entities = []
        for i in self.region_nbt['Entities']:
            temp = Entity()
            temp.nbt = i
            temp.position = Vec3d.from_list(i['Pos'])
            self.set_inventory(temp)
            temp.id = i['id']
            self.entities.append(temp)

    def get_palette_index(self, index: int) -> int:
        """
        :param index: Index of an entry in block_states.
        :return: Index of corresponding entry in the palette.
        """
        start_offset = index * self._bit_span  # amount of bits to skip
        start_array = start_offset >> 6  # value it reads from
        start_bit_offset = start_offset & 0x3F  # offset in the selected value
        entry_end = start_offset % 64 + self._bit_span  # where palette index will end

        try:
            if entry_end < 64:  # check if palette index ends in the array's value boundary
                palette_id = self.block_states[start_array] >> start_bit_offset & self._shift
            else:
                end_offset = 64 - start_bit_offset
                end_array = start_array + 1
                palette_id = (abs(self.block_states[start_array] >> start_bit_offset) | self.block_states[
                    end_array] << end_offset) & self._shift
        except IndexError:
            raise BlockOutOfBounds(f'Attempted to access out of bounds block at index {index}')

        return palette_id

    def block_iterator(self, scan_range: range = None) -> int:
        """
        Yields the index of each block in the region.
        More optimized than looping with get_palette_index() by reducing calculations in the loop.

        :param scan_range: Optional custom range. By default, equals to region volume.
        :return: Index of corresponding entry in the palette.
        """
        if scan_range is None:
            scan_range = range(self.volume)
        elif scan_range[0] < 0 < self.volume < scan_range[1]:
            raise BlockOutOfBounds(f'Provided range is out of bounds: {scan_range}')

        start_offset = scan_range[0] * self._bit_span
        start_array = start_offset >> 6
        start_bit_offset = start_offset & 0x3F
        entry_end = start_offset % 64 + self._bit_span

        for i in scan_range:
            if entry_end < 64:
                out = self.block_states[start_array] >> start_bit_offset & self._shift
            else:
                end_offset = 64 - start_bit_offset
                end_array = ((i + 1) * self._bit_span - 1) >> 6
                out = (abs(self.block_states[start_array] >> start_bit_offset) | self.block_states[
                    end_array] << end_offset) & self._shift

                start_array += 1
                entry_end -= 64

            start_offset += self._bit_span
            start_bit_offset = start_offset & 0x3F
            entry_end += self._bit_span

            yield out

    def get_index(self, coords: list | tuple | Vec3d) -> int:
        """
        :param coords: XYZ values as list, tuple or Vec3d.
                       Values at index > 2 will be ignored.
        :return: Index of corresponding entry in block_states.
                (Likely will be put as index param in the get_block_state)
        """
        return (coords[1]) * self.size.x * self.size.y + (coords[2]) * self.size.x + (coords[0])

    def get_coords(self, index: int) -> Vec3d:
        """
        :param index: Index of corresponding entry in block_states.
        :return: XYZ values as Vec3d.
        """
        layer_size = self.size.x * self.size.z
        return Vec3d(index % self.size.x, index // layer_size, index % layer_size // self.size.x)


class LitematicMetadata(Metadata):
    """
    Metadata structure:
    - author: string
    - description: string (usually empty)
    - name: string
    - size: Vec3d
    - region_count: int
    - time_created: int (unix timestamp)
    - time_modified: int (unix timestamp)
    - total_blocks: int
    - total_volume: int

    Added from main litematic field:
    - litematica_version: int
    - data_version: int (https://minecraft.fandom.com/wiki/Data_version)
    """

    description: str = field(default=None)
    time_created: int = field(default=None)
    time_modified: int = field(default=None)
    version: int = field(default=None)
    region_count: int = field(default=None)
    enclosing_size: Vec3d = field(default=None)
    litematica_version: int = field(default=None)
    total_blocks: int = field(default=None)
    total_volume: int = field(default=None)

    def __post_init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    # TODO: fix .get
    def from_nbt(cls, md_nbt: dict):
        temp = cls()

        temp.author = md_nbt.get('Author', '')
        temp.description = md_nbt.get('Description', '')
        temp.name = md_nbt.get('Name', '')
        temp.size = Vec3d.from_dict(md_nbt.get('EnclosingSize', {}))
        temp.region_count = md_nbt.get('RegionCount', 0)
        temp.time_created = md_nbt.get('TimeCreated', 0)
        temp.time_modified = md_nbt.get('TimeModified', 0)
        temp.total_blocks = md_nbt.get('TotalBlocks', 0)
        temp.total_volume = md_nbt.get('TotalVolume', 0)

        return temp


class Litematic(Structure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_nbt(cls, nbt: dict, init: bool = True) -> 'Litematic':
        """
        Initialize a structure from a NBT dict.
        :param nbt: Dict of NBT data.
        :param init: Tells region parser whether to parse the regions completely.
        (Set to False if you have a big file and don't want to parse all of it)
        :return: Structure object.
        """
        temp = cls()
        temp.raw_nbt = nbt
        temp.parse_metadata(nbt['Metadata'])
        temp.parse_regions(nbt['Regions'], init)
        return temp

    def parse_metadata(self, metadata_nbt):
        self.metadata = LitematicMetadata.from_nbt(metadata_nbt)
        self.metadata.version = self.raw_nbt.get('Version', None)
        self.metadata.data_version = self.raw_nbt.get('MinecraftDataVersion', None)

    def parse_regions(self, regions_nbt, init: bool = True):
        self.regions = {i: LitematicRegion.from_nbt(v, init) for i, v in regions_nbt.items()}
