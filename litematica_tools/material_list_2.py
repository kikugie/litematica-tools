import json
import logging
import os
import re
import tempfile

from mezmorize import Cache
from schematic_parser_2 import *

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR=os.path.join(tempfile.gettempdir(), 'litematica_cache'))


class Counter(dict):
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


class MaterialList:
    __multi = re.compile('(eggs)|(pickles)|(candles)')

    # used in __block_state_handler() to match one of similar properties

    def __init__(self, nbt: NBTFile = None):
        if nbt:
            self.data = nbt.data
            self.regions = nbt.data.regions
        self.__load_config()

    def __load_config(self):
        """
                block_ignore.json - List of blocks that will be excluded from the material list.
                By default contains blocks that don't have an item.

                block_config.json - List of items matching the blocks.

                name_references.json - Names matching the in game id

                list_options.json - Default options for generating lists
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
        if block.name not in buffer: return buffer
        if block.name not in self.__block_configs: return buffer

        new = self.__block_configs[block.name]
        if type(new) == str:
            self.__block_configs[block.name] = [new]
            new = [new]

        del buffer[block.name]
        for i in new:
            buffer[i] = 1

        return buffer

    def block_list(self, **kwargs) -> Counter:
        if kwargs:
            self.__update_options(kwargs)

        def get_blocks(data, r):
            out = Counter()
            data.__cache_palette(r)

            for i in range(r.volume):
                index = data.data.get_block_state(r, i)
                if index not in data.__cache:
                    continue
                out += data.__cache[index]
            return out

        gout = Counter()
        for r in self.regions.values():
            try:
                gout = get_blocks(self, r)
            except TypeError:
                logging.warning('No block data in the region, perhaps its in lazy mode?')
                self.data.set_block_data(r)
                gout = get_blocks(self, r)

        return gout.dsort()

    def item_list(self, **kwargs) -> Counter:
        if kwargs:
            self.__update_options(kwargs)

        def get_items(data, r):
            out = Counter()
            for i in Item.instances['tile_entity']:
                out += {i.id: i.count}
            return out

        gout = Counter()
        for r in self.regions.values():
            try:
                gout = get_items(self, r)
            except TypeError:
                logging.warning('No tile entity data in the region, perhaps its in lazy mode?')
                self.data.set_tile_entities(r)
                gout = get_items(self, r)

        return gout.dsort()

    def entity_list(self, **kwargs):
        if kwargs:
            self.__update_options(kwargs)

        def get_items(data, r):
            out = Counter()
            for i in Item.instances['tile_entity']:
                out += {i.id: i.count}
            return out