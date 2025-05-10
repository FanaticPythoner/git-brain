"""
Brain - Git Extension for Code Sharing.

Brain is a Git extension that allows sharing code between repositories
without duplicating it. It uses the concept of "neurons" - files or directories
that are shared from central "brain" repositories.

Basic usage:
    brain init            # Initialize a Git repository
    brain brain-init      # Initialize a brain repository
    brain add-brain       # Add a brain to a repository
    brain add-neuron      # Add a neuron mapping from a brain
    brain pull            # Pull from origin and sync neurons
    brain push            # Push to origin (with neuron protection)

See README.md for more detailed usage instructions.
"""

__version__ = '0.1.0'
