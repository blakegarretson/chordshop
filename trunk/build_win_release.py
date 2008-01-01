#!/usr/bin/env python
import os, shutil, glob, sys
join = os.path.join
import build_py_release
ver = build_py_release.ver
setup_dir = "setup_temp"
release_dir = "win_release/v%s" % ver

try:
    shutil.rmtree(release_dir)
except: pass
try:
    os.makedirs(release_dir)
except: pass

#build_py_release.go(setup_dir)
#os.chdir(setup_dir)

# create setup
setup_text = """#!/usr/bin/env python
from distutils.core import setup
import py2exe
import glob

manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="Chordshop"
    type="win32"
/>
<description>Chordshop</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24

opts = {"py2exe":
            {
            'excludes' : ['Tkinter', '_imagingtk'],
            'dist_dir': '%(release_dir)s',
            "compressed": 1,
            "optimize": 2,
            "dll_excludes": ['tk84.dll', 'tcl84.dll', '_ssl.pyd',
                            '_renderPM.pyd'],
            #'includes' : ["Pmw"]
            }
        }

chordshop_wx = dict(
    script = "chordshop.py",
    other_resources = [(RT_MANIFEST, 1, manifest_template)],
    icon_resources = [(1, "extras\chordshop.ico")]
    )

cs2pdf_gui_wx = dict(
    script = "cs2pdf_gui.py",
    other_resources = [(RT_MANIFEST, 1, manifest_template)],
    icon_resources = [(1, "extras\chordshop.ico")]
    )

setup(
    version = "%(ver)s",
    options = opts,
    name = "chordshop",
    zipfile = r"lib\library.zip",
    windows = [chordshop_wx, cs2pdf_gui_wx],
    console = ["cs2pdf.py"],
    data_files = [  ("examples", glob.glob("examples/*.*")),
                    ("extras", glob.glob("extras/*.*")),
                    ("licenses", glob.glob("licenses/*.*")),
                    ("docs", glob.glob("docs/*.html")),
                    ("docs/images", glob.glob("docs/images/*.*")),
                    ("", ["chordshop.cfg", "copyright.txt", "chords.cfg"]),
                    ("instruments", glob.glob("instruments/*.*"))],
    )
""" % {'release_dir':release_dir, 'ver':ver}

f = file("setup.py","w")
f.write(setup_text)
f.close()

os.system("python setup.py py2exe")
os.chdir(release_dir)
zipfilename = "chordshop_win_%s.zip" % ver
exefilename = "chordshop_%s.exe" % ver
os.system("7z a -tzip -r -mx=9 ..\%s *.*" % zipfilename)
os.chdir("..")
# ###################################################### InnoSetup
iss_text = '''[Setup]
AppName=Chordshop
AppVerName=Chordshop %(ver)s
AppPublisher=Blake T. Garretson
AppPublisherURL=http://chordshop.sourceforge.net
AppSupportURL=http://chordshop.sourceforge.net
AppUpdatesURL=http://chordshop.sourceforge.net
DefaultDirName={pf}\Chordshop
DefaultGroupName=Chordshop
AllowNoIcons=yes
LicenseFile=v%(ver)s\licenses\GPL.txt
InfoBeforeFile=v%(ver)s\copyright.txt
Compression=lzma
SolidCompression=yes
ChangesAssociations=yes
OutputBaseFilename=chordshop_v%(ver)s
OutputDir=.

[Registry]
Root: HKCR; Subkey: ".pro"; ValueType: string; ValueName: ""; ValueData: "chordprosource"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "chordprosource"; ValueType: string; ValueName: ""; ValueData: "ChordPro Chord Sheet"; Flags: uninsdeletekey
Root: HKCR; Subkey: "chordprosource\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\extras\chords_blue.ico,0"
Root: HKCR; Subkey: "chordprosource\shell\Edit in Chordshop\command"; ValueType: string; ValueName: ""; ValueData: """{app}\chordshop.exe"" ""%%1"""
Root: HKCR; Subkey: "chordprosource\shell\Generate PDF\command"; ValueType: string; ValueName: ""; ValueData: """{app}\cs2pdf_gui.exe"" ""%%1"""
Root: HKCR; Subkey: ".csp"; ValueType: string; ValueName: ""; ValueData: "chordshopsource"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "chordshopsource"; ValueType: string; ValueName: ""; ValueData: "Chordshop Chord Sheet"; Flags: uninsdeletekey
Root: HKCR; Subkey: "chordshopsource\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\extras\chords_red.ico,0"
Root: HKCR; Subkey: "chordshopsource\shell\Edit in Chordshop\command"; ValueType: string; ValueName: ""; ValueData: """{app}\chordshop.EXE"" ""%%1"""
Root: HKCR; Subkey: "chordshopsource\shell\Generate PDF\command"; ValueType: string; ValueName: ""; ValueData: """{app}\chordshop.EXE"" ""%%1"""

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "v%(ver)s\chordshop.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "v%(ver)s\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Chordshop"; Filename: "{app}\chordshop.exe"
Name: "{group}\{cm:UninstallProgram,Chordshop}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Chordshop"; Filename: "{app}\chordshop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\chordshop.exe"; Description: "{cm:LaunchProgram,Chordshop}"; Flags: nowait postinstall skipifsilent
''' % {'release_dir':os.path.abspath(release_dir), 'ver':ver}
iss_fn = 'chordshop_v%s.iss' % ver
f_iss = open(iss_fn, 'w')
f_iss.write(iss_text)
f_iss.close()
os.system('''iscc.exe "%s"''' % iss_fn)
#~ sfx = 'makesfx.exe /zip="%(zipfilename)s" /sfx="%(exefilename)s" /overwrite /title="Chordshop %(ver)s" ' \
#~ '/website="http://chordshop.sourceforge.net" /intro="Welcome to Chordshop! To continue with the installation, ' \
#~ 'just press Next. The program will be extracted and a link will be put on your desktop." ' \
#~ '/defaultpath="$programfiles$\Chordshop" /openexplorerwindow ' \
#~ '/shortcut="$desktop$\Chordshop.lnk|$targetdir$\chordshop.exe" ' #/icon="..\devel\extras\songsheets.ico"
#~ os.system(sfx % {'zipfilename':zipfilename, 'exefilename':exefilename, 'ver':ver})
#~ os.remove(zipfilename)
raw_input("Done.")
