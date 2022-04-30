import json
import os.path
import re
from collections import namedtuple
from dataclasses import dataclass, field
from typing import ClassVar, Type
from abc import ABC, abstractmethod

from nbtlib import File


class Vec3d(namedtuple('Vec3d', ['x', 'y', 'z'])):
    def __init__(self, *args, **kwargs):
        super().__init__()

    @classmethod
    def from_dict(cls, data: dict[str, float]):
        return cls(data['x'], data['y'], data['z'])

    @classmethod
    def from_list(cls, data: tuple[float] | list[float]):
        return cls(data[0], data[1], data[2])

    def _add(self, other: tuple[float] | list[float]):
        return Vec3d(self.x + other[0], self.y + other[1], self.z + other[2])

    def __add__(self, other):
        return self._add(other)

    def __iadd__(self, other):
        return self._add(other)

    def __abs__(self):
        return Vec3d(abs(self.x), abs(self.y), abs(self.z))

    def __repr__(self):
        return f'Vec3d({self.x}, {self.y}, {self.z})'

    def __str__(self):
        return f'({self.x}, {self.y}, {self.z})'


@dataclass
class Metadata:
    name: str = field(default=None)
    author: str = field(default=None)
    data_version: int = field(default=None)
    size: Vec3d = field(default=None)
    region_count: int = field(default=None)


@dataclass
class BlockState:
    name: str = field(default=None)
    properties: dict = field(default=None)


@dataclass
class Container:
    nbt: dict = field(default=None)
    inventory: list['ItemStack'] = field(default_factory=list)
    rec_inventory: list['ItemStack'] = field(default_factory=list)


@dataclass
class TileEntity(Container):
    id: str = field(default=None)
    position: Vec3d = field(default=None)

    def __post_init__(self, *args, **kwargs):
        super(TileEntity, self).__init__(*args, **kwargs)

    def __hash__(self):
        return id(self)


@dataclass
class Item:
    name: str
    stack_size: int = field(default=64)
    _all_items: ClassVar[dict] = field(default={}, init=False)

    @staticmethod
    def _generate_item(name: str):
        stack = 64
        with open(os.path.join(os.path.dirname(__file__), '..', 'config', '16-stackables.json'), 'r') as f:
            qstacks = json.load(f)
        with open(os.path.join(os.path.dirname(__file__), '..', 'config', 'unstackables.json'), 'r') as f:
            nstacks = json.load(f)
        if name in qstacks:
            stack = 16
        elif name in nstacks:
            stack = 1
        item = Item(name, stack)
        Item._all_items.update({name: item})

    def __class_getitem__(cls, name: str):
        if name == '*':
            return cls._all_items
        elif name in cls._all_items:
            return cls._all_items[name]
        elif re.search(r'\w+:\w+', name) and not re.search(r'[A-Z]', name):
            Item._generate_item(name)
            return cls._all_items[name]
        else:
            raise KeyError(f'Invalid item name: {name}')


@dataclass
class ItemStack(Container):
    item: Type[Item] = field(default=None)
    count: int = field(default=None)
    slot: int = field(default=None)
    origin: Container = field(default=None)
    display_name: str = field(default=None)

    def __post_init__(self, *args, **kwargs):
        super(ItemStack, self).__init__(*args, **kwargs)

    @property
    def name(self):
        return self.item.name


@dataclass
class Entity(Container):
    id: str = field(default=None)
    position: Vec3d = field(default=None)

    def __post_init__(self, *args, **kwargs):
        super(Entity, self).__init__(*args, **kwargs)


@dataclass
class Region(ABC):
    region_nbt: dict = field(default=None)
    palette: list = field(default=None)
    block_states: list = field(default=None)
    tile_entities: list = field(default=None)
    entities: list = field(default=None)
    position: Vec3d = field(default=None)
    size: Vec3d = field(default=None)
    volume: int = field(default=None)

    @classmethod
    def from_nbt(cls, region_nbt: dict, init=True) -> 'Region':
        temp = cls()
        temp.region_nbt = region_nbt

        if init:
            temp.parse_metadata()
            temp.parse_block_data()
            temp.parse_tile_entities()
            temp.parse_entities()

        return temp

    @abstractmethod
    def parse_metadata(self):
        pass

    @abstractmethod
    def parse_block_data(self):
        pass

    @abstractmethod
    def parse_tile_entities(self):
        pass

    @abstractmethod
    def parse_entities(self):
        pass

    @abstractmethod
    def get_palette_index(self, index: int) -> int:
        pass

    @abstractmethod
    def block_iterator(self, scan_range: range = None) -> int:
        pass

    @staticmethod
    def set_inventory(container: 'Container', nbt=None):
        # Passing custom nbt tag to start reading from
        if nbt is None:
            nbt = container.nbt
        if 'Items' not in nbt:
            return []

        for i in nbt['Items']:
            temp = ItemStack()
            temp.nbt = i
            temp.item = Item[i['id']]
            temp.count = i['Count']
            try:
                temp.slot = i['Slot']
            except KeyError:
                temp.slot = len(container.inventory)
            temp.origin = container
            temp.inventory = []
            temp.rec_inventory = []

            # Check if the item is a container
            if 'tag' in temp.nbt:
                next_dir = temp.nbt['tag']
                if 'display' in next_dir and 'Name' in next_dir['display']:
                    temp.display_name = re.search(r'(?<="text":").*(?=")', next_dir['display']['Name']).group()
                if 'BlockEntityTag' in next_dir:
                    next_dir = next_dir['BlockEntityTag']
                Region.set_inventory(temp, next_dir)

            # Update container
            container.inventory.append(temp)
            container.rec_inventory.append(temp)
            container.rec_inventory.extend(temp.inventory)


@dataclass
class Structure(ABC):
    """
    Base class for all structures.
    """
    metadata: Metadata = field(default=None)
    regions: dict = field(default=None)
    raw_nbt: dict = field(default=None)
    name: str = field(default=None)

    @classmethod
    def from_file(cls, file_path: str, unpack=True, init=True) -> 'Structure':
        with open(file_path, 'rb') as f:
            nbt = File.load(f, gzipped=True).unpack() if unpack \
                else File.load(f, gzipped=True)
        temp = cls.from_nbt(nbt, init)
        temp.name = os.path.basename(file_path)
        return temp

    @classmethod
    @abstractmethod
    def from_nbt(cls, nbt: dict, init=True) -> 'Structure':
        pass

    @abstractmethod
    def parse_metadata(self, nbt):
        """
        Creates Metadata object from NBT data.
        Should be implemented by subclasses.
        :param nbt: dict of metadata NBT data.
        :return:
        """
        pass

    @abstractmethod
    def parse_regions(self, nbt, init: bool = True):
        pass
