from dataclasses import dataclass, field
from collections import namedtuple

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


class Structure:
    def __init__(self, nbt=None, *, lazy=False):
        if nbt is not None:
            self.lazy_mode = lazy

        self.items = []

    def nbt_get_items(self, inv: dict, *, container: list = None) -> list:
        """
        Used for extracting items from inventories recursively.
        For general use get_items. (Not yet)

        :param inv: Inventory dict to look for items in.
                    Usually entries in TileEntities or Entities
        :param container: Optional param for defining path of the item.
        :return: List of Item objects.
        """
        out = []
        items = self.items

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
                temp.inventory = self.nbt_get_items(nd, container=temp.origin)
            items.append(temp)
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


class BlockOutOfBounds(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'Trying to get block outside the enclosing box at {self.message}!'
