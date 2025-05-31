"""
This module converts a text query into a dict that can be
directly used in a MongoDB query of a string array field.

See the readme for more information on the syntax and usage.
"""

__all__ = ['compile_query', 'exceptions']

from .compiler import compile_query, exceptions
