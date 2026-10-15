#!/usr/bin/env python3
"""Validate listing constraints and build a root-manifest plugin submission ZIP."""
import argparse, hashlib, json, re, xml.etree.ElementTree as ET, zipfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]

def validate():
    m = json.loads((PKG / 'plugin.json').read_text())
    assert m['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
    assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', m['name']) and len(m['name']) <= 64
    assert m['version'] == (PKG / 'VERSION').read_text().strip()
    assert m['author']['name'] and m['repository'].startswith('https://github.com/')
    extension = m['extensions']['com.openai']; i = extension['interface']
    for key, limit in [('displayName',30),('shortDescription',30),('longDescription',4000),('developerName',80)]:
        assert 0 < len(i[key]) <= limit, key
    assert len(i['defaultPrompt']) <= 3 and all(0 < len(s) <= 128 for s in i['defaultPrompt'])
    for key in ['brandColor','brandColorDark']: assert re.fullmatch('#[0-9A-Fa-f]{6}',i[key])
    paths = [i[k] for k in ['composerIcon','composerIconDark','logo','logoDark']] + i['screenshots']
    for value in paths:
        assert value.startswith('./') and '..' not in Path(value).parts
        p = PKG / value; assert p.is_file() and p.stat().st_size <= 5 * 1024**2, value
        if p.suffix == '.svg':
            r = ET.parse(p).getroot(); box = [float(x) for x in r.attrib['viewBox'].split()]
            assert box[2] == box[3] and box[2] >= 48
    assert not any(k in extension for k in ['apps','hooks'])
    assert not (PKG / 'mcp.json').exists()
    assert (PKG / 'skills/mudelitehas/SKILL.md').is_file()
    original = PKG / 'examples/teddy-walk'
    assert (PKG / i['screenshots'][0]).read_bytes() == (original / 'Jalutav_Mangukaru_Uus.png').read_bytes()
    manifest = json.loads((original / 'canonical-manifest.json').read_text())
    for name, data in manifest['files'].items():
        assert hashlib.sha256((original/name).read_bytes()).hexdigest() == data['sha256'], name
    return m

def build(destination):
    m = validate(); destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"Mudelitehas-{m['version']}-plugin.zip"
    files = [PKG / 'plugin.json']
    for folder in ['assets','skills']:
        files += [p for p in (PKG/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            info = zipfile.ZipInfo(p.relative_to(PKG).as_posix(), (2026,10,15,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644 << 16
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(path) as z:
        assert 'plugin.json' in z.namelist() and z.testzip() is None
    print(json.dumps({'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':'local-validation-passed; portal-validation-pending'}))
    return path

if __name__ == '__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',type=Path,required=True);build(a.parse_args().output)
