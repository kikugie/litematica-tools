import json
import logging
import os
import re
import tempfile

from mezmorize import Cache
from .schematic_parse import NBTFile
from .shared_storage import Region, BlockState

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR=os.path.join(tempfile.gettempdir(), 'litematica_cache'))


class Counter(dict):
    """
    Extended dict class.
    Supports safely adding to values and dict sorting.
    """
    def __init__(self, *args, **kw):
        super(Counter, self).__init__(*args, **kw)

    def __merge(self, other):
        out = self
        for i, v in other.items():
            if i in out:
                out[i] = out[i] + v
            else:
                out[i] = v
        return out

    def __add__(self, other):
        return self.__merge(other)

    def __iadd__(self, other):
        return self.__merge(other)

    def dsort(self, reverse=True):
        return Counter({i: v for i, v in sorted(self.items(), key=lambda item: item[1], reverse=reverse)})

    def localise(self) -> dict:
        """
        Converts minecraft ids to names.
        Names are configured in 'config/name_references.json'.

        :return: Dict of {'<Name>': <amount>, ...}
        """
        source_location = os.path.dirname(os.path.abspath(__file__))
        config_location = os.path.join(source_location, 'config')

        with open(os.path.join(config_location, 'name_references.json'), 'r') as f:
            names = json.load(f)

        # NOT IMPLEMENTED
        # r = re.compile(r'.+Flight:\d+.+')
        # rockets = list(filter(r.match, data))
        #
        # if rockets:
        #     for i in rockets:
        #         duration = re.search(r'(?<=Flight:)\d+', i).group()
        #         names[i] = f"{names['minecraft:firework_rocket']} [{duration}]"

        return {names[i]: v for i, v in self.items()}


