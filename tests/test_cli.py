"""CLI behaviour."""

from __future__ import annotations

import json

from click.testing import CliRunner

from geofuzz.cli import cli
from geofuzz.mutations import MUTATIONS


def test_generate_writes_geometry_to_stdout():
    result = CliRunner().invoke(cli, ["generate", "--geometry", "polygon", "--seed", "42"])
    assert result.exit_code == 0
    geometry = json.loads(result.stdout, parse_constant=float)
    assert geometry["type"] == "Polygon"


def test_generate_is_deterministic_across_invocations():
    runner = CliRunner()
    args = ["generate", "--geometry", "polygon", "--mutations", "self_intersection", "--seed", "42"]
    assert runner.invoke(cli, args).stdout == runner.invoke(cli, args).stdout


def test_generate_feature_flag_includes_provenance():
    result = CliRunner().invoke(
        cli,
        [
            "generate",
            "--geometry",
            "linestring",
            "--mutations",
            "antimeridian",
            "--seed",
            "9",
            "--feature",
        ],
    )
    assert result.exit_code == 0
    document = json.loads(result.stdout, parse_constant=float)
    assert document["type"] == "Feature"
    assert document["properties"]["geofuzz"]["mutations"] == ["antimeridian"]


def test_generate_reports_unknown_mutation_as_a_clean_error():
    result = CliRunner().invoke(cli, ["generate", "--mutations", "nope", "--seed", "1"])
    assert result.exit_code != 0
    assert "Unknown mutation" in result.output


def test_generate_rejects_unknown_geometry_type():
    result = CliRunner().invoke(cli, ["generate", "--geometry", "raster", "--seed", "1"])
    assert result.exit_code != 0
    assert "Unknown geometry type" in result.output


def test_corpus_command_writes_files(tmp_path):
    target = tmp_path / "corpus"
    result = CliRunner().invoke(cli, ["corpus", "--out", str(target)])
    assert result.exit_code == 0
    assert list(target.glob("*.geojson"))


def test_list_mutations_lists_every_registered_mutation():
    result = CliRunner().invoke(cli, ["list-mutations"])
    assert result.exit_code == 0
    for name in MUTATIONS:
        assert name in result.stdout
