import re

from nbtlib import File
from .litematic_storage import Litematic
from .schem_storage import Schem
from .nbt_storage import Nbt


class NBTFile:
    def __init__(self, filepath, *, lazy=False):
        """
        Opens the NBT file and writes its data to a python values.

        :param filepath: Path to the desired file.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        self.file = filepath

        with open(filepath, 'rb') as f:
            self.raw_nbt = File.load(f, gzipped=True).unpack()

        self.file_format = re.search(r'\w+$', filepath).group()

        match self.file_format:
            case 'litematic':
                self.data = Litematic(nbt=self.raw_nbt, lazy=lazy)
            case 'schem':
                self.data = Schem(nbt=self.raw_nbt, lazy=lazy)
            case 'nbt':
                self.data = Nbt(nbt=self.raw_nbt, lazy=lazy)
            case _: raise FormatError(self.file_format)


class FormatError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'File format {self.message} is not supported!'