class MaterialList:
    """
    Creates advanced material lists from schematic files.
    Uses data parsed by schematic_parse.py.

    Simple usage:
    ```
    from litematica_tools import *

    schem = NBTFile('sample.litematic')
    mat_list = MaterialList(schem)
    print(mat_list.block_list(sort=False, block_mode=True))
    ```

    Latest supported mc version: 1.18.x
    """
    __multi = re.compile('(eggs)|(pickles)|(candles)')

    # used in __block_state_handler() to match one of similar properties

    def __init__(self, nbt: NBTFile = None):
        if nbt:
            self.structure = nbt.data
            self.regions = nbt.data.regions
        self.__load_config()

    def __load_config(self):
        """
        Files:
        - block_ignore.json: List of blocks that will be excluded from the material list.
                             By default, contains blocks that don't have an item.
        - block_config.json: Describes how some blocks should be converted into items.
        - name_references.json: Names matching the in game id.
        - list_options.json: Default options for generating lists.
        - unstackables.json: List of unstackable items as for the latest supported version.
        - 16-stackables.json: List of 16x stackable items as for the latest supported version.
                              See latest supported version in MaterialList.__doc__
        """
        source_location = os.path.dirname(os.path.abspath(__file__))
        config_location = os.path.join(source_location, 'config')

        with open(os.path.join(config_location, 'block_ignore.json'), 'r') as f:
            self.__ignored_blocks = json.load(f)
        with open(os.path.join(config_location, 'block_config.json'), 'r') as f:
            self.__block_configs = json.load(f)
        with open(os.path.join(config_location, 'name_references.json'), 'r') as f:
            self.__names = json.load(f)
        with open(os.path.join(config_location, 'list_options.json'), 'r') as f:
            self.__options = json.load(f)

    def single_region(self, region: Region):
        self.regions = [region]

    def __update_options(self, opts: dict):
        for i, v in opts.items():
            if i in self.__options:
                self.__options[i] = v
            else:
                logging.warning('Unknown option provided, ignoring.')

    def __cache_palette(self, region: Region):
        """
        Precomputes items for block state palette entries for faster lookup.
        """
        self.__cache = {}
        for i, v in enumerate(region.palette):
            if v.name in self.__ignored_blocks:
                continue

            buffer = self.__block_state_handler(v)
            if not self.__options['block_mode']:
                buffer = self.__block_handler(v, buffer)
            self.__cache[i] = buffer

    def __block_state_handler(self, block: BlockState):
        out = {block.name: 1}
        if not block.properties:
            return out

        if ('half', 'upper') in block.properties.items():
            del out[block.name]
        if self.__options['block_mode']:
            return out
        if self.__options['waterlogging']:
            if ('waterlogged', 'true') in block.properties.items():
                out['minecraft:water_bucket'] = 1
        test = list(filter(self.__multi.match, block.properties))
        if test:
            out[block.name] = int(block.properties[test[0]])
        return out

    def __block_handler(self, block: BlockState, buffer):
        if block.name not in buffer:
            return buffer
        if block.name not in self.__block_configs:
            return buffer

        new = self.__block_configs[block.name]
        if type(new) == str:
            self.__block_configs[block.name] = [new]
            new = [new]

        del buffer[block.name]
        for i in new:
            buffer[i] = 1

        return buffer

    def composite_list(self, *, blocks: bool, items: bool, entities: bool, sort=True, **kwargs) -> Counter:
        """
        Combine several material lists in one

        :param blocks: Count blocks.
        :param items: Count items.
        :param entities: Count entities.
        :param sort: Sort output in descending order.
        :param kwargs: Override options.
        :return: Counter of {'minecraft:<id>': <amount>, ...}
        """
        if kwargs:
            self.__update_options(kwargs)

        out = Counter()
        if blocks:
            out += self.block_list(sort=False)
        if items:
            out += self.item_list(sort=False)
        if entities:
            out += self.entity_list(sort=False)

        if sort:
            return out.dsort()
        return out

    def block_list(self, sort=True, **kwargs) -> Counter:
        """
        Counts blocks in all regions of the schematic.
        For specific region use MaterialList.single_region().

        Options:
        - 'block_mode': Count blocks instead of representing item, overrides 'waterlogging'.
        (For example by default (False) converts 'minecraft:spruce_wall_sign' to 'minecraft:spruce_sign')
        - 'waterlogging': Additionally count water buckets for waterlogging blocks.

        :param sort: Sort output in descending order.
        :param kwargs: Override options.
        :return: Counter of {'minecraft:<block item>': <amount>, ...}
        """
        if kwargs:
            self.__update_options(kwargs)

        out = Counter()
        for r in self.regions.values():
            self.__cache_palette(r)

            for i in self.structure.block_iterator(r):
                if i not in self.__cache:
                    continue
                out += self.__cache[i]

        if sort:
            return out.dsort()
        return out

    def item_list(self, sort=True, **kwargs) -> Counter:
        """
        Counts items in all tile entities and entities of the schematic.
        For specific region use MaterialList.single_region().

        Relies on the Schematic.nbt_get_items() to store all instances of Item class created during parsing.

        :param sort: Sort output in descending order.
        :param kwargs: Override options.
        :return: Counter of {'minecraft:<entity>': <amount>, ...}
        """
        if kwargs:
            self.__update_options(kwargs)

        out = Counter()
        temp = {}
        for i in self.structure.items:
            if i.id not in temp:
                temp[i.id] = i.count
            else:
                out += temp
                temp.clear()
                temp[i.id] = i.count
        out += temp

        if sort:
            return out.dsort()
        return out

    def entity_list(self, sort=True, **kwargs) -> Counter:
        """
        Counts entities in all regions of the schematic.
        For specific region use MaterialList.single_region().

        :param sort: Sort output in descending order.
        :param kwargs: Override options.
        :return: Counter of {'minecraft:<entity>': <amount>, ...}
        """
        if kwargs:
            self.__update_options(kwargs)

        out = Counter()
        temp = {}
        for r in self.regions.values():
            for i in r.entities:

                if i.id not in temp:
                    temp[i.id] = 1
                else:
                    out += temp
                    temp.clear()
                    temp[i.id] = 1
        out += temp

        if sort:
            return out.dsort()
        return out
