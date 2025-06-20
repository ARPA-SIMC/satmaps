#!/usr/bin/python3

import argparse
import abc
import inspect
import sys
from pathlib import Path
from typing import Any, ClassVar, cast, Generator

import netCDF4 as nc

import numpy

from rich.console import Console
from rich.table import Table

import satpy
from satpy import Scene

# satpy.utils.trace_on()

console = Console()

srcdir = Path(sys.argv[0]).absolute().parent


def _get_first_docstring_line(obj: Any) -> str | None:
    if obj.__doc__ is None:
        raise RuntimeError(f"{obj!r} lacks a docstring")
    return cast(str, obj.__doc__).split("\n")[0].strip().rstrip(".")


class Command(abc.ABC):
    name: ClassVar[str]
    commands: dict[str, type["Command"]] = {}

    def __init_subclass__(cls, name: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if inspect.isabstract(cls):
            return
        cls.name = name or cls.__name__.lower()
        cls.commands[cls.name] = cls

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    @classmethod
    def add_subparsers(cls, subparsers: "argparse._SubParsersAction[Any]") -> None:
        for command_cls in cls.commands.values():
            subparser = subparsers.add_parser(
                command_cls.name, help=_get_first_docstring_line(command_cls)
            )
            command_cls.add_args(subparser)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        pass

    @abc.abstractmethod
    def run(self) -> None:
        """Run the command."""


class SceneCommand(Command, abc.ABC):
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "sources",
            type=Path,
            default=srcdir / "raw",
            nargs="?",
            help="path to the source MTG NetCDF files",
        )

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args)
        self.scene = Scene(reader="fci_l1c_nc", filenames=args.sources.glob("**/*.nc"))


class ProductCommand(SceneCommand, abc.ABC):
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--area",
            "-a",
            action="store",
            default="mtg_fci_fdss_4km",
            help="area of the products to generate",
        )


class Inventory(SceneCommand):
    """Show available datasets."""

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--all", "-a", action="store_true", help="list all variables in the file"
        )

    def run(self) -> None:
        table = Table(title="Contents")
        table.add_column("Name")
        table.add_column("Wavelength")
        table.add_column("Resolution", justify="right")
        table.add_column("Calibration", justify="right")
        if self.args.all:
            data_ids = self.scene.all_dataset_ids()
            table.add_column("Available")
            available: set[str] = set(
                x["name"] for x in self.scene.available_dataset_ids()
            )
        else:
            data_ids = self.scene.available_dataset_ids()
        for data_id in data_ids:
            row = [
                data_id["name"],
                str(wl) if (wl := data_id.get("wavelength")) else "",
                str(data_id["resolution"]),
                cal.name if (cal := data_id.get("calibration")) else "",
            ]
            if self.args.all:
                row.append("yes" if data_id["name"] in available else "no")
            table.add_row(*row)
        console.print(table)


class Composites(SceneCommand):
    """Show available composites."""

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--all", "-a", action="store_true", help="list all variables in the file"
        )

    def run(self) -> None:
        table = Table(title="Composites")
        table.add_column("Name")
        if self.args.all:
            data_ids = self.scene.all_composite_ids()
            table.add_column("Available")
            available = set(
                data_id["name"] for data_id in self.scene.available_composite_ids()
            )
        else:
            data_ids = self.scene.available_composite_ids()
        for data_id in data_ids:
            row = [data_id["name"]]
            if self.args.all:
                row.append("yes" if data_id["name"] in available else "")
            table.add_row(*row)
        console.print(table)


class Generate(ProductCommand, name="gen"):
    """Generate one or more named composites."""

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "products",
            nargs="+",
            help=(
                "names of products to generate." " See `composites` output for a list."
            ),
        )
        parser.add_argument(
            "--output", "-o", type=Path, default=Path("."), help="output directory"
        )

    def run(self) -> None:
        products = self.args.products
        self.scene.load(products)
        area = self.scene.resample(self.args.area)
        self.args.output.mkdir(parents=True, exist_ok=True)
        area.save_datasets(base_dir=self.args.output)


class Vis06(ProductCommand, name="vis_06_hr"):
    """High resolution visible 0.6µm image."""

    def run(self) -> None:
        self.scene.load(["vis_06"])
        # euro = self.scene.resample("euro4")
        euro = self.scene.resample(self.args.area)
        euro.save_dataset("vis_06", "./vis_06_hr.png")


class NetcdfContents(Command, name="ncls"):
    """List contents of a NetCDF file."""

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument("file", metavar="file.nc", type=Path, help="NetCDF file")
        parser.add_argument(
            "--all", "-a", action="store_true", help="list all variables in the file"
        )

    def scan_group(self, path: Path, group) -> Generator[tuple[Path, Any]]:
        for name, subgroup in group.groups.items():
            yield from self.scan_group(path / name, subgroup)
        for name, var in group.variables.items():
            yield path / name, var

    def scan_dataset(self, dataset: Any) -> Generator[tuple[Path, Any]]:
        for name, group in dataset.groups.items():
            yield from self.scan_group(Path("/") / name, group)
        for name, var in dataset.variables.items():
            yield Path("/") / name, var

    def run(self) -> None:
        table = Table(title="Contents")
        table.add_column("Path")
        table.add_column("Shape")
        table.add_column("Min", justify="right")
        table.add_column("Max", justify="right")
        table.add_column("Mean", justify="right")

        ds = nc.Dataset(self.args.file)
        for path, var in self.scan_dataset(ds):
            if path.name == "effective_radiance":
                valid_values = numpy.array(var) != 65535.0
                table.add_row(
                    f"[bold]{path}[/]",
                    str(var.shape),
                    str(numpy.min(var)),
                    str(numpy.max(var, initial=0, where=valid_values)),
                    str(numpy.mean(var, where=valid_values)),
                )
            elif self.args.all:
                table.add_row(str(path), "", "", "", "")
        console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="MTG experiments")
    subparsers = parser.add_subparsers(help="sub-commands", dest="command")
    Command.add_subparsers(subparsers)
    args = parser.parse_args()

    satpy.config.set(config_path=[srcdir / "config"])

    command_cls = Command.commands[args.command]
    command = command_cls(args)
    command.run()


if __name__ == "__main__":
    main()
