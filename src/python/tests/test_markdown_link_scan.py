from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner

from whero.doctidex.markdown_links import (
    MarkdownLink,
    _coarse_classify,
    _rg_available,
    _rg_command,
    scan_cross_boundary_links,
)
from whero.doctidex.store.runtime import RuntimeStore


def _link_keys(links: tuple[MarkdownLink, ...]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            link.path,
            link.line,
            link.link_path,
            link.target_path,
            link.boundary_point.path if link.boundary_point is not None else None,
        )
        for link in links
    )


def _scan_keys(git_root: Path) -> tuple[tuple[object, ...], ...]:
    with RuntimeStore(git_root).read_diagnostic_transaction() as transaction:
        return _link_keys(scan_cross_boundary_links(git_root, transaction.model_view()))


@pytest.mark.parametrize(
    ("document_path", "raw_candidate", "expected"),
    [
        ("/index.md", "/external/readme.md", ("target", "/external/readme.md")),
        ("/guides/intro.md", "../external/readme.md", ("target", "/external/readme.md")),
        ("/docs/index.md", "../../outside.md", ("outside-repository", None)),
        ("/index.md", "https://example.com/a.md", ("outside-repository", None)),
        ("/index.md", "", ("unresolved", None)),
        ("/index.md", '</external/my file.md> "title"', ("target", "/external/my file.md")),
    ],
)
def test_coarse_classify(
    document_path: str,
    raw_candidate: str,
    expected: tuple[str, str | None],
) -> None:
    assert _coarse_classify(document_path, raw_candidate) == expected


def test_rg_command_skips_workspace_boundary_exclusions() -> None:
    command = _rg_command(
        Path("/repository"),
        {"/external", "/.doctidex-git/imports/example"},
        "pattern",
    )

    assert "!external" in command
    assert "!external/**" in command
    assert "!.doctidex-git" in command
    assert "!.doctidex-git/**" in command
    assert "!.doctidex-git/imports/example" not in command


@pytest.mark.skipif(not _rg_available(), reason="ripgrep with PCRE2 is not available")
def test_validate_finds_parenthesized_cross_boundary_destination(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "index.md").write_text("[external](/external/readme(1).md)\n")

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 1
    diagnostic = next(item for item in result.payload["diagnostics"] if item["rule"] == "link.target.exists")
    assert diagnostic["details"]["target-path"] == "/external/readme(1).md"


@pytest.mark.skipif(not _rg_available(), reason="ripgrep with PCRE2 is not available")
def test_validate_finds_multiline_cross_boundary_destination(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "index.md").write_text('[external](/external/readme.md\n"title")\n')

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 1
    assert any(item["rule"] == "link.target.exists" for item in result.payload["diagnostics"])


@pytest.mark.skipif(not _rg_available(), reason="ripgrep with PCRE2 is not available")
def test_validate_finds_reference_definition_cross_boundary_link(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "index.md").write_text("[external][ext]\n\n[ext]: /external/readme.md\n")

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 1
    assert any(item["rule"] == "link.target.exists" for item in result.payload["diagnostics"])


def test_validate_ignores_root_escaping_and_external_candidates(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / "index.md").write_text(
        "[outside](../../outside.md)\n"
        "[site](https://example.com/readme.md)\n"
    )

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_falls_back_without_ripgrep(
    initialized_root: Path,
    cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "index.md").write_text("[external](/external/missing.md)\n")
    monkeypatch.setattr("whero.doctidex.markdown_links._rg_available", lambda: False)

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 1
    assert any(item["rule"] == "link.target.exists" for item in result.payload["diagnostics"])


@pytest.mark.skipif(not _rg_available(), reason="ripgrep with PCRE2 is not available")
def test_ripgrep_and_fallback_produce_equal_links(
    initialized_root: Path,
    cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (initialized_root / "external").mkdir()
    (initialized_root / "guides").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "index.md").write_text("[external](/external/missing.md)\n")
    (initialized_root / "guides" / "intro.md").write_text("[external](../external/readme.md)\n")

    ripgrep_links = _scan_keys(initialized_root)
    monkeypatch.setattr("whero.doctidex.markdown_links._rg_available", lambda: False)
    fallback_links = _scan_keys(initialized_root)

    assert ripgrep_links
    assert ripgrep_links == fallback_links


@pytest.mark.skipif(not _rg_available(), reason="ripgrep with PCRE2 is not available")
def test_large_tree_skips_non_candidate_documents_and_matches_fallback(
    initialized_root: Path,
    cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    noise = initialized_root / "noise"
    noise.mkdir()
    for index in range(20):
        (noise / f"{index}.md").write_text(f"[ordinary](/ordinary-{index}.md)\n")
    linked_document = initialized_root / "linked.md"
    linked_document.write_text("[external](/external/missing.md)\n")

    monkeypatch.setattr("whero.doctidex.markdown_links._rg_available", lambda: False)
    fallback_links = _scan_keys(initialized_root)
    monkeypatch.undo()

    original_read_text = Path.read_text
    markdown_reads: list[Path] = []

    def tracking_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.suffix == ".md":
            markdown_reads.append(path)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracking_read_text)
    ripgrep_links = _scan_keys(initialized_root)

    assert ripgrep_links == fallback_links
    assert set(markdown_reads) == {linked_document}
