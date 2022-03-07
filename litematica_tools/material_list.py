import json
import os
import re
import tempfile

from .schematic_parse import Schematic, Region
from mezmorize import Cache

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR=os.path.join(tempfile.tempdir, 'litematica_cache'))


def dsort(data: dict):
    return {i: v for i, v in sorted(data.items(), key=lambda item: item[1], reverse=True)}


def localise(data: dict):
    source_location = os.path.dirname(os.path.abspath(__file__))
    config_location = os.path.join(source_location, 'config')

    with open(os.path.join(config_location, 'name_references.json'), 'r') as f:
        names = json.load(f)

    r = re.compile('.+Flight:\d+.+')
    rockets = list(filter(r.match, data))

    if rockets:
        for i in rockets:
            duration = re.search('(?<=Flight:)\d+', i).group()
            names[i] = f"{names['minecraft:firework_rocket']} [{duration}]"

    return {names[i]: v for i, v in data.items()}


class MaterialList:
    def __init__(self, data: Schematic):
        self.regions = data.regions

    @cache.memoize()
    def block_list(self, block_mode=False, waterlogging=True):
        out = Counter()
        for i in self.regions.values():
            out += RegionMatList(i).block_list(block_mode, waterlogging)

        return out.data

    @cache.memoize()
    def item_list(self, tile_entities=True, entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        out = Counter()
        for i in self.regions.values():
            out += RegionMatList(i).item_list(tile_entities, entities, item_frames, armor_stands)

        return out.data

    @cache.memoize()
    def entity_list(self):
        out = Counter()
        for i in self.regions.values():
            out += RegionMatList(i).entity_list()

        return out.data

    @cache.memoize()
    def totals_list(self, block_mode=False, waterlogging=True, tile_entities=True,
                    entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        out = Counter()

        out += self.block_list(block_mode, waterlogging)
        out += self.item_list(tile_entities, entities, item_frames, armor_stands, rocket_duration)
        out += self.entity_list()

        return out.data

    @cache.memoize()
    def composite_list(self, blocks: bool, items: bool, entities: bool,
                       block_mode=False, waterlogging=True, tile_entities=True,
                       entity_items=True, item_frames=True, armor_stands=True, rocket_duration=True):
        out = Counter()
        if blocks:
            out += self.block_list(block_mode, waterlogging)
        if items:
            out += self.item_list(tile_entities, entity_items, item_frames,
                                                  armor_stands, rocket_duration)
        if entities:
            out += self.entity_list()

        return out.data


class RegionMatList:
    __multi = re.compile(
        '(eggs)|(pickles)|(candles)')  # used in __block_state_handler() to match one of similar properties

    def __init__(self, data: Region):
        self.region = data
        self.__options = {
            'block_mode': False,
            'waterlogging': True,
            'tile_entities': True,
            'entities': True,
            'item_frames': True,
            'armor_stands': True,
            'rocket_duration': True
        }

    @cache.memoize()
    def block_list(self, block_mode=False, waterlogging=True):
        self.__options['block_mode'] = block_mode
        self.__options['waterlogging'] = waterlogging

        self.__cache_palette()  # apply configs to the region block state palette
        out = Counter()

        for entry in range(self.region.volume):
            index = self.region.get_block_state(entry)
            if index == 0 or index not in self.__cache: continue
            out += self.__cache[index]

        return out.data

    @cache.memoize()
    def item_list(self, tile_entities=True, entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        self.__options['rocket_duration'] = rocket_duration
        out = Counter()

        if tile_entities:
            out += self.__tile_entity_items()
        if entities:
            out += self.__entity_items()
        if item_frames:
            out += self.__item_frames()
        if armor_stands:
            out += self.__armor_stand_items()

        return out.data

    @cache.memoize()
    def entity_list(self):
        out = Counter()
        for i in self.region.nbt['Entities']:
            if i['id'] == 'minecraft:item':
                out += self.__get_items([i['Item']])
            else:
                out += {i['id']: 1}

        return out.data

    def __cache_palette(self):
        """
        Precomputes items for block state palette entries for faster lookup.
        """
        self.__load_config()

        self.__cache = {}
        for i, v in enumerate(self.region.nbt['BlockStatePalette']):
            self.__name = v['Name']

            if self.__name in self.__ignored_blocks: continue
            self.__block_buffer = {self.__name: 1}
            self.__block_state_handler(v)
            if not self.__options['block_mode']:
                self.__block_handler()

            self.__cache[i] = self.__block_buffer

    def __load_config(self):
        """
        block_ignore.json - List of blocks that will be excluded from the material list.
        By default contains blocks that don't have an item.

        block_config.json - List of items matching the blocks.
        """
        source_location = os.path.dirname(os.path.abspath(__file__))
        config_location = os.path.join(source_location, 'config')

        with open(os.path.join(config_location, 'block_ignore.json'), 'r') as f:
            self.__ignored_blocks = json.load(f)
        with open(os.path.join(config_location, 'block_config.json'), 'r') as f:
            self.__block_configs = json.load(f)

    def __block_state_handler(self, var):
        """
        Modifies counter according to the block state
        :param var:
        
        """
        if 'Properties' not in var: return None
        block_states = var['Properties']

        if ('half', 'upper') in block_states.items():
            del self.__block_buffer[self.__name]

        if self.__options['block_mode']: return None  # prevents modifying counter when block mode is enabled

        if self.__options['waterlogging']:
            if ('waterlogged', 'true') in block_states.items():
                self.__block_buffer['minecraft:water_bucket'] = 1

        test = list(filter(self.__multi.match, block_states))
        if test:
            self.__block_buffer[self.__name] = int(block_states[test[0]])

    def __block_handler(self):
        """
        Applies modifications from block_config.json
        """
        if self.__name not in self.__block_buffer: return None
        if self.__name not in self.__block_configs: return None

        new = self.__block_configs[self.__name]
        if type(new) == str:
            self.__block_configs[self.__name] = [new]
            new = [new]

        del self.__block_buffer[self.__name]
        for v in new:
            self.__block_buffer[v] = 1

    def __get_items(self, values: list):  # Pass list of 'Items' key
        """
        Recursively searches for items in provided list.
        """
        out = Counter()

        for i in values:
            if not i: continue

            if 'tag' in i:
                if 'BlockEntityTag' in i['tag']:
                    container = i['tag']['BlockEntityTag']
                else:
                    container = i['tag']

                if 'Items' in container:
                    out += self.__get_items(container['Items'])

                if self.__options['rocket_duration']:
                    if (i['id'] == 'minecraft:firework_rocket') and 'Fireworks' in i['tag']:
                        tag = f"{{Fireworks:{{Flight:{i['tag']['Fireworks']['Flight']}}}}}"
                        out += {f"{i['id']}{tag}": i['Count']}
                        continue
            out += {i['id']: i['Count']}

        return out

    def __tile_entity_items(self):
        out = Counter()
        for i in self.region.nbt['TileEntities']:
            if 'Items' not in i: continue
            out += self.__get_items(i['Items'])
        return out

    def __entity_items(self):
        out = Counter()
        for i in self.region.nbt['Entities']:
            if 'Items' not in i: continue
            out += self.__get_items(i['Items'])
        return out

    def __item_frames(self):
        out = Counter()
        for i in self.region.nbt['Entities']:
            if i['id'] != ('minecraft:item_frame' or 'minecraft:glow_item_frame'): continue
            if 'Item' in i:
                out += self.__get_items([i['Item']])
        return out

    def __armor_stand_items(self):
        out = Counter()
        for i in self.region.nbt['Entities']:
            if i['id'] != 'minecraft:armor_stand': continue
            out += self.__get_items(i['ArmorItems'] + i['HandItems'])
        return out


class Counter:
    def __init__(self, values=None):
        if values is None:
            values = {}
        self.data = values

    def __merge(self, other):
        d1 = self.data
        if isinstance(other, Counter):
            d2 = other.data
        elif isinstance(other, dict):
            d2 = other
        else:
            raise ValueError('Trying to merge non-dict type!')
        for i, v in d2.items():
            if i in d1:
                d1[i] = d1[i] + v
            else:
                d1[i] = v
        return Counter(d1)

    def __add__(self, other):
        return self.__merge(other)

    def __iadd__(self, other):
        return self.__merge(other)
