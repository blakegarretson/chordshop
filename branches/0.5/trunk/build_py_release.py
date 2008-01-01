#!/usr/bin/env python
import os, shutil, glob, sys, re
join = os.path.join
devel_dir = "./"
sys.path.append(devel_dir)
f = file(join(devel_dir,'chordshop.py'))
t = f.read()
f.close()
m = re.search(r'VERSION = "(.+)?"', t)
ver = m.group(1)

files = (["chords.cfg", "chordshop.cfg", "chord.py", 'copyright.txt', 'chordshop.py',
            'images.py', 'cs2pdf.py', 'cs2pdf_gui.py'])
subdirs = [('extras',"*.*"), ('examples',"*.*"), ('instruments',"*.*"), ('licenses',"*.*"), ('docs',"*.html")]

def copyfiles(filelist, destdir):
    for f in filelist:
        shutil.copyfile(f, join(destdir,os.path.basename(f)))

def go(release_dir):
    try:
        shutil.rmtree(release_dir)
    except: pass
    try:
        os.makedirs(release_dir)
    except: pass
    for d, g in subdirs:
        try:
            os.mkdir(join(release_dir,d))
        except: pass
    for d, g in subdirs:
        copyfiles(glob.glob(join(devel_dir, d, g)), join(release_dir,d))
    copyfiles([join(devel_dir,f) for f in files], release_dir)

if __name__ == '__main__':
    release_dir = "release/v%s" % ver
    go(release_dir)
    os.chdir(release_dir)
    os.system("7z a -tzip -r -mm=BZip2 -mx=9 ..\chordshop_py_%s.zip *.*" % ver)
    raw_input("Done.")


