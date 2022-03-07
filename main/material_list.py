import json
import re

from .schematic_parse import Schematic, Region

from mezmorize import Cache

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR='../main/schematic_cache')

def merge_dicts(values: dict, source: dict):
    """
    Made to avoid adding values to not existing key
    """
    for i, v in values.items():
        if i in source:
            source[i] = source[i] + v
        else:
            source[i] = v
    return source


def sort(data: dict):
    return {i: v for i, v in sorted(data.items(), key=lambda item: item[1], reverse=True)}


def localize(data: dict):
    with open(r'../main/config/name_references.json') as f:
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
        out = {}
        for i in self.regions.values():
            out = merge_dicts(RegionMatList(i).block_list(block_mode, waterlogging), out)

        return out

    @cache.memoize()
    def item_list(self, tile_entities=True, entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        out = {}
        for i in self.regions.values():
            out = merge_dicts(
                RegionMatList(i).item_list(tile_entities, entities, item_frames, armor_stands), out)

        return out

    @cache.memoize()
    def entity_list(self):
        out = {}
        for i in self.regions.values():
            out = merge_dicts(RegionMatList(i).entity_list(), out)

        return out

    @cache.memoize()
    def totals_list(self, block_mode=False, waterlogging=True, tile_entities=True,
                    entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        out = {}
        out = merge_dicts(self.item_list(tile_entities, entities, item_frames, armor_stands, rocket_duration),
                          self.block_list(block_mode, waterlogging))
        out = merge_dicts(self.entity_list(), out)

        return out


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
        self.__options['waterlog'] = waterlogging

        self.__cache_palette()  # apply configs to the region block state palette
        out = {}

        for entry in range(self.region.volume):
            index = self.region.get_block_state(entry)
            if index == 0: continue
            if index not in self.__cache: continue
            out = merge_dicts(self.__cache[index], out)

        return out

    @cache.memoize()
    def item_list(self, tile_entities=True, entities=True, item_frames=True, armor_stands=True, rocket_duration=True):
        self.__options['rocket_duration'] = rocket_duration
        self.__item_buffer = {}

        if tile_entities: self.__tile_entity_items()
        if entities: self.__entity_items()
        if item_frames: self.__item_frames()
        if armor_stands: self.__armor_stand_items()

        return self.__item_buffer

    @cache.memoize()
    def entity_list(self):
        out = {}
        for i in self.region.nbt['Entities']:
            if i['id'] == 'minecraft:item':
                out = merge_dicts(self.__get_items([i['Item']]), out)
            else:
                out = merge_dicts({i['id']: 1}, out)

        return out

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
        with open('../main/config/block_ignore.json', 'r') as f:
            self.__ignored_blocks = json.load(f)
        with open('../main/config/block_config.json', 'r') as f:
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

        if self.__options['waterlog']:
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
        out = {}

        for i in values:
            if not i: continue

            if 'tag' in i:
                if 'BlockEntityTag' in i['tag']:
                    container = i['tag']['BlockEntityTag']
                else:
                    container = i['tag']

                if 'Items' in container:
                    out = merge_dicts(self.__get_items(container['Items']), out)

                if self.__options['rocket_duration']:
                    if (i['id'] == 'minecraft:firework_rocket') and 'Fireworks' in i['tag']:
                        tag = f"{{Fireworks:{{Flight:{i['tag']['Fireworks']['Flight']}}}}}"
                        out = merge_dicts({f"{i['id']}{tag}": i['Count']}, out)
                        continue
            out = merge_dicts({i['id']: i['Count']}, out)

        return out

    def __tile_entity_items(self):
        for i in self.region.nbt['TileEntities']:
            if 'Items' not in i: continue
            self.__item_buffer = merge_dicts(self.__get_items(i['Items']), self.__item_buffer)

    def __entity_items(self):
        for i in self.region.nbt['Entities']:
            if 'Items' not in i: continue
            self.__item_buffer = merge_dicts(self.__get_items(i['Items']), self.__item_buffer)

    def __item_frames(self):
        for i in self.region.nbt['Entities']:
            if i['id'] != ('minecraft:item_frame' or 'minecraft:glow_item_frame'): continue
            if 'Item' in i:
                self.__item_buffer = merge_dicts(self.__get_items([i['Item']]), self.__item_buffer)

    def __armor_stand_items(self):
        for i in self.region.nbt['Entities']:
            if i['id'] != 'minecraft:armor_stand': continue
            self.__item_buffer = merge_dicts(self.__get_items(i['ArmorItems'] + i['HandItems']),
                                             self.__item_buffer)
