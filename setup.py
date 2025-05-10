"""
Setup script for the Brain Git extension.
"""

from setuptools import setup, find_packages

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-brain",
    version="0.1.0",
    author="FanaticPythoner",
    author_email="nathantrudeau@hotmail.com",
    description="🧠 Eradicate code & asset duplication across projects! Brain repositories serve \"neurons\"—your chosen files, folders, and their dependencies—which Brain then intelligently and selectively syncs into any Git consumer repository. Think submodules, on steroid, and without the headaches.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FanaticPythoner/git-brain",
    packages=find_packages(exclude=[
        "tests*",
        "brain_demo*",
        "docs*",
    ]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "brain=brain.cli:main",
        ],
    },
    install_requires=[
        "packaging>=20.0",
    ],
    keywords="git, extension, code sharing, synchronization, modularity, version control, devops, python, cli"
)