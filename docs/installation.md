Installation
------------

Brain is a Python package and can be installed using `pip`.

### Prerequisites

*   **Python**: Version 3.7 or higher (as per `setup.py` `python_requires=">=3.7"`).
*   **Git**: Brain is a Git extension, so a working Git installation is essential and must be available in your system's PATH.
*   **pip**: Python's package installer, usually comes with Python.

### Installation Steps

To install the `git-brain` package from PyPI, run the following command in your terminal:

```bash
pip install git-brain
```

This command will download Brain from the Python Package Index (PyPI) and install it along with its dependencies (currently `packaging>=20.0` as per `setup.py`).

### Verifying Installation

After installation, you can verify that Brain is correctly installed by checking its help message for a command:

```bash
brain --help
```
This should display the main usage information for Brain. Alternatively, try:
```bash
brain list --help
```

If Brain is installed correctly, this will display the help message for the `list` command. If the `brain` command is not found, ensure that the directory containing Python scripts (pip's `bin` or `Scripts` directory, or the relevant virtual environment's `bin` directory) is in your system's `PATH`.