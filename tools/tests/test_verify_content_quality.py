"""Tests for verify-content-quality.py's purpose-built logic: B7's
duplicate-policy detection and B3's bash/console snippet syntax checks.

The rest of that script (YAML/frontmatter validation, Python snippet
checks, generated-file drift) is exercised by running it directly in
CI/check.sh against this repo's real content — no separate test file
existed before B7. This file covers only logic where synthetic tmp_path
fixtures are actually needed: distinguishing a real policy conflict from
legitimate mentions, and proving the syntax checkers fail on a real
syntax error rather than passing vacuously.
"""
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify-content-quality.py"
spec = importlib.util.spec_from_file_location("verify_content_quality", MODULE_PATH)
vcq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcq)


def _write_source(tmp_path: Path, coverage_line: str = "At Production tier: minimum 80% test coverage.\n") -> None:
    source_dir = tmp_path / "patterns" / "testing"
    source_dir.mkdir(parents=True)
    (source_dir / "COVERAGE_REQUIREMENTS.md").write_text(coverage_line)


def test_flags_a_genuinely_conflicting_number(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "bad.md").write_text("Coverage must be at least 75% for this project.\n")

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert len(errors) == 1
    assert "bad.md" in errors[0]
    assert "75" in errors[0]
    assert "80" in errors[0]


def test_does_not_flag_a_consistent_restatement_with_cross_reference(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "good.md").write_text(
        "Coverage >= 80% (minimum requirement) -- see COVERAGE_REQUIREMENTS.md.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_does_not_flag_a_measured_result_description(tmp_path):
    # The real false positive B7 caught during implementation:
    # .claude/skills/agentic-loops/SKILL.md's "(100% coverage)" describes
    # one file's *measured* test result, not a restated mandate — no
    # mandate-signal word (minimum/required/below/>=/<) appears near it.
    _write_source(tmp_path)
    (tmp_path / "unrelated.md").write_text(
        "This module is tested (100% coverage) as a reference implementation.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_does_not_flag_an_aspirational_stretch_goal_on_an_adjacent_line(tmp_path):
    # The real false positive from the character-window design (rejected
    # during implementation in favor of per-line matching): a checklist's
    # "(minimum requirement)" on one line must not leak into an adjacent
    # "Strive for 90%+ coverage" line and make it look like a restated,
    # conflicting mandate.
    _write_source(tmp_path)
    (tmp_path / "checklist.md").write_text(
        "- [ ] Coverage >= 80% (minimum requirement)\n"
        "- [ ] Strive for 90%+ coverage\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_ignores_fenced_code_blocks(tmp_path):
    # An illustrative example (e.g. README.md's before/after drift demo)
    # showing a *hypothetical* project's wrong number isn't this repo's
    # actual policy and must not be scanned as if it were.
    _write_source(tmp_path)
    (tmp_path / "example.md").write_text(
        "Some prose.\n\n"
        "```markdown\n"
        "Coverage must be at least 70% minimum for this project.\n"
        "```\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_ignores_excluded_directories_and_filenames(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "docs" / "operational" / "reviews").mkdir(parents=True)
    (tmp_path / "docs" / "operational" / "reviews" / "old-review.md").write_text(
        "Coverage must be at least 75% minimum in the old policy.\n"
    )
    (tmp_path / "examples" / "python-project").mkdir(parents=True)
    (tmp_path / "examples" / "python-project" / "README.md").write_text(
        "Aim for 75% coverage minimum in this fixture.\n"
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "Coverage must be at least 75% minimum, changed from the old value.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_reports_a_clear_error_when_source_of_truth_file_is_missing(tmp_path):
    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert len(errors) == 1
    assert "not found" in errors[0]


# B3: wider runnable-snippet validation. check_python_snippets() (the
# existing precedent this mirrors) has no dedicated test of its own — it's
# only ever exercised against real repo content in CI. These two do get a
# deliberately-broken fixture each, proving the check actually fails on a
# real syntax error rather than passing vacuously no matter what's fed in.


def test_check_bash_snippets_flags_a_real_syntax_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "```bash\n"
        "if [ -f foo ]; then\n"
        "  echo missing-fi\n"
        "```\n"
    )

    errors = vcq.check_bash_snippets(sources=[bad])

    assert len(errors) == 1
    assert "bad.md" in errors[0]
    assert "syntax error" in errors[0]


def test_check_bash_snippets_passes_a_valid_multiline_recipe(tmp_path):
    good = tmp_path / "good.md"
    good.write_text(
        "```bash\n"
        "cd ~/my-project\n"
        "cat >> CLAUDE.md <<EOF\n"
        "## Section\n"
        "EOF\n"
        "```\n"
    )

    errors = vcq.check_bash_snippets(sources=[good])

    assert errors == []


def test_check_bash_snippets_reports_missing_source_file(tmp_path):
    errors = vcq.check_bash_snippets(sources=[tmp_path / "nope.md"])

    assert len(errors) == 1
    assert "not found" in errors[0]


def test_check_console_snippets_flags_a_real_syntax_error_in_prompt_lines(tmp_path):
    bad = tmp_path / "bad-demo.md"
    bad.write_text(
        "```console\n"
        "$ if [ -f foo ]; then\n"
        "some output line, not a command\n"
        "```\n"
    )

    errors = vcq.check_console_snippets(sources=[bad])

    assert len(errors) == 1
    assert "bad-demo.md" in errors[0]
    assert "syntax error" in errors[0]


def test_check_console_snippets_ignores_non_prompt_output_lines(tmp_path):
    # Only "$ "-prefixed lines are commands — box-drawing decoration and
    # command output (like docs/DEMO.md's trunk-protection banner) must
    # not be fed to bash -n as if they were shell syntax.
    good = tmp_path / "good-demo.md"
    good.write_text(
        "```console\n"
        "$ echo hello\n"
        "hello\n"
        "╔══════╗\n"
        "$ git status\n"
        "```\n"
    )

    errors = vcq.check_console_snippets(sources=[good])

    assert errors == []
