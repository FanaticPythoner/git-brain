import os
import re
from setuptools import setup, find_packages

def get_version():
    version_file = os.path.join(os.path.dirname(__file__), 'brain', '__init__.py')
    with open(version_file, 'r', encoding='utf-8') as f:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="git-brain",
    version=get_version(),
    author="FanaticPythoner",
    author_email="nathantrudeau@hotmail.com",
    description="🧠 Git extension for intelligent code sharing & synchronization between repositories without duplication.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FanaticPythoner/git-brain",
    project_urls={
        "Homepage": "https://github.com/FanaticPythoner/git-brain",
        "Source Code": "https://github.com/FanaticPythoner/git-brain",
        "Issue Tracker": "https://github.com/FanaticPythoner/git-brain/issues",
        "Documentation": "https://FanaticPythoner.github.io/git-brain/"
    },
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
        "Environment :: Console",
        "Natural Language :: English",
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
    keywords="git, extension, code sharing, synchronization, modularity, version control, devops, python, cli, asset management, neuron",
    license="GPL-3.0"
)
