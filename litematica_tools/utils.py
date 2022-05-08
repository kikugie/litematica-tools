import json
import logging
import os

from litematica_tools.storage import Item
from litematica_tools.config import CONFIG


class ItemCounter(dict):
    """
    Extended dict class.
    Supports safely adding to values and dict sorting.
    """

    def __init__(self, *args, **kw):
        super(ItemCounter, self).__init__(*args, **kw)
        self._stacks: dict[str, tuple] = {}
        self._names: dict[str, str] = {}

    def _add(self, other: dict):
        for i, v in other.items():
            if i in self:
                self[i] = self[i] + v
            else:
                self[i] = v
        return self

    def __add__(self, other):
        return self._add(other)

    def __iadd__(self, other):
        return self._add(other)

    def extend(self, other: dict):
        for i, v in other.items():
            if i in self:
                self[i] += v
            else:
                self[i] = v
        return None

    def append(self, item: str, amount: int):
        if item in self:
            self[item] += amount
        else:
            self[item] = amount

    def sort(self, reverse=True) -> 'ItemCounter':
        return ItemCounter({i: v for i, v in sorted(self.items(), key=lambda item: item[1], reverse=reverse)})

    @property
    def stacks(self) -> 'ItemCounter':
        if self._stacks.keys() != self.keys():
            for i, v in self.items():
                self._stacks[i] = self.get_stacks(i, v)
        return self._stacks

    @property
    def names(self) -> 'ItemCounter':
        if self._names.keys() != self.keys():
            for i, v in self.items():
                self._names[i] = self.localise(i)
        return self._names

    @staticmethod
    def get_stacks(item: str, count: int) -> tuple:
        ss = Item[item].stack_size
        out = (
            count // (ss * 27),
            count % (ss * 27) // ss,
            count % ss
        )
        if ss == 1:
            out = (out[0], 0, out[1])
        return out

    @staticmethod
    def localise(item: str) -> str:
        if item in CONFIG.name_references:
            return CONFIG.name_references[item]
        logging.warning(f'Localisation missing for {item}, attempting to parse from name.')
        return ' '.join([i.capitalize() for i in item.split('_')])
