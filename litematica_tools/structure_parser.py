import os
from litematica_tools.storage import Litematic, Schem, Nbt
from litematica_tools.errors import FileException


class NBTFile:
    def __new__(cls, file_path: str, unpack: bool = True, init: bool = True):
        file_format = os.path.splitext(file_path)[1]
        if file_format == '.litematic':
            return Litematic.from_file(file_path, unpack, init)
        elif file_format == '.schem':
            return Schem.from_file(file_path, unpack, init)
        elif file_format == '.nbt':
            return Nbt.from_file(file_path, unpack, init)
        else:
            raise FileException(f'Provided not supported file format: {file_format}')
