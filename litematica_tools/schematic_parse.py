import os
import pickle
import re
import logging

from nbtlib import File
from .storage import *
from hashlib import md5

logging.basicConfig(level=logging.INFO)
CACHE_DIR = '../cache/files'

class NBTFile:
    def __init__(self, filepath, *, lazy=False, unpack=True, cache=True):
        """
        Opens the NBT file and writes its data to a python values.

        :param filepath: Path to the desired file.
        :param lazy: Optional parameter for decoding nbt.
                     Reduces the decoded information, decreasing object creation time.
        """
        self.file = filepath

        with open(filepath, 'rb') as f:
            def load_nbt(file):
                f.seek(0)
                return File.load(file, gzipped=True).unpack() if unpack else File.load(file, gzipped=True)

            if cache:
                file_hash = md5('{}.{}'.format(
                    f.read(),
                    unpack
                ).encode('utf-8')).hexdigest()

                cache_path = os.path.join(CACHE_DIR, str(file_hash))
                logging.debug(f'File hash: {file_hash}')

                if os.path.exists(cache_path):
                    with open(cache_path, 'rb') as ff:
                        self.raw_nbt = pickle.load(ff)
                else:
                    self.raw_nbt = load_nbt(f)
                    with open(cache_path, 'wb') as ff:
                        pickle.dump(self.raw_nbt, ff)
            else:
                self.raw_nbt = load_nbt(f)

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
