from setuptools import setup, find_packages

setup(
    name='litematica-tools',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'mezmorize',
        'nbtlib',
        'storage'
    ],
    entry_points={
        'console_scripts': [
            'litematica = litematica_tools.scripts.cli:cli',
        ],
    },
)
