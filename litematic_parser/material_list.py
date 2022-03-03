import json
import re

from .decoder import Region

class MaterialList:
    __multi = re.compile(
        '(eggs)|(pickles)|(candles)')  # used in __block_state_handler() to match one of similar properties

    def __init__(self, data: Region):
        self.region = data

    def block_list(self, block_mode=False, waterlogged=True):
        self.__block_options = {}
        self.__block_options['block_mode'] = block_mode
        self.__block_options['waterlog'] = waterlogged

        self.__cache_palette()  # apply configs to the region block state palette
        out = {}

        for entry in range(self.region.volume):
            index = self.region.get_block_state(entry)
            if index == 0: continue
            if index not in self.__cache: continue
            out = self.__update_counter(self.__cache[index], out)
        return out

    def item_list(self, tile_entities=True, entities=True, item_frames=True, armor_stands=True):
        self.__item_buffer = {}

        if tile_entities: self.__tile_entity_items()
        if entities: self.__entity_items()
        if item_frames: self.__item_frames()
        if armor_stands: self.__armor_stand_items()

        return self.__item_buffer

    def entity_list(self):
        out = {}
        for i in self.region.nbt['Entities']:
            if i['id'] == 'minecraft:item':
                out = self.__update_counter(self.__get_items([i['Item']]), out)
            else:
                out = self.__update_counter({i['id']: 1}, out)
        return out

    def __cache_palette(self):
        """
        Precomputes items for block state palette entries for faster lookup.
        :return:
        """
        self.__load_config()

        self.__cache = {}
        for i, v in enumerate(self.region.nbt['BlockStatePalette']):
            self.__name = v['Name']

            if self.__name in self.__ignored_blocks: continue
            self.__block_buffer = {self.__name: 1}
            self.__block_state_handler(v)
            if not self.__block_options['block_mode']:
                self.__block_handler(v)

            self.__cache[i] = self.__block_buffer

    def __load_config(self):
        """
        block_ignore.json - List of blocks that will be excluded from the material list.
        By default contains blocks that don't have an item.

        block_config.json - List of items matching the blocks.
        :return:
        """
        with open('../litematic_parser/config/block_ignore.json') as f:
            self.__ignored_blocks = json.load(f)
        with open(r'../litematic_parser/config/block_config.json') as f:
            self.__block_configs = json.load(f)

    def __block_state_handler(self, var):
        """
        Modifies counter according to the block state
        :param var:
        :return:
        """
        if 'Properties' not in var: return None
        block_states = var['Properties']

        if ('half', 'upper') in block_states.items():
            del self.__block_buffer[self.__name]

        if self.__block_options['block_mode']: return None  # prevents modifying counter when block mode is enabled

        if self.__block_options['waterlog']:
            if ('waterlogged', 'true') in block_states.items():
                self.__block_buffer['minecraft:water_bucket'] = 1

        test = list(filter(self.__multi.match, block_states))
        if test:
            self.__block_buffer[self.__name] = int(block_states[test[0]])

    def __block_handler(self):
        """
        Applies modifications from block_config.json
        :param var:
        :return:
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
        :param values:
        :return:
        """
        out = {}

        for i in values:
            if not i: continue
            out = self.__update_counter({i['id']: i['Count']}, out)
            if 'tag' not in i: continue
            if 'BlockEntityTag' in i['tag']:
                container = i['tag']['BlockEntityTag']
            else:
                container = i['tag']
            if 'Items' in container:
                out = self.__update_counter(self.__get_items(container['Items']), out)

        return out

    def __tile_entity_items(self):
        for i in self.region.nbt['TileEntities']:
            if 'Items' not in i: continue
            self.__item_buffer = self.__update_counter(self.__get_items(i['Items']), self.__item_buffer)

    def __entity_items(self):
        for i in self.region.nbt['Entities']:
            if 'Items' not in i: continue
            self.__item_buffer = self.__update_counter(self.__get_items(i['Items']), self.__item_buffer)

    def __item_frames(self):
        for i in self.region.nbt['Entities']:
            if i['id'] != ('minecraft:item_frame' or 'minecraft:glow_item_frame'): continue
            if 'Item' in i:
                self.__item_buffer = self.__update_counter(self.__get_items([i['Item']]), self.__item_buffer)

    def __armor_stand_items(self):
        for i in self.region.nbt['Entities']:
            if i['id'] != 'minecraft:armor_stand': continue
            self.__item_buffer = self.__update_counter(self.__get_items(i['ArmorItems'] + i['HandItems']),
                                                       self.__item_buffer)

    @staticmethod
    def __update_counter(values: dict, source: dict):
        """
        Made to avoid adding values to not existing key
        :param values:
        :param source:
        :return:
        """
        for i, v in values.items():
            if i in source:
                source[i] = source[i] + v
            else:
                source[i] = v
        return source
