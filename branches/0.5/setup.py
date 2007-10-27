#!/usr/bin/env python
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
            'dist_dir': 'win_release/v0.5',
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
    version = "0.5",
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
