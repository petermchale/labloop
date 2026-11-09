"""Resolve external research tools before starting paid model sessions."""
import os
from pathlib import Path
import re
import shutil
import subprocess


IGV_SETUP = (
    "Install IGV Desktop from https://igv.org/doc/desktop/DownloadPage/ and put "
    "igv or igv.sh on PATH, or pass --igv /path/to/igv.sh. On macOS, LabLoop "
    "also discovers IGV*.app in /Applications and ~/Applications when the app "
    "includes Java. IGV snapshots require a graphical desktop session."
)


def _mac_igv_commands(directories=None):
    directories = directories if directories is not None else (Path('/Applications'), Path.home() / 'Applications')
    apps = [app for directory in directories
            for app in directory.glob('IGV*.app')]
    def version(app):
        return tuple(int(n) for n in re.findall(r'\d+', app.name))
    for app in sorted(apps, key=version, reverse=True):
        contents = app / 'Contents'
        lib = contents / 'Java' / 'lib'
        if not (lib / 'igv.jar').is_file():
            continue
        for java in sorted(contents.glob('jdk*/bin/java'), reverse=True):
            if os.access(java, os.X_OK):
                # The native macOS launcher can ignore CLI arguments. Use the
                # bundled Java entry point, which accepts --batch directly.
                yield [str(java), '-Xmx4g', '-cp', str(lib / '*'), 'org.broad.igv.ui.Main']


def resolve_igv(override=None):
    """Return a verified argv prefix; never install or change a user's PATH."""
    if override:
        executable = shutil.which(str(Path(override).expanduser()))
        if not executable:
            raise ValueError(f'IGV launcher not executable: {override}. {IGV_SETUP}')
        candidates = [[executable]]
    else:
        candidates = [[path] for name in ('igv', 'igv.sh') if (path := shutil.which(name))]
        candidates.extend(_mac_igv_commands())
    failures = []
    for argv in candidates:
        try:
            result = subprocess.run([*argv, '--help'], capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and '--batch' in result.stdout + result.stderr:
                return {'argv': argv, 'usage': 'Append -b /absolute/path/to/batch.txt. '
                        'Use this argv directly; a shell alias is not required. '
                        'CLI availability is verified, but snapshot rendering still '
                        'requires GUI access in the role sandbox.'}
            failures.append(f'{argv[0]}: --help did not confirm --batch support')
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(f'{argv[0]}: {exc}')
    detail = ' '.join(failures) if failures else 'No IGV launcher found.'
    raise ValueError(f'IGV preflight failed. {detail} {IGV_SETUP}')


def prepare_tools(config, *, igv=None):
    required = config.get('required_tools', [])
    if not isinstance(required, list) or any(name != 'igv' for name in required):
        raise ValueError('required_tools must be a list of supported tool names: igv')
    return {'igv': resolve_igv(igv)} if 'igv' in required or igv else {}
