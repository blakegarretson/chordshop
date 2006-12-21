#!/usr/bin/env python
import os
import build_py_release
ver = build_py_release.ver
outfilename = "chordshop_src_%s" % ver
devel_release_dir = "..\\devel_releases\\"
release_dir = devel_release_dir + outfilename

os.system('''TortoiseProc.exe /command:export /path:"%s" /notempfile /closeonend''' % release_dir)

os.chdir(devel_release_dir)
zipfilename = outfilename+".zip"
os.system("7za a -tzip -r -mx=9 %s %s\\*" % (zipfilename,outfilename))

raw_input("Done.")
