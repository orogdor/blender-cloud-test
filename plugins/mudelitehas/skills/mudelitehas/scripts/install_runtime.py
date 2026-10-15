#!/usr/bin/env python3
"""Install pinned Linux x64 Blender and a Blender-compatible Pillow target."""
import argparse,hashlib,os,platform,shutil,subprocess,sys,tarfile,urllib.request
from pathlib import Path
URL='https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz'
URLS=[URL,URL.replace('download.blender.org','mirror.blender.org'),'https://mirror.clarkson.edu/blender/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz']
SHA256='975c58fcb244273838534bba771e64ad87739216b0f9b39a888531a49a72d845'

def download_archive(archive):
 errors=[];partial=archive.with_suffix(archive.suffix+'.part')
 for url in URLS:
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; Mudelitehas/0.1; Blender runtime installer)'})
   with urllib.request.urlopen(request,timeout=120) as response,partial.open('wb') as target:shutil.copyfileobj(response,target)
   with partial.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
   if digest!=SHA256:raise RuntimeError('Blender archive checksum mismatch')
   partial.replace(archive);return
  except (OSError,RuntimeError) as error:
   partial.unlink(missing_ok=True);errors.append(f'{url}: {error}');print(errors[-1],flush=True)
 raise RuntimeError('Could not download verified Blender archive: '+'; '.join(errors))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
 if platform.system()!='Linux' or platform.machine() not in ['x86_64','AMD64']:p.error('Automatic setup supports Linux x64 only; install Blender 4.5.3 manually on other platforms.')
 directory=a.directory.expanduser().resolve();directory.mkdir(parents=True,exist_ok=True);archive=directory/'blender-4.5.3-linux-x64.tar.xz';blender=directory/'blender-4.5.3-linux-x64/blender'
 if not blender.exists():
  if not archive.exists():download_archive(archive)
  if hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()!=SHA256:raise RuntimeError('Blender archive checksum mismatch')
  with tarfile.open(archive) as t:t.extractall(directory,filter='data')
 target=directory/'py311'
 if not (target/'PIL').exists():subprocess.run([sys.executable,'-m','pip','install','--target',str(target),'--python-version','3.11','--only-binary=:all:','--no-deps','Pillow==11.3.0'],check=True)
 subprocess.run([str(blender),'--version'],check=True)
 print('BLENDER='+str(blender));print('MUDELITEHAS_PYTHONPATH='+str(target))
 if os.environ.get('GITHUB_ENV'):
  with open(os.environ['GITHUB_ENV'],'a') as f:f.write('BLENDER='+str(blender)+'\nMUDELITEHAS_PYTHONPATH='+str(target)+'\n')
if __name__=='__main__':main()
