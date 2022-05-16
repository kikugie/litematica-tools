from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="litematica-tools",
    version="1.0.3a1",
    author="KikuGie",
    author_email="kikugie@duck.com",
    description="Python scripts for interacting with litematica and other formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kikugie/litematica-tools",
    project_urls={
        "Bug Tracker": "https://github.com/Kikugie/litematica-tools/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={},
    install_requires=[
        "nbtlib"
    ],
    include_package_data=True
)
