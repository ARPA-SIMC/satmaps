import abc
import argparse
import inspect
import logging
import sys
from typing import Any, ClassVar, override


class Fail(BaseException):
    """
    Failure that causes the program to exit with an error message.

    No stack trace is printed.
    """


class Success(BaseException):
    """
    Exception raised when a command has been successfully handled, and no
    further processing should happen
    """


def _get_first_docstring_line(obj: Any) -> str | None:
    if obj.__doc__ is None:
        raise RuntimeError(f"{obj!r} lacks a docstring")
    assert isinstance(obj.__doc__, str)
    try:
        return obj.__doc__.split("\n")[0].strip()
    except (AttributeError, IndexError):
        return None


class Command(abc.ABC):
    """Base class for actions run from command line."""

    name: ClassVar[str]
    commands: dict[str, type["Command"]] = {}

    @override
    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:
        """
        Register the command subclass as a command line subcommand.

        Abstract classes will not get registered.

        :param name: if given, this is the subcommand name, otherwise it
          defaults to the lowercased class name.
        """
        super().__init_subclass__(**kwargs)
        if inspect.isabstract(cls):
            return
        cls.name = name or cls.__name__.lower()
        cls.commands[cls.name] = cls

    def __init__(self, args: argparse.Namespace) -> None:
        """Instantiate the command."""
        self.args = args

    @classmethod
    def add_subparsers(
        cls, subparsers: "argparse._SubParsersAction[Any]"
    ) -> None:
        for command_cls in cls.commands.values():
            subparser = subparsers.add_parser(
                command_cls.name, help=_get_first_docstring_line(command_cls)
            )
            command_cls.add_args(subparser)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="verbose output",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="debugging output",
        )

    def setup_logging(self) -> None:
        """Set up logging for the command."""
        FORMAT = "%(asctime)-15s %(levelname)s %(name)s %(message)s"
        if self.args.debug:
            level = logging.DEBUG
        elif self.args.verbose:
            level = logging.INFO
        else:
            level = logging.WARN

        log_handler = logging.StreamHandler(sys.stderr)
        log_handler.setFormatter(logging.Formatter(FORMAT))
        log_handler.setLevel(level)
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.DEBUG)

    @abc.abstractmethod
    def run(self) -> None:
        """Run the command."""
        self.setup_logging()
