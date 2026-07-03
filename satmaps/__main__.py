#!/usr/bin/python3

import abc
import argparse
import logging
import sys
from pathlib import Path
from typing import NamedTuple, override

# import netCDF4 as nc
# import numpy
import satpy
import yaml
from rich.console import Console
from rich.table import Table

# Satpy doesn't currently use __all__ to explicitly export attributes
from satpy import Scene  # type: ignore[attr-defined]

from .cmdline import Command
from .flavours import Flavour

# satpy.utils.trace_on()

console = Console()

srcdir = Path(sys.argv[0]).absolute().parent.parent


class SatmapsCommand(Command, abc.ABC):
    @override
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--recipes",
            "-r",
            type=Path,
            default=srcdir / "recipes",
            help="path to the recipe definitions",
        )
        parser.add_argument(
            "--input",
            "-i",
            type=Path,
            dest="sources",
            default=srcdir / "input",
            help="path to the source files",
        )
        parser.add_argument(
            "--data",
            "-d",
            type=Path,
            default=srcdir / "data",
            help="path to satpy data files",
        )

    @abc.abstractmethod
    @override
    def run(self) -> None:
        super().run()
        # Satpy doesn't currently use __all__ to explicitly export attributes
        satpy.config.set(  # type: ignore[attr-defined]
            config_path=[self.args.recipes / "satpy"]
        )
        satpy.config.set(data_dir=self.args.data.as_posix())  # type: ignore[attr-defined]


class AreaInfo(NamedTuple):
    """Information about an area."""

    name: str
    description: str
    projection: str
    width: int
    height: int
    lat_range: str
    lon_range: str
    local: bool


class Areas(SatmapsCommand):
    """Print available areas."""

    @override
    def run(self) -> None:
        from pyresample.area_config import _create_area_def_from_dict
        from satpy._config import config_search_paths
        from satpy.resample import get_area_def

        super().run()
        areas: list[AreaInfo] = []
        for path_str in config_search_paths("areas.yaml"):
            path = Path(path_str)
            is_local = path.is_relative_to(self.args.recipes)
            with path.open("rt") as fd:
                area_defs = yaml.safe_load(fd)
            for name, area in area_defs.items():
                try:
                    if isinstance(area["projection"], dict):
                        projection = area["projection"]["proj"]
                    else:
                        projection = area["projection"]
                except KeyError:
                    projection = "-"
                # area_def = get_area_def(name)
                area_def = _create_area_def_from_dict(name, area)
                if (
                    extent := getattr(area_def, "area_extent_ll", None)
                ) is not None:
                    lats = sorted((extent[1], extent[3]))
                    lons = sorted((extent[0], extent[2]))
                    lat_range = f"{lats[0]:.3f} to {lats[1]:.3f}"
                    lon_range = f"{lons[0]:.3f} to {lons[1]:.3f}"
                else:
                    lat_range = "-"
                    lon_range = "-"
                areas.append(
                    AreaInfo(
                        name,
                        area.get("description", "no description available"),
                        projection,
                        area_def.width,
                        area_def.height,
                        lat_range,
                        lon_range,
                        is_local,
                    )
                )
        areas.sort(key=lambda info: info.name)
        table = Table(title="Areas")
        table.add_column("Name")
        table.add_column("Description", overflow="fold")
        table.add_column("Proj")
        table.add_column("W", justify="right")
        table.add_column("H", justify="right")
        table.add_column("Lat")
        table.add_column("Lon")
        table.add_column("Source")
        for area in areas:
            table.add_row(
                area.name,
                area.description,
                area.projection,
                str(area.width),
                str(area.height),
                area.lat_range,
                area.lon_range,
                "system" if not area.local else "local",
            )
        console.print(table)


class SceneCommand(SatmapsCommand, abc.ABC):
    """Command working on a Satpy scene."""

    #: Satpy scene used to generate products
    scene: Scene

    # See: https://satpy.readthedocs.io/en/stable/api/satpy.scene.html#satpy.scene.Scene

    @override
    @abc.abstractmethod
    def run(self) -> None:
        super().run()
        self.scene = Scene(
            # Map readers to input files
            filenames={
                # Load FCI products
                "fci_l1c_nc": self.args.sources.glob("**/*.nc"),
            }
        )


class Sources(SceneCommand):
    """Show available source datasets."""

    @override
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            help="also list unavailable source datasets",
        )

    @override
    def run(self) -> None:
        super().run()
        table = Table(title="Contents")
        table.add_column("Name")
        table.add_column("Wavelength")
        table.add_column("Resolution", justify="right")
        table.add_column("Calibration", justify="right")
        if self.args.all:
            data_ids = self.scene.all_dataset_ids()
            table.add_column("Available")
            available: set[str] = {
                x["name"] for x in self.scene.available_dataset_ids()
            }
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
    """Show composites that can be generated from sources."""

    @override
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            help="also list unavailable composites",
        )

    @override
    def run(self) -> None:
        super().run()
        table = Table(title="Composites")
        table.add_column("Name")
        if self.args.all:
            data_ids = self.scene.all_composite_ids()
            table.add_column("Available")
            available = {
                data_id["name"]
                for data_id in self.scene.available_composite_ids()
            }
        else:
            data_ids = self.scene.available_composite_ids()
        for data_id in data_ids:
            row = [data_id["name"]]
            if self.args.all:
                row.append("yes" if data_id["name"] in available else "")
            table.add_row(*row)
        console.print(table)


