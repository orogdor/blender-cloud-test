"""Keep Lab writes within a dedicated root and out of original runs."""
import os
from pathlib import Path

def lab_root():
    value = os.environ.get('MODELFACTORY_LAB_ROOT')
    if value and not Path(value).is_absolute():
        raise ValueError('MODELFACTORY_LAB_ROOT must be absolute')
    return Path(value).resolve() if value else (Path.cwd()/'work/modelfactory-lab').resolve()

def require_lab_path(path):
    path = Path(path).resolve()
    root = lab_root()
    if not path.is_relative_to(root):
        raise ValueError('Lab path must be inside MODELFACTORY_LAB_ROOT: '+str(root))
    for parent in (path, *path.parents):
        if (parent/'.mudelitehas-run.json').exists():
            raise ValueError('Refusing an original ModelFactory/Mudelitehas run')
    return path
