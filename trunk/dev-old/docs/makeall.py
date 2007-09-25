import os, glob, sys

if len(sys.argv) > 1:
    files = sys.argv[1:]
else:
    files = glob.glob("*.asc")

for f in files:
    print "Processing", f
    os.system("asciidoc -b html %s" % f)

raw_input("Done")
