"""geofuzz command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import click

from geofuzz import __version__
from geofuzz.corpus import as_feature, mutation_catalog, write_corpus
from geofuzz.generate import generate_case
from geofuzz.geometry import GEOMETRY_TYPES, UnsupportedGeometryError
from geofuzz.mutations import UnsupportedMutationError


@click.group()
@click.version_option(__version__, prog_name="geofuzz")
def cli() -> None:
    """Generate pathological vector geometries for testing GIS pipelines."""


@cli.command()
@click.option(
    "--geometry", default="polygon", show_default=True, help="point | linestring | polygon"
)
@click.option("--mutations", default=None, help="Comma-separated mutation names.")
@click.option(
    "--mutation-count", type=int, default=None, help="Pick N random applicable mutations."
)
@click.option(
    "--seed", type=int, default=None, help="Seed. Omit for a random one (it is reported)."
)
@click.option("--vertices", type=int, default=8, show_default=True, help="Base vertex count.")
@click.option("--feature", is_flag=True, help="Emit a GeoJSON Feature with provenance properties.")
def generate(
    geometry: str,
    mutations: str | None,
    mutation_count: int | None,
    seed: int | None,
    vertices: int,
    feature: bool,
) -> None:
    """Write one pathological geometry to stdout."""
    names = [part.strip() for part in mutations.split(",") if part.strip()] if mutations else None
    try:
        case = generate_case(
            geometry=geometry,
            mutations=names,
            seed=seed,
            vertices=vertices,
            mutation_count=mutation_count,
        )
    except (UnsupportedGeometryError, UnsupportedMutationError, ValueError) as error:
        raise click.ClickException(str(error)) from error

    payload = as_feature(case) if feature else case["geometry"]
    click.echo(json.dumps(payload, indent=2))
    if seed is None:
        click.echo(f"seed: {case['provenance']['seed']}", err=True)


@cli.command()
@click.option(
    "--out", "out_dir", default="corpus", show_default=True, type=click.Path(path_type=Path)
)
@click.option("--seed", type=int, default=0, show_default=True, help="Base seed for the corpus.")
def corpus(out_dir: Path, seed: int) -> None:
    """Write the reproducible pathological corpus to a directory."""
    written = write_corpus(out_dir, seed=seed)
    for path in written:
        click.echo(str(path))
    click.echo(f"\n{len(written)} files written to {out_dir}/", err=True)


@cli.command("list-mutations")
def list_mutations() -> None:
    """List available mutations and the geometry families they apply to."""
    catalog = mutation_catalog()
    width = max(len(entry["name"]) for entry in catalog)
    for entry in catalog:
        families = ", ".join(entry["families"])
        click.echo(
            f"{entry['name']:<{width}}  [{families}]\n{' ' * width}  {entry['description']}\n"
        )
    click.echo(f"{len(catalog)} mutations. Geometry types: {', '.join(GEOMETRY_TYPES)}.")


def main() -> None:
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
