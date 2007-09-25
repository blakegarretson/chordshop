import glob, cPickle, base64, zlib

files = glob.glob("*.png")
outfile = file('../images.py','w')
outfile.write('catalog = {} \n\n')
for f in files:
    outfile.write('catalog["%s"] = """\n' % f[:-4])
    outfile.write(base64.encodestring(file(f, "rb").read()))
    outfile.write('"""\n\n')
