import json
import os

from litematica_tools.storage import Item


class ItemCounter(dict):
    """
    Extended dict class.
    Supports safely adding to values and dict sorting.
    """

    def __init__(self, *args, **kw):
        super(ItemCounter, self).__init__(*args, **kw)

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

    def get_stacks(self) -> 'ItemCounter':
        out = ItemCounter()
        for i, v in self.items():
            temp = [0, 0, 0]
            temp[0] = v // (Item[i].stack_size * 27)
            temp[1] = v % (Item[i].stack_size * 27) // Item[i].stack_size
            temp[2] = v % Item[i].stack_size
            out[i] = temp
        return out

    def localise(self) -> 'ItemCounter':
        """
        Converts minecraft ids to names.
        Names are configured in 'config/name_references.json'.

        :return: Dict of {'<Name>': <amount>, ...}
        """

        with open(os.path.join(os.path.abspath(__file__), '..', 'config', 'name_references.json'), 'r') as f:
            names = json.load(f)
        return ItemCounter({names[i]: v for i, v in self.items()})