class FlavourCommand(SceneCommand, abc.ABC):
    """Command that takes a flavour."""

    flavour: Flavour

    @override
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--flavour",
            "-f",
            default="default",
            help="flavour name to use to control processing",
        )

    @abc.abstractmethod
    @override
    def run(self) -> None:
        super().run()
        self.flavour = Flavour.load(
            self.args.recipes / "flavours" / f"{self.args.flavour}.yaml"
        )


class Render(FlavourCommand):
    """Render outputs."""

    @override
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser) -> None:
        super().add_args(parser)
        parser.add_argument(
            "--output",
            "-o",
            type=Path,
            default=srcdir / "output",
            help="output directory",
        )
        parser.add_argument(
            "products",
            nargs="*",
            help=(
                "names of products to generate."
                " Defaults to all available ones."
            ),
        )
        parser.add_argument(
            "--serial",
            action="store_true",
            help="generate composites one at a time. It is slower, but may help understand which ones crash",
        )

    def process_serial(self, todo: dict[str, Path]) -> None:
        for data_id, dest in todo.items():
            logging.info("Generate %s", data_id)
            logging.info("Load...")
            self.scene.load([data_id])
            logging.info("Resample...")
            area = self.scene.resample(self.flavour.area)
            logging.info("Write...")
            area = self.scene.resample(self.flavour.area)
            self.args.output.mkdir(parents=True, exist_ok=True)
            logging.info("%s: writing composite %s", dest, data_id)
            area.save_dataset(data_id, filename=dest.as_posix())

    def process_parallel(self, todo: dict[str, Path]) -> None:
        logging.info("Load...")
        self.scene.load(todo.keys())
        logging.info("Resample...")
        area = self.scene.resample(self.flavour.area)
        logging.info("Write...")
        area = self.scene.resample(self.flavour.area)
        self.args.output.mkdir(parents=True, exist_ok=True)
        for data_id, dest in todo.items():
            logging.info("%s: writing composite %s", dest, data_id)
            area.save_dataset(data_id, filename=dest.as_posix())

    @override
    def run(self) -> None:
        super().run()
        data_ids: list[str]
        if self.args.products:
            data_ids = self.args.products
        else:
            data_ids = [x["name"] for x in self.scene.available_composite_ids()]

        # Compute the list of products to generate
        todo: dict[str, Path] = {}
        for data_id in data_ids:
            if data_id in self.flavour.skip:
                continue
            # TODO: rename composites according to flavour rules if needed
            dest = self.args.output / f"{data_id}.tif"
            if dest.exists():
                logging.info("%s: already exists: preserving old version", dest)
                continue
            todo[data_id] = dest
        logging.info("Selected data IDs: %s", " ".join(sorted(todo)))

        if self.args.serial:
            self.process_serial(todo)
        else:
            self.process_parallel(todo)


# class NetcdfContents(Command, name="ncls"):
#     """List contents of a NetCDF file."""
#
#     @classmethod
#     def add_args(cls, parser: argparse.ArgumentParser) -> None:
#         super().add_args(parser)
#         parser.add_argument(
#             "file", metavar="file.nc", type=Path, help="NetCDF file"
#         )
#         parser.add_argument(
#             "--all",
#             "-a",
#             action="store_true",
#             help="list all variables in the file",
#         )
#
#     def scan_group(self, path: Path, group) -> Generator[tuple[Path, Any]]:
#         for name, subgroup in group.groups.items():
#             yield from self.scan_group(path / name, subgroup)
#         for name, var in group.variables.items():
#             yield path / name, var
#
#     def scan_dataset(self, dataset: Any) -> Generator[tuple[Path, Any]]:
#         for name, group in dataset.groups.items():
#             yield from self.scan_group(Path("/") / name, group)
#         for name, var in dataset.variables.items():
#             yield Path("/") / name, var
#
#     def run(self) -> None:
#         table = Table(title="Contents")
#         table.add_column("Path")
#         table.add_column("Shape")
#         table.add_column("Min", justify="right")
#         table.add_column("Max", justify="right")
#         table.add_column("Mean", justify="right")
#
#         ds = nc.Dataset(self.args.file)
#         for path, var in self.scan_dataset(ds):
#             if path.name == "effective_radiance":
#                 valid_values = numpy.array(var) != 65535.0
#                 table.add_row(
#                     f"[bold]{path}[/]",
#                     str(var.shape),
#                     str(numpy.min(var)),
#                     str(numpy.max(var, initial=0, where=valid_values)),
#                     str(numpy.mean(var, where=valid_values)),
#                 )
#             elif self.args.all:
#                 table.add_row(str(path), "", "", "", "")
#         console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate satellite products")
    subparsers = parser.add_subparsers(help="sub-commands", dest="command")
    Command.add_subparsers(subparsers)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        raise SystemExit(1)

    command_cls = Command.commands[args.command]
    command = command_cls(args)
    command.run()


if __name__ == "__main__":
    main()
