import os

class NBTFile:
    def __new__(cls, file_path: str, unpack: bool = True, init: bool = True):
        file_format = os.path.splitext(file_path)[1]
        if file_format == '.litematic':
            return Litematic.open_file(file_path, unpack, init)
        else:
            raise FileException(f'Provided not supported file format: {file_format}')



