"""
This module provides a testing framework for the project.
"""

from pathlib import Path
from sys import exc_info
from traceback import format_exception
from typing import Callable

from compiler import compile_query, exceptions

__tests: dict[str, Callable[[], None]] = {}


def test(func: Callable[[], None]) -> Callable:
	"""
	Decorator to mark a function as a test.

	The test description is derived from the function's docstring.

	Returns:
		Callable: The decorated function.
	"""
	description = func.__doc__.strip().strip('.') if func.__doc__ else func.__name__
	__tests[description] = func
	return func


class RaisesError(Exception):
	"""
	Custom exception raised when a test expects an exception but receives a different one.
	"""


class RaisesContext:
	"""
	Context manager to assert that a block of code raises a specific exception.

	Usage:
		with raises(ValueError):
			# Code that should raise ValueError
	"""

	def __init__(self, exception: type[BaseException], *other_exceptions: type[BaseException]) -> None:
		self.exceptions = (exception, *other_exceptions)
		self.excinfo = None

	def __enter__(self) -> None:
		self.excinfo = exc_info()

	def __exit__(self, exc_type, exc_value, tb) -> bool:
		if exc_type not in self.exceptions:
			valid_types = ', '.join(
				exc.__name__ for exc in self.exceptions[:-1]
			)
			valid_types += ' or ' if len(self.exceptions) > 1 else ''
			valid_types += self.exceptions[-1].__name__

			# Alter the exception to be an AssertionError.
			raise RaisesError(
				f'  Expected {valid_types}, but got `{exc_type.__name__}: {exc_value}`'
			) from exc_value

		return True  # Suppress the exception if it matches


def raises(exception: type[BaseException], *other_exceptions: type[BaseException]) -> RaisesContext:
	"""
	Assert that a function raises a specific exception.
	At least one exception type must be provided.

	Args:
		exception (type[BaseException]): The exception type that is expected to be raised.
		other_exceptions (type[BaseException]): Any other exceptions that are expected to be raised.
	"""
	if not issubclass(exception, BaseException):
		raise RaisesError('The provided exceptions must be a subclass of BaseException.')
	if not all(issubclass(exc, BaseException) for exc in other_exceptions):
		raise RaisesError('All provided exceptions must be subclasses of BaseException.')

	return RaisesContext(exception, *other_exceptions)


# Dynamically import and register all tests
for i in [
    f.name[:-3]
    for f in Path(__file__).parent.iterdir()
    if f.name != '__init__.py' and not f.is_dir()
]:
	__import__(f'tests.{i}')


def run_tests() -> None:
	"""
	Run all registered tests.
	"""
	failed_tests: list[str] = []

	for description, function in __tests.items():
		# pylint: disable=broad-exception-caught
		try:
			print(f'{description}...', end=' ')
			function()
			# Print green checkmark for success
			print('\033[92m✓\033[0m')
		except RaisesError as e:
			etype, value, tb = exc_info()
			info = format_exception(etype, value, tb)
			failed_tests.append(f'{info[1]}{e}\n')
			# Print red cross for failure
			print('\033[91m✗\033[0m')
		except AssertionError:
			etype, value, tb = exc_info()
			info, _error = format_exception(etype, value, tb)[-2:]
			failed_tests.append(info)
			# Print red cross for failure
			print('\033[91m✗\033[0m')
		except Exception as e:
			etype, value, tb = exc_info()
			info = format_exception(etype, value, tb)
			failed_tests.append(f'{info[1]}  {etype.__name__ if etype else "<none>"}: {e}\n')
			# Print red cross for failure
			print('\033[91m✗\033[0m')
		# pylint: enable=broad-exception-caught

	if failed_tests:
		print('\033[91mSome tests failed:\033[0m')
		for failure in failed_tests:
			print(failure)

	else:
		print('\033[92mAll tests passed!\033[0m')
