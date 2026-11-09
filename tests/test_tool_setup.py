import json
import sys

import pytest

from labloop import cli, tool_setup


@pytest.fixture
def isolated_discovery(monkeypatch):
    monkeypatch.setattr(tool_setup.shutil, 'which', lambda name: None)
    monkeypatch.setattr(tool_setup, '_mac_igv_commands', lambda: [])


def launcher(path, *, success=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!{sys.executable}\nimport sys\n'
                    f'print({"--batch -b" if success else "not IGV"!r})\n')
    path.chmod(0o755)
    return str(path)


def test_explicit_launcher_with_spaces(tmp_path, monkeypatch):
    path = launcher(tmp_path / 'IGV install' / 'igv.sh')
    monkeypatch.setattr(tool_setup.shutil, 'which', lambda name: path if name == path else None)
    assert tool_setup.resolve_igv(path)['argv'] == [path]


def test_missing_and_invalid_override_are_actionable(isolated_discovery):
    with pytest.raises(ValueError, match='No IGV launcher found.*--igv'):
        tool_setup.resolve_igv()
    with pytest.raises(ValueError, match='not executable'):
        tool_setup.resolve_igv('/missing/igv')


def test_path_falls_back_to_mac_java(tmp_path, monkeypatch):
    bad = launcher(tmp_path / 'igv', success=False)
    java = launcher(tmp_path / 'Java bundle' / 'java')
    command = [java, '-cp', str(tmp_path / 'lib' / '*'), 'org.broad.igv.ui.Main']
    monkeypatch.setattr(tool_setup.shutil, 'which', lambda name: bad if name == 'igv' else None)
    monkeypatch.setattr(tool_setup, '_mac_igv_commands', lambda: [command])
    assert tool_setup.resolve_igv()['argv'] == command
    # An explicit bad launcher must not silently fall back to another install.
    with pytest.raises(ValueError, match='did not confirm --batch'):
        tool_setup.resolve_igv('igv')


def test_mac_discovery_prefers_newer_app_and_bundled_java(tmp_path):
    for version in ('2.9.0', '2.19.6'):
        contents = tmp_path / f'IGV_{version}.app' / 'Contents'
        lib = contents / 'Java' / 'lib'
        lib.mkdir(parents=True)
        (lib / 'igv.jar').touch()
        launcher(contents / 'jdk-21' / 'bin' / 'java')
    commands = list(tool_setup._mac_igv_commands([tmp_path]))
    assert len(commands) == 2
    assert '2.19.6' in commands[0][0]
    assert commands[0][-1] == 'org.broad.igv.ui.Main'


def test_timeout_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_setup.shutil, 'which', lambda name: '/fake/igv')
    def timeout(*args, **kwargs):
        raise tool_setup.subprocess.TimeoutExpired(args[0], 15)
    monkeypatch.setattr(tool_setup.subprocess, 'run', timeout)
    with pytest.raises(ValueError, match='preflight failed.*timed out'):
        tool_setup.resolve_igv('igv')


def test_other_tasks_do_not_require_igv(isolated_discovery):
    assert tool_setup.prepare_tools({}) == {}
    with pytest.raises(ValueError, match='supported tool names'):
        tool_setup.prepare_tools({'required_tools': ['unknown']})


def test_cli_preflight_stops_before_codex_and_run_creation(tmp_path, monkeypatch, isolated_discovery):
    config = tmp_path / 'task.json'
    config.write_text(json.dumps({'goal': 'Test', 'criteria': 'Test', 'distill': 'Test',
                                 'required_tools': ['igv']}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['labloop', 'run', str(config)])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert not (tmp_path / 'runs').exists()
    assert not (tmp_path / 'vault').exists()


def test_demo_skips_external_tool_requirements(tmp_path, monkeypatch, isolated_discovery):
    config = tmp_path / 'task.json'
    config.write_text(json.dumps({'goal': 'Test', 'criteria': 'Test', 'distill': 'Test',
                                 'required_tools': ['igv']}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['labloop', 'run', str(config), '--demo', '--cycles', '1'])
    cli.main()
    assert next((tmp_path / 'runs').glob('*/run.json')).exists()
