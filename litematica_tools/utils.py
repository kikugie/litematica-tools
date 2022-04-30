import json
import os


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

    def sort(self, reverse=True):
        return ItemCounter({i: v for i, v in sorted(self.items(), key=lambda item: item[1], reverse=reverse)})

    def get_stacks(self):
        with open(os.path.join(os.path.abspath(__file__), 'config', '16-stackables.json'), 'r') as f:
            qstacks = json.load(f)
        with open(os.path.join(os.path.abspath(__file__), 'config', 'unstackables.json'), 'r') as f:
            nostacks = json.load(f)

        out = ItemCounter()
        for i, v in self.items():
            temp = [0, 0, 0]
            if i in nostacks:
                stack_size = 1
            elif i in qstacks:
                stack_size = 16
            else:
                stack_size = 64

            temp[0] = v // (stack_size * 27)
            temp[1] = v % (stack_size * 27) // stack_size
            temp[2] = v % stack_size
            out[i] = temp
        return out

    def localise(self) -> dict:
        """
        Converts minecraft ids to names.
        Names are configured in 'config/name_references.json'.

        :return: Dict of {'<Name>': <amount>, ...}
        """

        with open(os.path.join(os.path.abspath(__file__), 'config', 'name_references.json'), 'r') as f:
            names = json.load(f)
        return ItemCounter({names[i]: v for i, v in self.items()})
