#!/usr/bin/env python
"""
usage: cs2pdf <file>

    Where <file> can be a single ChordPro (or ChordPro Plus)
    file or a Songbook collection file.

Copyright (C) 2004-2007 Blake T. Garretson

Email: blake@blakeg.net

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the Licensed.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
USA.

"""

import sys, os, copy, glob, chord, re
from reportlab.lib.colors import white, black, red, blue
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import *
from reportlab.graphics import renderPDF
#from optparse import OptionParser, OptionGroup
#progdir = os.path.dirname(__file__)


# this bizarre conditional is so py2exe works
if globals().has_key('__file__') and __name__ == '__main__':
    progdir = os.path.dirname(__file__)
else:
    progdir = os.path.dirname(os.path.abspath(sys.argv[0]))

default_configfile = os.path.join(progdir,"chordshop.cfg")

class Error(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

def errorGUI(string):
    import wx
    class ErrorDialog(wx.App):
        def OnInit(self):
            frame = wx.MessageDialog(None, string, 'Error', wx.OK | wx.ICON_INFORMATION)
            frame.ShowModal()
            return True
    err = ErrorDialog(0)
    err.MainLoop()

class Container:
    pass

class Config:
    def __init__(self, configfile):
        f = file(configfile, 'r')
        try:
            for line in f.readlines():
                line = line.strip()
                if (not line.startswith("#")) and line:
                    var, val = [x.strip() for x in line.split('=')]
                    self.set_value(var, val)
        except:
            raise Error, "Config file problem on this line: '%s'" % line
        f.close()
    def set_value(self, var, val):
        """
        var will look like "index" or "fonts.comments_face"
        """
        fqv = var.split(".")
        container = ""
        for c in fqv[:-1]:
            if not eval("hasattr(self%s, '%s')" % (container, c)):
                container = container+"."+c
                exec("self%s = Container()" % container)
        #print "self.%s = %s" % (var, val)
        try:
            exec("self.%s = %s" % (var, val))
        except NameError: # the user probably forgot to quote the values?
            # Must be consistently right or wrong:
            #   This will work if the user entered C,D,G but not C,'D','G'
            #
            # make them strings
            if ',' in val:
                exec("self.%s = %s" % (var, ",".join(["'%s'" % x.strip() for x in val.split(",")])))
            else:
                exec("self.%s = '%s'" % (var, val))
            #error("Problem setting config variable:\n    %s = %s\nThe value(s) probably need to be quoted." % (var,val))
    def __repr__(self):
        items = dir(self)
        return "\n".join(items)

config = Config(default_configfile)


class ChordProPlusFile:
    """
    This module should be imported to handle ChordPro Plus files.
    It parses files and offers convenience functions such as transposing.

    self.measures = [
        {
        'type':'directive',
        'directive':'timing',
        'data':'4/4'
        }
        {
        'type':'bar',
        'data':'|:',
        'repeat':'',
        }
        {
        'type':'music',
        'data':[('G',"words words"), ('C7',"words"), ('C7',"more words"), ('F',"and done")],
        },
        {
        'type':'bar',
        'style':'|:',
        'repeat':"1. 3.",
        }
        {
        'type':'directive',
        'directive':'soc',
        'data':''
        },
        ]
    """
    def __init__(self,filename):
        self.filename = filename
        #self.chordpro_re = re.compile(r"(\[.+?\])|(( *:*\|:*)(\(.+?\))* *)")
        self.chordpro_re = re.compile(r"(\[.+?\])|(( *:*\|:*)(\(.+?\))* *)|(<|>)")
        try:
            self.file = file(filename,'r')
        except:
            raise "Can't open file %s" % filename
        self.filecontents = self.file.readlines()
        self.file.close()
        #
        self.initilize_vars()
        self.parse()
        #
    def use_sharps(self,val=1):
        self.use_sharps = val
    def initilize_vars(self):
        self.title=""
        self.credits=""
        self.copyright=""
        self.subtitles = []
        self.chordsused = []
        self.measures = []
        self.use_sharps = 1
        self.key = ""
        self.order = ""
        self.barspresent = 0
        self.tab = 0
        self.into_music = 0
        self.config = []
    def _directive_measure(self,directive,data=None):
        self.measures.append({'type':'directive', 'directive':directive, 'data':data})
    def _music_measure(self, data):
        self.measures.append({'type':'music', 'data':data})
    def _chordgroup(self, value):
        self.measures.append({'type':'chordgroup', 'value':value})
    def _bar(self, style, repeat=None):
        if repeat:
            repeat = repeat[1:-1]
        self.measures.append({'type':'bar', 'style':style, 'repeat':repeat})
        self.barspresent = 1
    def parse(self):
        for line in self.filecontents:
            line = line.strip()
            if not line:
                #empty line
                if self.into_music:
                    self._directive_measure("blank")
            elif line[0] == '{':
                self.process_directive(line)
            elif line[0] == '#':
                # The current line is a comment, ignore it.
                pass
            else:
                self.into_music = 1
                if self.tab:
                    self._music_measure(line)
                    continue
                current_position = 0
                data = []
                chord = ""
                for x in self.chordpro_re.finditer(line):
                    start, end = x.span()
                    matches = x.groups()
                    if start:
                        t = line[current_position:start]
                        if t or chord:
                            data.append((chord, t))
                    if matches[0]: #chord
                        chord = matches[0][1:-1]
                    elif matches[1]: #bar
                        if data: # i.e. not empty
                            self._music_measure(data)
                            data = []
                            chord = ""
                        #print matches[2].strip(),matches[3]
                        self._bar(matches[2].strip(),matches[3]) #args: '|:', '(1. 3.)'
                    elif matches[4]: #chord grouper
                        self._chordgroup(matches[4]):
                    current_position = end
                if chord or line[current_position:]:
                    data.append((chord, line[current_position:]))
                if data:
                    self._music_measure(data)
                self._directive_measure("\n")
        #print self.measures
    def process_directive(self,line):
        line=line[1:-1]
        colon_loc=line.find(':')
        if colon_loc != -1:
            command = line[:colon_loc].strip()
            value = line[colon_loc+1:].strip()
            if command in ['t','title']:
                self.title = value
            elif command in ['st','subtitle']:
                self.subtitles.append(value)
            elif command == 'timing':
                self._directive_measure("timing",data=value)
            elif command == 'credits':
                self.credits = value
            elif command == 'copyright':
                self.copyright = value
            elif command == 'order':
                self.order = value
            elif command == 'set':
                var, val = [x.strip() for x in value.split("=")]
                self.config.append((var, val))
            elif command == 'key':
                self.key = value
            elif command in ['c','comment']:
                self._directive_measure("c",data=value)
            elif command in ['soblk','start_of_block']:
                self._directive_measure("soblk",data=value)
            elif command == 'define':
                pass #FIXME
        else:
            line=line.strip()
            if line in ['soc','start_of_chorus']:
                self._directive_measure("soc")
            elif line in ['eoc','end_of_chorus']:
                self._directive_measure("eoc")
            elif line in ['sot','start_of_tab']:
                self._directive_measure("sot")
                self.tab = 1
            elif line in ['eot','end_of_tab']:
                self.tab = 0
                self._directive_measure("eot")
            elif line in ['sob','start_of_bridge']:
                self._directive_measure("sob")
            elif line in ['eob','end_of_bridge']:
                self._directive_measure("eob")
            elif line in ['eoblk','end_of_block']:
                self._directive_measure("eoblk")
    def transpose(self,transval=1,toggle=None):
        new_measures = []
        for m in self.measures:
            if m['type'] == 'music':
                new_data = []
                for chordname, text in m['data']:
                    c = chord.Chord(chordname)
                    if not self.use_sharps:
                        c.use_flats()
                    c.transpose(transval)
                    chordname = c.name
                    new_data.append((chordname,text))
                m['data'] = new_data
            new_measures.append(m)
        self.measures = new_measures
        if self.key:
            c = chord.Chord(self.key)
            c.transpose(transval)
            self.key = c.name


class ChordPro2PDF:
    def __init__(self, pdf_filename='untitled.pdf'):
        self.config = config
        #
        self.c = canvas.Canvas(pdf_filename,
                        pagesize=(self.config.paper.width,self.config.paper.height))
        self.songs_added = []
    def save_config(self):
        self.config_saved = copy.deepcopy(self.config)
    def restore_config(self):
        self.config = copy.deepcopy(self.config_saved)
    def draw_page_number(self):
        self.c.saveState()
        self.c.setFont(self.config.fonts.page_num_face, self.config.fonts.page_num_size)
        self.c.drawCentredString(self.config.paper.width/2.0,
                self.config.paper.footer, "%s" % self.c.getPageNumber())
        self.c.restoreState()
    def add_alpha_index(self):
        self.add_index(alphabetize=1)
    def add_index(self, alphabetize=0):
        self.c.setFont(self.config.fonts.title_face, self.config.fonts.title_size)
        self.c.drawCentredString(self.config.paper.width/2.0,
                self.config.paper.height-self.config.paper.top_margin, "Index of Songs")
        self.draw_page_number()
        #
        self.c.setFont(self.config.fonts.index_face, self.config.fonts.index_size)
        y_loc = self.config.paper.height - self.config.paper.top_margin*2.0
        songlist = self.songs_added[:]
        if alphabetize:
            songlist.sort()
        for name, page in songlist:
            if y_loc < self.config.paper.bottom_margin:
                self.next_page()
                y_loc = self.config.paper.height - self.config.paper.top_margin
                self.draw_page_number()
            x = self.config.paper.left_margin*1.5
            self.c.drawString(self.config.paper.left_margin*1.5, y_loc, name)
            self.c.drawRightString(self.config.paper.width-self.config.paper.right_margin*1.5, y_loc, str(page))
            self.c.linkAbsolute(str(page), str(page),
                    (x, y_loc, x+self.c.stringWidth(name,
                    self.config.fonts.index_face,
                    self.config.fonts.lyrics_size), y_loc+ self.config.fonts.index_size*1.2),
                    Border='[0 0 0]')
            #self.c.addOutlineEntry(name,
            #        str(page), 0, 0)
            y_loc = y_loc - self.config.fonts.index_size*1.2
    def add_song(self, fn, config_overrides=None):
        n , ext = os.path.splitext(os.path.basename(fn))
        song = SongRenderer(canvas=self.c, filename=fn,
                    parent=self, config=self.config)
        if config_overrides:
            for var, val in config_overrides:
                song.config.set_value(var, val)
        # Transpose
        single_song = 1
        if isinstance(self.config.transpose, tuple): # tuple of values
            transpose_seq = self.config.transpose
            single_song = 0
        else: # single value, make it a tuple
            transpose_seq = (self.config.transpose,)
        if isinstance(self.config.capo, tuple): # tuple of values
            capo_seq = self.config.capo
            single_song = 0
        else: # single value, make it a tuple
            capo_seq = (self.config.capo,)
        if not single_song:
            try:
                multsongtitle = "%s (%s)" % (song.song.title,song.song.subtitles[0])
            except:
                multsongtitle = song.song.title
            bm = "".join([multsongtitle,str(self.c.getPageNumber())])
            self.c.bookmarkPage(bm)
            self.c.addOutlineEntry(multsongtitle, bm, level=0, closed=self.config.outline_closed)
        for t in transpose_seq:
            for c in capo_seq:
                if c == song.song.key: # same, don't do anything
                    c = 0
                pagenum = self.c.getPageNumber()
                if t:
                    song.transpose(t)
                song.set_capo(c)
                song.draw()
                if single_song:
                    if song.song.subtitles:
                        linkname = "".join([song.song.title, " (", song.song.subtitles[0], ")"])
                    else:
                        linkname = song.song.title
                    if song.song.key:
                        linkname = "".join([linkname, " - in ", song.song.key])
                        if c:
                            linkname = "".join([linkname, " - capo ", str(song.capo), " into ", song.capokey])
                    else:
                        if c:
                            linkname = "".join([linkname, " - capo ", str(song.capo)])
                    level = 0
                    closed = 0
                else:
                    if song.song.key:
                        if c:
                            linkname = "in %s, capo %d into %s" % (song.song.key, song.capo, song.capokey)
                        else:
                            linkname = "in %s" % (song.song.key)
                    else:
                        if c:
                            linkname = "transposed %s intervals, capo %d" % (song.intervals_transposed, song.capo)
                        else:
                            linkname = "transposed %s intervals" % (song.intervals_transposed,)
                    level = 1
                    closed = 0
                song.clear_capo()
                if t:
                    song.untranspose()
                if single_song:
                    self.songs_added.append((linkname,pagenum))
                else:
                    self.songs_added.append(("".join([multsongtitle,' - ',linkname]),pagenum))
                self.c.addOutlineEntry(linkname, str(pagenum), level=level, closed=closed)
                self.c.showPage()
    def add_songs(self, filenames):
        """Expects a sequence"""
        for fn in filenames:
            self.add_song(fn)
    def next_page(self):
        self.c.showPage()
    def save(self):
        # add index
        if self.config.index == 1:
            self.add_alpha_index()
        elif self.config.index == 2:
            if len(self.songs_added) > 1:
                self.add_alpha_index()
        elif self.config.index == 3:
            self.add_index()
        elif self.config.index == 4:
            if len(self.songs_added) > 1:
                self.add_index()
        # save file
        try:
            self.c.save()
        except IOError:
            text = "Cannot write the PDF file. " \
                "The file may be open \nin another program or " \
                "it may be read-only.\nClose the open file or fix the permissions\nand try again."
            raise Error, text

class SongRenderer:
    def __init__(self, canvas, parent, config, filename=None, fileobj=None):
        """
        The vertical spacing is tracked with self.y_loc and
        advanced with self.update_y_loc(amount).

        For each item, the vertical space needed is calculated,
        self.update_y_loc is called (advancing the page if necessary),
        and then the item is drawn by adding the right amount of
        spacing back to the current self.y_loc.
        """
        self.c = canvas
        self.filename = filename
        if filename:
            self.song = ChordProPlusFile(filename)
        elif fileobj:
            self.song = fileobj
        else:
            raise "Must give filename or file object."
        self.config = config
        for var, val in self.song.config:
            self.config.set_value(var, val)
        #
        self.parent = parent
        self.intervals_transposed = 0
        self.clear_capo()
        # vars
        self.space_after_title = 16
        self.space_after_subtitle = 14
        self.indent = 30
        self.repeatbracket = 0
        self.bar_drawn_last = 0
        self.line_spacing = self.config.fonts.lyrics_size*0.4
        self.lyrics_spacing = self.config.fonts.lyrics_size*1.1
        self.chords_spacing = self.config.fonts.chords_size*1.1
        self.blockid_spacing = self.config.fonts.blockid_size*1.2
        self.comments_spacing = self.config.fonts.comments_size*1.1
        self.repeat_spacing = self.config.fonts.repeat_size*1.1
        self.paper_center = self.config.paper.width/2.0
        self.paper_rightedge = self.config.paper.width - self.config.paper.right_margin
    def set_capo(self, value):
        if isinstance(value, int):
            self.capo = value # num
            if self.song.key:
                c = chord.Chord(self.song.key)
                c.transpose(self.capo)
                self.capokey = c.name
            else:
                self.capokey = ''
        else: # must be a key, e.g. 'G'
            if not self.song.key:
                raise Error, "A key must be set to capo using key names."
            self.capokey = value # key
            self.capo = 0
            c = chord.Chord(self.song.key)
            while 1:
                self.capo += 1
                c.transpose(1)
                c.use_sharps()
                if c.name == self.capokey:
                    break
                c.use_flats()
                if c.name == self.capokey:
                    break
    def clear_capo(self):
        self.capo = 0
        self.capokey = ''
    def draw(self):
        self.y_loc = self.config.paper.height - self.config.paper.top_margin
        self.draw_footer(self.filename)
        self.c.setLineWidth(1)
        self.c.setFillColor(black)
        self.draw_title()
        self.draw_subtitles()
        self.draw_header_info()
        self.draw_chords_and_lyrics()
    def untranspose(self):
        """Return to song's original key."""
        #print "Trans", transpose_intervals
        self.song.transpose(-self.intervals_transposed)
        self.intervals_transposed = 0
    def transpose(self, transpose_intervals):
        #print "Trans", transpose_intervals
        if isinstance(transpose_intervals, str): # convert from named key to interval
            transpose_intervals = self.key_to_interval(base_key=self.song.key, key=transpose_intervals)
        self.intervals_transposed = self.intervals_transposed + transpose_intervals
        if transpose_intervals: # skip 0
            self.song.transpose(transpose_intervals)
    def key_to_interval(self, base_key, key):
        intervals = 0
        #while (base_key != final_key) and (base_key not in chord.equivalent_keys[final_key]):
        while (base_key != key):
            intervals += 1
            k = chord.Chord(base_key)
            k.transpose(1)
            base_key = k.name
        return intervals
    def draw_title(self):
        self.update_y_loc(self.config.fonts.title_size)
        #self.y_loc = self.y_loc - self.config.fonts.title_size*1.2
        self.c.setFont(self.config.fonts.title_face, self.config.fonts.title_size)
        self.c.drawCentredString(self.paper_center, self.y_loc, self.song.title)
    def draw_subtitles(self):
        self.c.setFont(self.config.fonts.subtitle_face, self.config.fonts.subtitle_size)
        for st in self.song.subtitles:
            self.update_y_loc(self.config.fonts.subtitle_size*1.2)
            self.c.drawCentredString(self.paper_center, self.y_loc, st)
        self.update_y_loc(5)
        self.c.line(self.config.paper.left_margin, self.y_loc,
                self.config.paper.width - self.config.paper.right_margin, self.y_loc)
    def draw_header_info(self):
        self.c.setFont(self.config.fonts.header_face, self.config.fonts.header_size)
        header_spacer = self.config.fonts.header_size*1.2
        if self.song.key or self.song.credits or self.song.copyright or self.song.order:
            if self.song.credits and self.song.copyright:
                lines_used = 2
            elif self.song.key and self.song.order:
                lines_used = 2
            else:
                lines_used = 1
        else:
            lines_used = 0
        self.update_y_loc(header_spacer)
        tmp_y_loc = self.y_loc
        if self.song.key:
            if self.capo:
                self.c.drawString(self.config.paper.left_margin, tmp_y_loc,
                    "Key: %s (capo %s to hear %s)" % (self.song.key, self.capo, self.capokey))
            else:
                self.c.drawString(self.config.paper.left_margin, tmp_y_loc, "Key: %s" % self.song.key)
            tmp_y_loc -= header_spacer
        elif self.capo:
            self.c.drawString(self.config.paper.left_margin, tmp_y_loc,
                    "Capo: %s" % self.capo)
            tmp_y_loc -= header_spacer
        if self.song.order:
            self.c.drawString(self.config.paper.left_margin, tmp_y_loc, "Order: %s" % self.song.order)
        tmp_y_loc = self.y_loc
        if self.song.credits:
            self.c.drawRightString(self.paper_rightedge, tmp_y_loc, self.song.credits)
            tmp_y_loc -= header_spacer
        if self.song.copyright:
            self.c.drawRightString(self.paper_rightedge, tmp_y_loc, self.song.copyright)
        for x in range(lines_used):
            self.update_y_loc(header_spacer)
    def draw_chords_and_lyrics(self):
        # set some flags
        tab = 0
        if self.song.barspresent and not self.config.chordpro_mode:
            processbars = self.song.barspresent
        else:
            processbars = 0
        if processbars:
            add_first_barline = 1
        else:
            add_first_barline = 0
        # set initial variables
        self.repeat_circle_radius = 1.2
        self.pre_padding = 8
        self.post_padding = 8
        minimum_beat_width = self.c.stringWidth("GG", self.config.fonts.chords_face, self.config.fonts.chords_size)
        bar_width = self.c.stringWidth("|", self.config.fonts.chords_face, self.config.fonts.chords_size)
        space_width = self.c.stringWidth(" ", self.config.fonts.lyrics_face, self.config.fonts.lyrics_size)
        repeatbar_width = self.c.stringWidth("|:", self.config.fonts.chords_face, self.config.fonts.chords_size)
        if self.capo:
            #minimum_line_height = (self.chords_spacing*2 + self.lyrics_spacing)
            #maximum_line_height = (self.chords_spacing*2 + self.lyrics_spacing + self.repeat_spacing)
            minimum_line_height = (self.config.fonts.chords_size*2 + self.lyrics_spacing)
            maximum_line_height = (self.config.fonts.chords_size*2 + self.lyrics_spacing + self.repeat_spacing)
            self.repeat_bracket_ymin = self.chords_spacing*2 + self.lyrics_spacing
            self.repeat_bracket_ymax = self.chords_spacing*2 + self.lyrics_spacing + self.repeat_spacing
        else:
            #minimum_line_height = (self.chords_spacing + self.lyrics_spacing)
            #maximum_line_height = (self.chords_spacing + self.lyrics_spacing + self.repeat_spacing)
            minimum_line_height = (self.config.fonts.chords_size + self.lyrics_spacing)
            maximum_line_height = (self.config.fonts.chords_size + self.lyrics_spacing + self.repeat_spacing)
            self.repeat_bracket_ymin = self.chords_spacing + self.lyrics_spacing
            self.repeat_bracket_ymax = self.chords_spacing + self.lyrics_spacing + self.repeat_spacing
        maximum_line_width = self.config.paper.width - self.config.paper.left_margin - self.config.paper.right_margin
        minimum_x = self.config.paper.left_margin
        current_x = minimum_x # this is the current x location on the entire page canvas
        # create first Drawing, this is a drawing of one line at a time.
        d = Drawing(maximum_line_width, maximum_line_height)
        self.d_height = minimum_line_height
        d_x_indent = 10
        if processbars:
            d_x = 0 # this is the current x location in the drawing
        else:
            d_x = d_x_indent
        #
        for m in self.song.measures:
            if m['type'] == 'directive':
                directive = m['directive']
                if directive == 'c':  # commment
                    self.update_y_loc(self.comments_spacing)
                    self.c.setFont(self.config.fonts.comments_face, self.config.fonts.comments_size)
                    self.c.drawString(current_x, self.y_loc, m['data'])
                elif directive == '\n': # line finished
                    if processbars:
                        add_first_barline = 1
                        if not self.bar_drawn_last:
                            d_x = self.draw_bar("|", "", d, d_x, minimum_line_height)
                    self.update_y_loc(self.d_height + self.line_spacing)
                    renderPDF.draw(d, self.c, current_x, self.y_loc)
                    self.d_height = minimum_line_height
                    if processbars:
                        d_x = 0 # this is the current x location in the drawing
                    else:
                        d_x = d_x_indent
                    d = Drawing(maximum_line_width, maximum_line_height)
                elif directive == 'blank':
                    self.update_y_loc(self.chords_spacing*1.5)
                elif directive == 'soblk':
                    self.update_y_loc(self.blockid_spacing)
                    block_y_start = self.y_loc - self.line_spacing/2
                    self.c.setFont(self.config.fonts.blockid_face, self.config.fonts.blockid_size)
                    self.c.drawString(minimum_x, self.y_loc, m['data'])
                elif directive == 'eoblk':
                    self.draw_block_bracket(current_x, block_y_start)
                elif directive == 'soc':
                    self.update_y_loc(self.blockid_spacing)
                    block_y_start = self.y_loc - self.line_spacing/2
                    self.c.setFont(self.config.fonts.blockid_face, self.config.fonts.blockid_size)
                    self.c.drawString(minimum_x, self.y_loc, "Chorus")
                    current_x = minimum_x + self.indent
                elif directive == 'eoc':
                    self.draw_block_bracket(current_x, block_y_start)
                    current_x = minimum_x
                elif directive == 'sot':
                    self.update_y_loc(self.blockid_spacing)
                    self.c.setFont(self.config.fonts.blockid_face, self.config.fonts.blockid_size)
                    self.c.drawString(minimum_x, self.y_loc, "Tab")
                    tab = 1
                elif directive == 'eot':
                    tab = 0
                elif directive == 'sob':
                    self.update_y_loc(self.blockid_spacing)
                    block_y_start = self.y_loc - self.line_spacing/2
                    self.c.setFont(self.config.fonts.blockid_face, self.config.fonts.blockid_size)
                    self.c.drawString(minimum_x, self.y_loc, "Bridge")
                    current_x = minimum_x + self.indent
                elif directive == 'eob':
                    self.draw_block_bracket(current_x, block_y_start)
                    current_x = minimum_x
                elif directive == 'timing':
                    top, bottom = m['data'].split("/")
                    fs = self.config.fonts.chords_size
                    fn = self.config.fonts.chords_face
                    top_width = self.c.stringWidth(top, fn, fs)
                    bottom_width = self.c.stringWidth(bottom, fn, fs)
                    timing_width = max((top_width, bottom_width))
                    timing_halfwidth = timing_width/2.0
                    timing_y_spacing = 2
                    timing_line_y = fs
                    d.add(String(self.pre_padding+timing_halfwidth,0, bottom, fontSize=fs, fontName=fn, textAnchor='middle'))
                    d.add(Line(self.pre_padding,
                                timing_line_y,
                                self.pre_padding + timing_width,
                                timing_line_y,
                                strokeWidth=1.5))
                    d.add(String(self.pre_padding+timing_halfwidth,
                                timing_line_y + timing_y_spacing,
                                top,
                                fontSize=fs,
                                fontName=fn, textAnchor='middle'))
                    d_x = self.pre_padding + timing_width
                    if not processbars: # need some extra space since the bar won't be present
                        d_x += self.post_padding
            elif m['type'] == 'bar':
                ##d.add(Line(d_x,timing_line_y, timing_width,timing_line_y, strokeWidth=2))
                if processbars:
                    d_x = self.draw_bar(m['style'], m['repeat'], d, d_x, minimum_line_height)
                    add_first_barline = 0
                    self.bar_drawn_last = 1
                else:
                    d_x += space_width
            elif m['type'] == 'music': # Normal lyrics, chords
                if tab:
                    self.update_y_loc(self.config.fonts.tab_size)
                    self.c.setFont(self.config.fonts.tab_face, self.config.fonts.tab_size)
                    self.c.drawString(minimum_x, self.y_loc, m['data'])
                    continue
                self.bar_drawn_last = 0
                if add_first_barline:
                    d_x = self.draw_bar("|", "", d, d_x, minimum_line_height)
                    add_first_barline = 0
                last_chord = None
                for chordname, lyrics in m['data']:
                    chord_length = 0
                    symbol = 0
                    if last_chord == chordname:
                        chordname = "/"
                        symbol = 1
                    elif chordname == '/':
                        symbol = 1
                    else:
                        last_chord = chordname
                    cfn = self.config.fonts.chords_face
                    cfs = self.config.fonts.chords_size
                    if self.capo:
                        capofn = self.config.fonts.capo_face
                        capofs = self.config.fonts.capo_size
                    if chordname:
                        # draw chords
                        if symbol:
                            #cfn = self.config.fonts.slash_face
                            #cfs = self.config.fonts.slash_size
                            chord_width = self.c.stringWidth("G", cfn, cfs)
                            d.add(Line(d_x, self.lyrics_spacing, d_x + chord_width,
                                self.lyrics_spacing + self.config.fonts.chords_size*0.8,
                                strokeWidth=1.5))
                        else:
                            d.add(String(d_x, self.lyrics_spacing, chordname , fontName=cfn, fontSize=cfs))
                            chord_width1 = self.c.stringWidth(chordname, cfn, cfs)
                            if self.capo:
                                c = chord.Chord(chordname)
                                c.transpose(self.capo)
                                chord2 = c.name
                                d.add(String(d_x, self.lyrics_spacing+self.chords_spacing,
                                    chord2 , fontName=capofn, fontSize=capofs))
                                chord_width2 = self.c.stringWidth(chord2, capofn, capofs)
                            else:
                                chord_width2 = 0
                            chord_width = max(chord_width1, chord_width2)
                        ##self.c.drawString(current_x,self.y_loc+self.lyrics_spacing, chord)
                    else:
                        chord_width = 0
                    ##self.c.setFont(self.config.fonts.lyrics_face, self.config.fonts.lyrics_size)
                    # draw lyrics
                    d.add(String(d_x, 0, lyrics,
                                        fontName=self.config.fonts.lyrics_face,
                                        fontSize=self.config.fonts.lyrics_size))
                    ##self.c.drawString(current_x, self.y_loc, lyrics)
                    lyrics_width = self.c.stringWidth(lyrics, self.config.fonts.lyrics_face, self.config.fonts.lyrics_size)
                    if chord_width:
                        d_x = d_x + max(chord_width+space_width, lyrics_width, minimum_beat_width)
                    else:
                        d_x = d_x + lyrics_width
    def draw_block_bracket(self, x, y):
        bottom = self.y_loc-self.line_spacing/2
        bracket_legs = x+3
        self.c.line(x, y, x, bottom)
        self.c.line(x, y, bracket_legs, y)
        self.c.line(x, bottom, bracket_legs, bottom)
    def draw_bar(self, style, repeat, drawing, x, height):
        if self.repeatbracket:
            drawing.add(Line(self.repeatbracket,  self.repeat_bracket_ymax, x,
                 self.repeat_bracket_ymax, strokeWidth=1))
            self.repeatbracket = 0
        repeat_bar_space = 2
        x = self.pre_padding + x 
        bar_width = 1.2
        bar_height = height/2.0
        y_start = height/2.0 # experimental
        if style == "|":
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            repeat_xloc = x
            x += self.post_padding
        elif style == "|:":
            repeat_xloc = x
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            x += repeat_bar_space
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            x += self.repeat_circle_radius*3
            for h in (bar_height/3.0, 2*bar_height/3.0):
                drawing.add(Circle(x, y_start+h, self.repeat_circle_radius,
                                    fillColor=colors.black,
                                    strokeColor=colors.black,
                                    strokeWidth=0.5))
            x += self.post_padding
        elif style == ":|":
            x += self.repeat_circle_radius
            for h in (bar_height/3.0, 2*bar_height/3.0):
                drawing.add(Circle(x, y_start+h, self.repeat_circle_radius,
                                    fillColor=colors.black,
                                    strokeColor=colors.black,
                                    strokeWidth=0.5))
            x += self.repeat_circle_radius*3
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            x += repeat_bar_space
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            repeat_xloc = x
            x += self.post_padding
        elif style == ":|:":
            #x += self.repeat_circle_radius
            for h in (bar_height/3.0, 2*bar_height/3.0):
                drawing.add(Circle(x, y_start+h, self.repeat_circle_radius,
                                    fillColor=colors.black,
                                    strokeColor=colors.black,
                                    strokeWidth=0.5))
            x += self.repeat_circle_radius*3
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            x += repeat_bar_space
            drawing.add(Line(x, y_start, x, height, strokeWidth=bar_width))
            repeat_xloc = x
            x += self.repeat_circle_radius*3
            for h in (height/3.0, 2*height/3.0):
                drawing.add(Circle(x, h, self.repeat_circle_radius,
                                    fillColor=colors.black,
                                    strokeColor=colors.black,
                                    strokeWidth=0.5))
            x += self.post_padding
        if repeat:
            self.repeatbracket = repeat_xloc
            self.d_height = self.repeat_bracket_ymax
            drawing.add(Line(repeat_xloc, self.repeat_bracket_ymin,
                    repeat_xloc, self.repeat_bracket_ymax, strokeWidth=1))
            drawing.add(String(repeat_xloc, self.repeat_bracket_ymin, " "+repeat,
                                        fontName=self.config.fonts.repeat_face,
                                        fontSize=self.config.fonts.repeat_size))
        return x
    def update_y_loc(self, amount):
        self.y_loc = self.y_loc - amount
        #print self.y_loc
        if self.y_loc < self.config.paper.bottom_margin:
            self.c.setFont(self.config.fonts.footer_face, self.config.fonts.footer_size)
            self.c.drawRightString(self.config.paper.width-self.config.paper.right_margin,self.config.paper.footer,"Cont.")
            self.next_page()
            self.c.setFont(self.config.fonts.footer_face, self.config.fonts.footer_size)
            self.c.drawString(self.config.paper.left_margin,self.config.paper.height-self.config.paper.top_margin,"Cont.")
            self.parent.draw_page_number()
            self.y_loc = self.config.paper.height - self.config.paper.top_margin - self.lyrics_spacing - self.chords_spacing*2
    def draw_footer(self, chordpro_filename):
        num = self.c.getPageNumber()
        self.c.saveState()
        self.c.setFont(self.config.fonts.page_num_face, self.config.fonts.page_num_size)
        self.c.drawCentredString(self.config.paper.width/2.0,
                self.config.paper.footer, "%s" % num)
        self.c.setFont(self.config.fonts.footer_face, self.config.fonts.footer_size)
        self.c.drawString(self.config.paper.left_margin,
                self.config.paper.footer, os.path.basename(chordpro_filename))
        self.c.restoreState()
        self.c.bookmarkPage(str(num))
    def next_page(self):
        self.c.showPage()


class Songbook(ChordPro2PDF):
    def __init__(self, sbk, pdf):
        ChordPro2PDF.__init__(self, pdf)
        self.songs = []
        self.pdf = pdf
        f = file(sbk,'r')
        lines = f.readlines()
        f.close()
        for line in lines:
            line = line.strip()
            if line and (not line.startswith("#")):
                if line.startswith("!"): # variables
                    self.config.set_value(*self.parse_variable(line[1:]))
                elif line.startswith("@"): # glob macro
                    for s in glob.glob(line[1:]):
                        self.songs.append((s,()))
                else: # song
                    l = line.split("|")
                    song = l[0].strip()
                    configs = l[1:]
                    config_overrides = []
                    for c in configs:
                        config_overrides.append(self.parse_variable(c))
                    self.songs.append((song,config_overrides))
        self.save_config()
        for song, config_overrides in self.songs:
            #for var, val in config_overrides:
            #    self.config.set_value(var, val)
            self.add_song(song,config_overrides)
            self.restore_config()
    def parse_variable(self, line):
        """line should be: 'variable = value'  """
        var, val = [x.strip() for x in line.split("=")]
        return (var, val)

def process_file(f):
    if not os.access(f, os.R_OK):
        raise Error, "Input file '%s' does not exist or is not readable." % f
    root, ext = os.path.splitext(f)
    if ext == '.sbk': #songbook
        s = Songbook(f, root+'.pdf')
        s.save()
    else:
        p = ChordPro2PDF(root+'.pdf')
        p.add_song(f)
        p.save()

if __name__ == '__main__':
    #usage = "%prog [options] <file>"
    #parser = OptionParser(usage=usage)
    #parser.add_option("-g", "--gui", action='store_true', dest='gui',
    #                            help='Send error messages to a dialog, not the'
    #                            'command line.')
    #options, args = parser.parse_args()
    #if args:
    #    files = args
    #else:
    #    #print __doc__
    #    #sys.exit()
    #    files = ['test.csp'] # testing only
    #if options.gui:
    #    try:
    #        for f in files:
    #            process_file(f)
    #    except Error, error:
    #        errorGUI(error.message)
    #    except:
    #        c,i,t = sys.exc_info()
    #        errorGUI("Unexpected Error:\n\n%s\n\nType: %s" % (str(i),str(c)))
    #else:
    #    # pass in any combination of pro, csp, and sbk files
    try:
        for f in sys.argv[1:]:
            process_file(f)
    except Error, error:
        print "Error:", error.message
