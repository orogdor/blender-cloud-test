#!/usr/bin/env python3
"""Install pinned Linux x64 Blender and a Blender-compatible Pillow target."""
import argparse,hashlib,os,platform,subprocess,sys,tarfile,urllib.request
from pathlib import Path
URL='https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz'
SHA256='975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
 if platform.system()!='Linux' or platform.machine() not in ['x86_64','AMD64']:p.error('Automatic setup supports Linux x64 only; install Blender 4.5.3 manually on other platforms.')
 directory=a.directory.expanduser().resolve();directory.mkdir(parents=True,exist_ok=True);archive=directory/'blender-4.5.3-linux-x64.tar.xz';blender=directory/'blender-4.5.3-linux-x64/blender'
 if not blender.exists():
  if not archive.exists():urllib.request.urlretrieve(URL,archive)
  if hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()!=SHA256:raise RuntimeError('Blender archive checksum mismatch')
  with tarfile.open(archive) as t:t.extractall(directory,filter='data')
 target=directory/'py311'
 if not (target/'PIL').exists():subprocess.run([sys.executable,'-m','pip','install','--target',str(target),'--python-version','3.11','--only-binary=:all:','--no-deps','Pillow==11.3.0'],check=True)
 subprocess.run([str(blender),'--version'],check=True)
 print('BLENDER='+str(blender));print('MUDELITEHAS_PYTHONPATH='+str(target))
 if os.environ.get('GITHUB_ENV'):
  with open(os.environ['GITHUB_ENV'],'a') as f:f.write('BLENDER='+str(blender)+'\nMUDELITEHAS_PYTHONPATH='+str(target)+'\n')
if __name__=='__main__':main()
