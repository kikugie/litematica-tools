import json
import logging
import re
import time

from .decoder import Region


class MaterialList:
    times = []
    def __init__(self, data: Region):
        self.__load_config()
        self.region = data

    def __load_config(self):
        with open('../litematic_parser/config/block_ignore.json') as f:
            self.__ignored_blocks = json.load(f)
        with open(r'../litematic_parser/config/block_config.json') as f:
            self.__block_configs = json.load(f)

    def block_list(self):
        start = time.time()
        out = {}
        cache = {}
        for i in range(self.region.volume):
            index = self.region.get_block_state(i)
            if index in cache: self.__local_list = cache[index]
            else:
                self.__current = dict(self.region.nbt['BlockStatePalette'][index])
                if self.__current['Name'] in self.__ignored_blocks: continue
                self.__local_list = {str(self.__current['Name']): 1}
                self.__block_state_handler()
                self.__block_handler()
                cache[index] = self.__local_list

            for key, val in self.__local_list.items():
                if key in out:
                    out[key] += val
                else:
                    out[key] = val

        end = time.time()
        self.times.append(end - start)
        print(cache)
        return out

    def __block_handler(self):
        i = str(self.__current['Name'])
        if i not in self.__local_list: return None
        if i not in self.__block_configs: return None
        new = self.__block_configs[i]
        if type(new) == str:
            self.__block_configs[i] = [new]
            new = [new]
        del self.__local_list[i]
        for v in new:
            self.__local_list[v] = 1

    __multi = re.compile('(eggs)|(pickles)|(candles)')

    def __block_state_handler(self):
        i = str(self.__current['Name'])
        if 'Properties' not in self.__current: return None
        blockstates = dict(self.__current['Properties'])
        if ('half', 'upper') in blockstates.items():
            del self.__local_list[i]
        if ('waterlogged', 'true') in blockstates.items():
            self.__local_list['minecraft:water_bucket'] = 1
        test = list(filter(self.__multi.match, blockstates))
        if test:
            self.__local_list[i] = int(blockstates[test[0]])
