#!/usr/bin/env python
"""
Chordshop
Copyright (C) 2004-2006 Blake T. Garretson

Email: blakeg@freeshell.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
USA.

"""
VERSION = "0.5"
import cs2pdf, sys, re, os, glob, base64, cStringIO, zlib
chord = cs2pdf.chord
config = cs2pdf.config

#from optparse import OptionParser, OptionGroup
import wx
import wx.stc
import wx.lib.rcsizer as rcs
import wx.lib.colourdb
import wx.html
import images

if wx.Platform == '__WXMSW__':
    face1 = 'Arial'
    face2 = 'Times New Roman'
    face3 = 'Courier New'
    #face3 = 'Lucida Console'
    pb = 10
else:
    face1 = 'Helvetica'
    face2 = 'Times'
    face3 = 'Courier'
    pb = 10

#progdir = os.path.dirname(__file__)
if globals().has_key('__file__') :
    if __name__ == '__main__':
        progdir = os.path.dirname(__file__)
    else:
        progdir = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    progdir = os.path.dirname(os.path.abspath(sys.argv[0]))

instrdir = os.path.join(progdir,"instruments")

def get_icon(name):
    #return wx.Image(iconpath(name+".png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
    data = base64.decodestring(images.catalog[name])
    stream = cStringIO.StringIO(data)
    bmp = wx.BitmapFromImage( wx.ImageFromStream( stream ))
    return bmp

class WID:
    open = wx.NewId()
    save = wx.NewId()
    exit = wx.NewId()
    about = wx.NewId()
    help = wx.NewId()

class conf:
    program_str = "Chordshop"
    version_str = VERSION
    title_str = " ".join([program_str,version_str])
    default_instrument = config.instrument
    sharp_scale = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    flat_scale = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
    interval_scale = ['1', 'b9', '2/9', 'b3', '3', '4/11', 'b5', '5', '#5', '6/13', 'b7', '7']
    interval_to_scaleindex = { '1':0, '2':2, '3':4, '4':5, '5':7, '6':9,
                            '7':11, '9':2, '11':5, '13':9}
    colors = {0:'dot-yellow', 1:'dot-cyan', 2:'dot-green', 3:'dot-ltblue', 4:'dot-orange', 5:'dot-pur', 6:'dot-pink'}

def get_scale(startingnote, sharp, length):
    if sharp:
        scale = conf.sharp_scale*4
    else:
        scale = conf.flat_scale*4
    i = scale.index(startingnote)
    scale = scale[i:]
    scale = scale[:length]
    return scale

def get_interval_scale(root, startingnote, sharp, length):
    iscale = conf.interval_scale*3
    scale = get_scale(root, sharp, 100)
    i = scale.index(startingnote)
    iscale = iscale[i:]
    iscale = iscale[:length]
    return iscale


class FingerboardCanvas(wx.Window):
    def __init__(self, parent, width=730, height=200):
        wx.Window.__init__(self, parent, -1, wx.DefaultPosition, (width, height),
                wx.SIMPLE_BORDER )
        self.parent = parent
        self.height = height
        self.width = width
        self.SetBackgroundColour(wx.WHITE)
        # hardcoded variables
        self.frets = 16
        self.fret_spacing = 40
        self.string_spacing = 26
        self.string_linewidth = 2
        self.fret_linewidth = 5
        self.nut_linewidth = 7
        self.neck_buffer = 10 # space outside of strings on neck
        self.fingercircle_radius = 12
        self.fingercircle_bitmapleftoffset = 2
        self.fingercircle_bitmapradius = 15
        self.fingercircle_bitmaprightoffset = self.fingercircle_bitmapradius*2-self.fingercircle_radius*2-self.fingercircle_bitmapleftoffset
        # calculated instrument variables
        self.resetInstrument()
        #
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.Bind(wx.EVT_PAINT, self.OnPaint)
    def resetInstrument(self):
        self.instrument = self.parent.instrument
        self.neck_width = (self.instrument.strings-1)*self.string_spacing + self.neck_buffer*2
        self.margin_top = (self.height - self.neck_width - self.string_linewidth*self.instrument.strings)/2.0
        self.string_locs = []
        for x in range(self.instrument.strings):
            self.string_locs.append((self.margin_top + self.neck_buffer) + x*self.string_spacing)
        self.fretboard_length = self.frets*self.fret_spacing
        self.margin_left = ((self.width - self.fretboard_length)/2.0)
                            #- self.nut_linewidth - self.fret_linewidth*self.frets
        self.fret_locs = []
        for x in range(1,self.frets+1):
            self.fret_locs.append(self.margin_left + self.fret_spacing*x)
        self._margin_bottom = self.margin_top + self.neck_width
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        #dc = wx.MemoryDC()
        self.PrepareDC(dc)
        self.DoDrawing(dc)
        #return dc
    def draw_fingering(self, dc):
        # Get info from parent
        show_numbers = self.parent.show_numbers
        show_sharps = self.parent.show_sharps
        show_chordnotes = self.parent.show_chordnotes
        chord_notes = self.parent.chord_notes
        chord_construction = self.parent.chord_construction
        #
        string = 0
        for openstring, sloc in zip(self.instrument.tuning[::-1], self.string_locs):
            scale = get_scale(openstring, show_sharps, self.frets+1)
            iscale = get_interval_scale(chord_notes[0], openstring, show_sharps, self.frets+1)
            current_fret = 0
            for note, interval, floc in zip(scale, iscale, [self.margin_left]+self.fret_locs):
                if show_numbers:
                    ilist = interval.split('/')
                    text = ilist[0]
                    for i in ilist:
                        if i in chord_construction:
                            text = i
                else:
                    text = note
                if self.parent.fingering and (self.parent.fingering[::-1][string] == current_fret):
                    selected = 1
                else:
                    selected = 0
                if note in chord_notes:
                    self.draw_finger_circle(dc, text, floc, sloc, conf.colors[chord_notes.index(note)], selected)
                elif not show_chordnotes:
                    self.draw_finger_circle(dc, text, floc, sloc, 'dot-grey', selected)
                current_fret += 1
            string += 1
    def draw_finger_circle(self, dc, text, xloc, yloc, bgcolor, selected=1):
        if selected:
            bmp = get_icon('dot-red')
        else:
            bmp = get_icon(bgcolor)
        bmp_h = bmp.GetHeight()
        bmp_w = bmp.GetWidth()
        dc.DrawBitmap(bmp, xloc-self.fingercircle_bitmapradius*2,yloc-self.fingercircle_bitmapradius, True)
        w,h = dc.GetTextExtent(text)
        dc.DrawText(text, xloc-self.fingercircle_radius-self.fingercircle_bitmaprightoffset-w/2-1, yloc-h/2-1)
    def draw_fretboard(self, dc):
        dc.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD))
        # draw fretboard background
        dc.SetBrush(wx.Brush("BURLYWOOD4", wx.SOLID))
        dc.SetPen(wx.NullPen)
        dc.DrawRectangle(self.margin_left,self.margin_top,self.fretboard_length,self.neck_width)
        # draw nut
        dc.SetPen(wx.Pen('black', self.nut_linewidth))
        dc.DrawLine(self.margin_left, self.margin_top,
                      self.margin_left, self._margin_bottom)
        # draw frets
        dc.SetPen(wx.Pen('goldenrod3', self.fret_linewidth))
        fret = 1
        for f in self.fret_locs:
            dc.DrawLine(f, self.margin_top,
                          f, self._margin_bottom)
            fretnum = str(fret)
            tw, th = dc.GetTextExtent(fretnum)
            tw = tw/2.0
            dc.DrawText(fretnum, f-tw, self._margin_bottom + th/2.0)
            fret += 1
        # draw strings
        tw, th = dc.GetTextExtent("A")
        th = th/2.0
        dc.SetPen(wx.Pen('black', self.string_linewidth))
        string = 0
        tuning = self.instrument.tuning[::-1]
        for s in self.string_locs:
            right_end = self.margin_left + self.fretboard_length
            dc.DrawLine(self.margin_left, s, right_end, s)
            dc.DrawText(tuning[string], right_end+tw, s-th)
            string += 1
    def DoDrawing(self, dc):
        dc.BeginDrawing()
        self.draw_fretboard(dc)
        self.draw_fingering(dc)
        dc.EndDrawing()

class ChordExplorer(wx.Panel):
    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID)#, style=wx.CLIP_CHILDREN)
        #self.SetBackgroundColour(wx.RED)
        #self.Refresh()
        self.parent = parent
        # Initialize Variables
        self.instrument = chord.Instrument(conf.default_instrument)
        self.current_chord = "C"
        self.show_numbers = True
        self.show_sharps = True
        self.show_chordnotes = True
        self.chord_notes, self.chord_construction = self.get_chord_info()
        self.set_fingering(self.c.get_voicings()[0])
        #
        self.fbc = FingerboardCanvas(self)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add((10,10))
        box.Add(self.fbc, 0, flag=wx.ALIGN_CENTER)
        box.Add((10,10))
        box.Add(self.make_controls(), 0, flag=wx.ALIGN_CENTER)
        self.populateCalculatedFingerings()
        #self.set_fingering(self.fingering_str2list(self.fingercalc_lb.GetStringSelection()))
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Fit()
    def make_controls(self):
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        # COLUMN 1
        column1box = wx.BoxSizer(wx.VERTICAL)
        self.chordbox = wx.StaticBoxSizer( wx.StaticBox(self, -1, "Chord" ), wx.VERTICAL )
        self.chordname_widget = wx.StaticText(self, -1, 
                                    label=self.current_chord)#, style=wx.ALIGN_CENTRE)
        c = chord.Chord(self.current_chord)
        self.notes_widget = wx.StaticText(self, -1, " ".join(c.get_chord_notes()))
        self.formula_widget = wx.StaticText(self, -1, " ".join(c.get_chord_construction()))
        chordfont1 = wx.Font(18, wx.ROMAN , wx.NORMAL, wx.BOLD)
        chordfont2 = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.chordname_widget.SetFont(chordfont1)
        self.notes_widget.SetFont(chordfont2)
        self.formula_widget.SetFont(chordfont2)
        self.chordbox.Add(self.chordname_widget, 1, wx.ADJUST_MINSIZE |wx.ALIGN_CENTER)
        self.chordbox.Add((5,5))
        self.chordbox.Add(self.notes_widget, 0, wx.ADJUST_MINSIZE |wx.ALIGN_CENTER)
        self.chordbox.Add(self.formula_widget, 0, wx.ADJUST_MINSIZE |wx.ALIGN_CENTER)
        # ################
        optionsbox = wx.StaticBoxSizer( wx.StaticBox(self, -1, "Options"), wx.VERTICAL )
        optionsbox.Add((-1,10))
        optionsbox.Add(wx.StaticText(self, -1, "Instrument File:"))
        self.instrument_browser = wx.Choice(self, -1,
            choices = self.getInstrumentList())
        self.instrument_browser.SetStringSelection(self.instrument.name)
        optionsbox.Add(self.instrument_browser)
        self.Bind(wx.EVT_CHOICE, self.ChangeInstrument, self.instrument_browser)
        optionsbox.Add((-1,10))
        #
        optionsbox.Add(wx.StaticText(self, -1, "Show:"))
        optionsbox.Add((-1,5))
        rb_sizer = rcs.RowColSizer()
        rb_info = [ (["Numbers", "Notes"],self.changeRB_NotesNumbers),
                    (["Sharps","Flats"],self.changeRB_SharpsFlats),
                    (["Notes in Chord", "All Notes"],self.changeRB_AllChord),
                    ]
        row = 0
        for names, func in rb_info:
            rbs = self.make_options_radiobuttons(names)
            col = 0
            for rb in rbs:
                rb_sizer.Add(rb, row=row, col=col)
                self.Bind(wx.EVT_RADIOBUTTON, func, rb)
                col += 1
            row += 1
        optionsbox.Add(rb_sizer)
        #
        #
        # COLUMN 2
        chordselectorbox = wx.StaticBoxSizer( wx.StaticBox(self, -1, "Fretboard Chord Highlighting"), wx.HORIZONTAL )
        #
        self.chordroot_rb = wx.RadioBox(
            self, -1, "Root", wx.DefaultPosition, wx.DefaultSize,
            conf.sharp_scale, 1, wx.RA_SPECIFY_COLS | wx.NO_BORDER )
        self.Bind(wx.EVT_RADIOBOX, self.changeChordRoot, self.chordroot_rb)
        chordselectorbox.Add(self.chordroot_rb, 0, wx.EXPAND)
        #
        #~ self.chordtypes = [
            #~ "major",
            #~ "m",
            #~ "7",
            #~ "m7",
            #~ "maj7, M7",
            #~ "add9, add2",
            #~ "sus4, sus",
            #~ "sus2, 2",
            #~ "aug, +",
            #~ "dim, o",
            #~ "dim7, o7",
            #~ "7sus4, 7sus",
            #~ "7sus2",
            #~ "7aug, 7+",
            #~ "5, no3",
            #~ "6, maj6",
            #~ "9",
            #~ "11",
            #~ "13",
            #~ "m9",
            #~ "m11",
            #~ "m13",
            #~ "maj9",
            #~ "maj11",
            #~ "maj13",
            #~ "6/9, 6add9",
            #~ ]
        # ################################
        self.allchords = {}
        d = {}
        for k,v in chord.chord_aliases.items():
            d.setdefault(v,[v]).append(k)
        for x in chord.chord_construction.keys():
            if not x:
                self.allchords['major'] = 'major'
            elif d.has_key(x):
                self.allchords[x] = ", ".join(d[x])
            else:
                self.allchords[x] = x
        self.chordtypes = self.allchords.values()
        self.chordtypes.sort()
        # ################################
        self.chordtype_box = wx.StaticBoxSizer( wx.StaticBox(self, -1, "Type"), wx.VERTICAL )
        self.chordtype_lb = wx.ListBox(self, -1, wx.DefaultPosition, (100,-1),
            self.chordtypes, wx.LB_SINGLE )
        self.chordtype_lb.SetSelection(0)
        self.Bind(wx.EVT_LISTBOX, self.changeChordType, self.chordtype_lb)

        self.chordtype_box.Add((4,4))
        self.chordtype_box.Add(self.chordtype_lb, 1, wx.EXPAND)
        chordselectorbox.Add(self.chordtype_box, 0, wx.EXPAND)

        #
        self.chordbass_rb = wx.RadioBox(
            self, -1, "Bass Note", wx.DefaultPosition, wx.DefaultSize,
            ['None']+conf.sharp_scale, 1, wx.RA_SPECIFY_COLS | wx.NO_BORDER )
        self.Bind(wx.EVT_RADIOBOX, self.changeChordBass, self.chordbass_rb)
        chordselectorbox.Add(self.chordbass_rb, 0, wx.EXPAND)

        # COLUMN 3
        column3box = wx.BoxSizer(wx.VERTICAL)
        voicingsbox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Saved Voicings"), wx.VERTICAL)
        self.voicings_lb = wx.ListBox(self, -1, wx.DefaultPosition, (100,-1),
            [], wx.LB_SINGLE )
        #self.voicings_lb.SetSelection(0)
        self.Bind(wx.EVT_LISTBOX, self.changeChordType, self.voicings_lb)

        voicingsbox.Add((4,4))
        voicingsbox.Add(self.voicings_lb, 1, wx.EXPAND)

        voice_add_b = wx.Button(self, -1, "Add")
        self.Bind(wx.EVT_BUTTON, self.add_voicing, voice_add_b)
        voice_add_b.SetSize(voice_add_b.GetBestSize())
        voicingsbox.Add(voice_add_b, 0, wx.EXPAND)
        #voice_remove_b = wx.Button(self, -1, "Remove")
        #self.Bind(wx.EVT_BUTTON, self.add_voicing, voice_remove_b)
        #voice_remove_b.SetSize(voice_remove_b.GetBestSize())
        #voicingsbox.Add(voice_remove_b, 0, wx.EXPAND)
        #voice_addtosong_b = wx.Button(self, -1, "Add to Song")
        #self.Bind(wx.EVT_BUTTON, self.add_voicing, voice_addtosong_b)
        #voice_addtosong_b.SetSize(voice_addtosong_b.GetBestSize())
        #voicingsbox.Add(voice_addtosong_b, 0, wx.EXPAND)

        fingeroptionsbox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Fingering Options"), wx.VERTICAL)
        fingercalcbox_sizer = rcs.RowColSizer()
        fingercalcbox_sizer.Add(wx.StaticText(self, -1, "Fret Span: "),
            row=0, col=0)
        self.fretspan_ch = wx.Choice(self, -1, wx.DefaultPosition, wx.DefaultSize, choices = ['1','2','3','4','5'])
        self.Bind(wx.EVT_CHOICE, self.set_fretspan, self.fretspan_ch)
        #sc = wx.SpinCtrl(self, -1, "WWW")
        #sc.SetRange(1,5)
        #sc.SetValue(3)
        fingercalcbox_sizer.Add(self.fretspan_ch, row=0,col=1)

        fingeroptionsbox.Add((4,4), 0, wx.EXPAND)
        fingeroptionsbox.Add(fingercalcbox_sizer, 0, wx.EXPAND)
        column3box.Add(voicingsbox, 0, wx.EXPAND)
        column3box.Add(fingeroptionsbox, 0, wx.EXPAND)

        # COLUMN 4
        fingercalcbox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Possible Voicings"), wx.VERTICAL)
        self.fingercalc_lb = wx.ListBox(self, -1, wx.DefaultPosition, (100,-1),
            [], wx.LB_SINGLE )
        #self.voicings_lb.SetSelection(0)
        self.Bind(wx.EVT_LISTBOX, self.changeFingering, self.fingercalc_lb)

        fingercalcbox.Add((4,4))
        fingercalcbox.Add(self.fingercalc_lb, 1, wx.EXPAND)


        # ######
        column1box.Add(self.chordbox, 0, wx.EXPAND)
        column1box.Add(optionsbox, 1, wx.EXPAND)
        hbox.Add(column1box, 1, flag=wx.ALIGN_TOP)
        hbox.Add((10,10))
        hbox.Add(chordselectorbox, 0, flag=wx.ALIGN_TOP)
        hbox.Add((10,10))
        hbox.Add(column3box, 0, flag=wx.ALIGN_TOP|wx.EXPAND)
        hbox.Add((10,10))
        hbox.Add(fingercalcbox, 0, flag=wx.ALIGN_TOP|wx.EXPAND)
        return hbox
    def set_fretspan(self, event):
        pass
    def add_voicing(self, event):
        pass
    def clearModifier(self, event):
        pass
    def set_fingering(self, fingering_list):
        self.fingering = fingering_list
        #print self.fingering
    def fingering_list2str(self, l):
        return " ".join([str(y) for y in l])
    def fingering_str2list(self, s):
        l = []
        for x in s.split():
            try:
                l.append(int(x))
            except:
                l.append(x)
        return l
    def changeFingering(self, event):
        lb = event.GetEventObject()
        self.set_fingering(self.fingering_str2list(lb.GetStringSelection()))
        self.fbc.Refresh()
    def changeModifier(self, event):
        #print dir(event)
        print event.Checked()
        print event.GetEventObject().GetLabel()
    def updateChord(self):
        self.Freeze()
        bassnote = self.chordbass_rb.GetStringSelection()
        if bassnote == "None":
            bassnote = ""
        else:
            bassnote = "/" + bassnote
        chordtype = self.chordtype_lb.GetStringSelection()
        comma_loc = chordtype.find(",")
        if comma_loc != -1:
            chordtype = chordtype[:comma_loc].strip()
        if chordtype == "major":
            chordtype = ''
        chord = self.chordroot_rb.GetStringSelection() + chordtype + bassnote
        self.current_chord = chord
        self.chord_notes, self.chord_construction = self.get_chord_info()
        self.updateChordText()
        self.populateCalculatedFingerings()
        self.Thaw()
    def populateCalculatedFingerings(self):
        v = self.c.get_voicings()
        self.fingercalc_lb.Set([self.fingering_list2str(x) for x in v])
        if v:
            self.fingercalc_lb.SetSelection(0)
            self.set_fingering(self.fingering_str2list(self.fingercalc_lb.GetStringSelection()))
        else:
            self.set_fingering([])
        self.fbc.Refresh()
    def get_chord_info(self):
        #c = chord.Chord(self.current_chord)
        #self.c = chord.Chord(self.current_chord)
        self.c = chord.Voicings(self.current_chord, tuning=self.instrument.tuning)
        if self.show_sharps:
            s = 1
        else:
            s = 0
        return self.c.get_chord_notes(sharp=s, preferred=0), self.c.get_chord_construction()
    def updateChordText(self):
        self.chordname_widget.SetLabel(self.current_chord)
        #self.chordname_widget.
        #self.chordname_widget.Refresh()
        self.notes_widget.SetLabel(" ".join(self.chord_notes))
        self.formula_widget.SetLabel(" ".join(self.chord_construction))
        self.chordbox.CalcMin()
        self.chordbox.RecalcSizes()
        self.fbc.Refresh()
    def changeChordBass(self, event):
        self.updateChord()
    def changeChordRoot(self, event):
        self.updateChord()
    def changeChordType(self, event):
        self.updateChord()
    def populateChordRootLabels(self):
        if self.show_sharps:
            scale = conf.sharp_scale
        else:
            scale = conf.flat_scale
        for x in range(12):
            self.chordroot_rb.SetItemLabel(x,scale[x])
        for x in range(1,13):
            self.chordbass_rb.SetItemLabel(x,scale[x-1])
    def make_options_radiobuttons(self, text_list):
        l = []
        first = 1
        for t in  text_list:
            if first:
                l.append(wx.RadioButton( self, -1, t, style = wx.RB_GROUP ))
                first = 0
            else:
                l.append(wx.RadioButton( self, -1, t ))
        return l
    def changeRB_NotesNumbers(self, event):
        radio_selected = event.GetEventObject()
        if radio_selected.GetLabel() == "Numbers":
            self.show_numbers = True
        else:
            self.show_numbers = False
        self.updateChord()
    def changeRB_SharpsFlats(self, event):
        radio_selected = event.GetEventObject()
        if radio_selected.GetLabel() == "Sharps":
            self.show_sharps = True
        else:
            self.show_sharps = False
        self.populateChordRootLabels()
        self.updateChord()
    def changeRB_AllChord(self, event):
        radio_selected = event.GetEventObject()
        if radio_selected.GetLabel() == "Notes in Chord":
            self.show_chordnotes = True
        else:
            self.show_chordnotes = False
        self.updateChord()
    def getInstrumentList(self):
        a = glob.glob(os.path.join(instrdir,"*.cd"))
        b = [ os.path.splitext(os.path.basename(x))[0] for x in a ]
        return b
    def ChangeInstrument(self, evt):
        self.instrument = chord.Instrument(self.instrument_browser.GetStringSelection())
        self.fbc.resetInstrument()
        self.updateChord()
        self.fbc.Refresh()


class ChordProPlusEditor(wx.Panel):
    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID)
        #self.SetBackgroundColour(wx.Color(wx.LIGHT_GREY))
        #self.Refresh()
        self.parent = parent
        self.currentfile = ""
        self.key_re = re.compile(r"{\s*key\s*:\s*([A-Z][b#]*m*)\s*}")
        self.chordline_re = re.compile(
            r"^(?:\s*(\(*[ABCDEFG][#/\-+a-zA-Z0-9]*\)*)(?=$|\s+))+\s*$")
        self.crd_re = re.compile(r"[ABCDEFG][#/\-+a-zA-Z0-9]*")
        #
        box = wx.BoxSizer(wx.VERTICAL)
        self.editor = TextEditor(self, -1)
        self.editor.SetEOLMode(wx.stc.STC_EOL_LF)
        self.editor.SetUseTabs(False) # tabs are spaces
        if config.editor.showeol:
            self.editor.SetViewEOL(True)
        self.editor.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, "size:%d,face:%s" % (pb, face3))
        self.editor.StyleSetSpec(1, "size:%d,bold,face:%s,fore:#c50000" % (pb, face3))
        self.editor.StyleSetSpec(2, "size:%d,bold,face:%s,fore:#0800a2" % (pb, face3))
        self.editor.StyleSetSpec(3, "size:%d,bold,face:%s,fore:#000000,back:#fff600" % (pb, face3))
        self.editor.StyleSetSpec(4, "size:%d,bold,face:%s,fore:#038103" % (pb, face3))
        self.editor.StyleSetSpec(5, "size:%d,bold,face:%s,fore:#6e0381" % (pb, face3))
        #
        self.makeToolbar()
        box.Add(self.toolbar, 0, wx.EXPAND)
        box.Add(self.editor, 1, wx.EXPAND)
        self.SetAutoLayout(1)
        self.SetSizer(box)
    def makeToolbar(self):
        self.toolbar = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                       wx.TB_HORIZONTAL | wx.TB_NODIVIDER | wx.TB_FLAT )
        self.toolbar.SetToolBitmapSize(wx.Size(24,24))
        i = self.toolbar.AddSimpleTool(-1, get_icon('new'), "New", "Long help for 'New'")
        self.Bind(wx.EVT_TOOL, self.newFile, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('open'), "Open", "Long help for 'Open'")
        self.Bind(wx.EVT_TOOL, self.loadFileDialog, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('save'), "Save", "Long help for 'Save'")
        self.Bind(wx.EVT_TOOL, self.saveFile, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('saveas'), "Save As", "Long help for 'Save As'")
        self.Bind(wx.EVT_TOOL, self.saveFileDialog, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('savepdf'), "Generate PDF", "Generate PDF")
        self.Bind(wx.EVT_TOOL, self.generateSinglePDF, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('down'), "Transpose Down", "Long help for 'Transpose Down'")
        self.Bind(wx.EVT_TOOL, self.transpose_down, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('up'), "Transpose Up", "Long help for 'Transpose Up'")
        self.Bind(wx.EVT_TOOL, self.transpose_up, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('chordpro'), "Crd to Chord Pro", "Convert .crd format to Chord Pro.")
        self.Bind(wx.EVT_TOOL, self.link, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('sharp'), "Use Sharps", "Use all sharps")
        self.Bind(wx.EVT_TOOL, self.use_sharps, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('flat'), "Use Flats", "Use all flats")
        self.Bind(wx.EVT_TOOL, self.use_flats, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('title'), "Title", "Convert line to title")
        self.Bind(wx.EVT_TOOL, self.convert_to_title, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('subtitle'), "Subtitle", "Convert line to subtitle")
        self.Bind(wx.EVT_TOOL, self.convert_to_subtitle, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('comment'), "Comment", "Convert line to comment")
        self.Bind(wx.EVT_TOOL, self.convert_to_comment, i)
        self.markblockID = wx.NewId()
        i = self.toolbar.AddSimpleTool(self.markblockID, get_icon('markblock'), "Mark Block", "Mark selected block as a chorus, bridge, tab, or named block")
        self.Bind(wx.EVT_TOOL, self.convert_to_block, i)
        #self.toolbar.AddControl(wx.Button(self.toolbar, wx.NewId(), "Link"))
        self.toolbar.AddSeparator()
        self.toolbar.Realize()
    def newFile(self, event):
        cont = 1
        if self.editor.modified:
            cont = self.confirmSave()
        if cont:
            self.editor.SetText("")
            self.currentfile = "Untitled.csp"
            self.editor.modified = False
            self.updateTitle()
    def loadFile(self, filename):
        f = open(filename, 'rU')
        self.editor.SetText(f.read().expandtabs())
        f.close()
        self.editor.ConvertEOLs(wx.stc.STC_EOL_LF)
        self.editor.modified = False
        self.currentfile = filename
        self.updateTitle()
    def updateTitle(self):
        self.parent.parent.SetTitle("%s - %s" % (conf.program_str, os.path.basename(self.currentfile)))
    def writeFile(self, filename):
        f = open(filename, 'w')
        f.write(self.editor.GetText())
        f.close()
        self.editor.modified = False
    def saveFile(self, event=None, filename=None):
        if filename:
            self.writeFile(filename)
        else:
            if self.currentfile:
                self.writeFile(self.currentfile)
            else:
                self.saveFileDialog(None)
    def generateSinglePDF(self, event):
        if self.editor.modified:
            dlg = wx.MessageDialog(self, 'The current Chordshop source file needs to be saved first.  Save and continue?',
                  'Save File?', wx.YES_NO | wx.ICON_INFORMATION)
                  #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION)
            returncode = dlg.ShowModal()
            dlg.Destroy()
            if returncode == wx.ID_YES:
                self.saveFile()
            elif returncode == wx.ID_NO:
                return
        root, ext = os.path.splitext(self.currentfile)
        dlg = wx.FileDialog(self, message="Save PDF file as ...", defaultDir=os.getcwd(),
            defaultFile=root+".pdf", wildcard="PDF files (*.pdf)|*.pdf", style=wx.SAVE
            )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path:
                try:
                    p = cs2pdf.ChordPro2PDF(path)
                    p.add_song(self.currentfile)
                    p.save()
                except cs2pdf.Error, error:
                    dlg = wx.MessageDialog(self, error.message,
                          'PDF Generation Error', wx.OK | wx.ICON_ERROR)
                    dlg.ShowModal()
                    dlg.Destroy()
    def saveFileDialog(self, event):
        wildcard = "Chordshop (*.csp)|*.csp|" \
           "Chord Pro (*.pro)|*.pro|" \
           "Chord (*.crd)|*.crd|" \
           "Text (*.txt)|*.txt|" \
           "All files (*.*)|*.*"
        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=os.getcwd(),
            defaultFile=self.currentfile, wildcard=wildcard, style=wx.SAVE
            )
        path = None
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if path:
                self.saveFile(filename=path)
                self.currentfile = path
                self.updateTitle()
    def confirmSave(self, event=None):
        dlg = wx.MessageDialog(self, 'Do you want to save the current file first?',
              'Save File?', wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION)
              #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION)
        returncode = dlg.ShowModal()
        dlg.Destroy()
        if returncode == wx.ID_YES:
            self.saveFileDialog(None)
            return 1
        elif returncode == wx.ID_CANCEL:
            return 0
        else:
            return 1
    def loadFileDialog(self, event):
        cont = 1
        if self.editor.modified:
            cont = self.confirmSave()
        if cont:
            wildcard = "Chordshop (*.csp)|*.csp|" \
               "Chord Pro (*.pro)|*.pro|" \
               "Chord (*.crd)|*.crd|" \
               "Text (*.txt)|*.txt|" \
               "All files (*.*)|*.*"
            dlg = wx.FileDialog(self, message="Open a file", defaultDir=os.getcwd(),
                defaultFile="", wildcard=wildcard, style=wx.OPEN | wx.CHANGE_DIR
                )
            if dlg.ShowModal() == wx.ID_OK:
                paths = dlg.GetPaths()
                if paths:
                    self.loadFile(paths[0])
                    #self.currentfile = paths[0]
    def convert_to_block(self, event):
        tb = event.GetEventObject()
        p = tb.GetToolPos(self.markblockID)
        if not hasattr(self, "popupID1"):
            self.popupID1 = wx.NewId()
            self.popupID2 = wx.NewId()
            self.popupID3 = wx.NewId()
            self.popupID4 = wx.NewId()
            self.Bind(wx.EVT_MENU, self.convert_to_chorus, id=self.popupID1)
            self.Bind(wx.EVT_MENU, self.convert_to_bridge, id=self.popupID2)
            self.Bind(wx.EVT_MENU, self.convert_to_tab, id=self.popupID3)
            self.Bind(wx.EVT_MENU, self.convert_to_namedblock, id=self.popupID4)
        menu = wx.Menu()
        menu.Append(self.popupID1, "Chorus")
        menu.Append(self.popupID2, "Bridge")
        menu.Append(self.popupID3, "Tab")
        menu.Append(self.popupID4, "Named Block")
        self.PopupMenu(menu, (24*p,24))
        menu.Destroy()
        #win = MarkBlockChooser(self.parent.parent)
        #win.CenterOnParent(wx.BOTH)
        #win.Show(True)
    def convert_to_chorus(self, event):
        self._wrap_lines("{soc}\n","\n{eoc}")
    def convert_to_bridge(self, event):
        self._wrap_lines("{sob}\n","\n{eob}")
    def convert_to_tab(self, event):
        self._wrap_lines("{sot}\n","\n{eot}")
    def convert_to_namedblock(self, event):
        self._wrap_lines("{soblk:}\n","\n{eoblk}")
    def convert_to_title(self, event):
        self._wrap_line("{title:", "}")
    def convert_to_subtitle(self, event):
        self._wrap_line("{subtitle:", "}")
    def convert_to_comment(self, event):
        self._wrap_line("{comment:", "}")
    def _wrap_selection(self, pre, post):
        text = self.editor.GetSelectedText()
        self.editor.ReplaceSelection(pre+text+post)
    def _wrap_lines(self, pre, post):
        #GetSelectionStart()
        #GetSelectionEnd()
        #GetLine()
        #GetCurLine
        #GetLineEndPosition(int line);
        #GetSelectedText()
        #GetTextRange(int startPos, int endPos);
        #GetTargetStart()
        #GetTargetEnd();
        #ReplaceTarget
        #GetCurrentLine()
        #ReplaceSelection
        #LineFromPosition
        start_line_num = self.editor.LineFromPosition(self.editor.GetSelectionStart())
        start = self.editor.GetLineEndPosition(start_line_num-1)+1
        end_line_num = self.editor.LineFromPosition(self.editor.GetSelectionEnd())
        end = self.editor.GetLineEndPosition(end_line_num)
        self.editor.SetTargetStart(start)
        self.editor.SetTargetEnd(end)
        text = self.editor.GetTextRange(start,end)
        self.editor.ReplaceTarget(pre+text+post)
    def _wrap_line(self, pre, post):
        line_num = self.editor.GetCurrentLine()
        prev_line_num = line_num - 1
        end = self.editor.GetLineEndPosition(line_num)
        start = self.editor.GetLineEndPosition(prev_line_num)+1
        self.editor.SetTargetStart(start)
        self.editor.SetTargetEnd(end)
        text = self.editor.GetTextRange(start,end)
        self.editor.ReplaceTarget(pre+text+post)
    def transpose_up(self, event):
        self._transpose(1)
    def transpose_down(self, event):
        self._transpose(-1)
    def use_sharps(self, event):
        self._use_sharps_or_flats(1)
    def use_flats(self, event):
        self._use_sharps_or_flats(0)
    def _use_sharps_or_flats(self, usesharps):
        def sub_chord(chordname_match):
            chordname = chordname_match.group()[1:-1]
            c = chord.Chord(chordname)
            if usesharps:
                c.use_sharps()
            else:
                c.use_flats()
            return "[%s]" % c.name
        newstring = self.editor.chord_re.sub(sub_chord,self.editor.GetText())
        self.editor.SetText(newstring)
    def _transpose(self, intervals):
        def tranpose_chord(chordname_match):
            chordname = chordname_match.group()[1:-1]
            c = chord.Chord(chordname)
            c.transpose(intervals)
            return "[%s]" % c.name
        newstring = self.editor.chord_re.sub(tranpose_chord,self.editor.GetText())
        # fix key directive too
        key_re = self.key_re.search(newstring)
        if key_re:
            key = key_re.group(1)
            c = chord.Chord(key)
            c.transpose(intervals)
            key = c.name
            newstring = self.key_re.sub("{key: %s}" % key, newstring)
        self.editor.SetText(newstring)
    def _combine_chords_and_lyrics(self, chords, lyrics):
        """Expects pair of .crd format lines.
        Chords on top, lyrics on bottom.
        Returns combined line in chordpro format
        """
        line = ''
        lastloc = 0
        if len(chords) > len(lyrics):
            extraspaces = len(chords) - len(lyrics)
            lyrics = lyrics + " "*extraspaces
        for m in self.crd_re.finditer(chords):
            x = m.start()
            c = m.group()
            line = line + lyrics[lastloc:x] + '[' + c + ']'
            lastloc = x
        line = line + lyrics[lastloc:]
        return line
    def link(self, event):
        self.editor.ConvertEOLs(wx.stc.STC_EOL_LF)
        lines = self.editor.GetText().split('\n')
        chords_line = None
        newlines = []
        for line in lines:
            m = self.chordline_re.search(line)
            if m: # current line is chords line
                if chords_line != None: # last line was chord too, add the old chords and save the new
                    newlines.append(self._combine_chords_and_lyrics(chords_line, " "))
                chords_line = line
            else: # current line is not chords line
                if chords_line != None: # last line was chords, this one is lyrics
                    newlines.append(self._combine_chords_and_lyrics(chords_line, line))
                    if not line: # a blank line
                        newlines.append("")
                    chords_line = None
                else: # line is probably a directive or blank lines
                    newlines.append(line)
        if chords_line != None: # There are still chords to write
            newlines.append(self._combine_chords_and_lyrics(chords_line, " "))
        self.editor.SetText('\n'.join(newlines))


class TextEditor(wx.stc.StyledTextCtrl):
    def __init__(self, parent, ID):
        wx.stc.StyledTextCtrl.__init__(self, parent, ID)
        self.modified = False
        self.chord_re = re.compile(r"\[.*?\]")
        self.directive_re = re.compile(r"\{.+?\}")
        self.bar_re = re.compile(r":*\|:*")
        self.comment_re = re.compile(r"(^|\n)#.*(?=$|\n)")
        wx.stc.EVT_STC_DO_DROP(self, ID, self.OnDoDrop)
        wx.stc.EVT_STC_DRAG_OVER(self, ID, self.OnDragOver)
        wx.stc.EVT_STC_START_DRAG(self, ID, self.OnStartDrag)
        wx.stc.EVT_STC_CHANGE(self, ID, self.OnChange)
        wx.stc.EVT_STC_STYLENEEDED(self, ID, self.OnStyleNeeded)
        wx.EVT_WINDOW_DESTROY(self, self.OnDestroy)
        #self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        wx.EVT_KEY_DOWN(self, self.OnKeyPress)
    def OnKeyPress(self, event):
        if event.GetKeyCode() == wx.WXK_NUMPAD_ENTER: # catch CR and make them LF
            self.AddText("\n")
        else:
            event.Skip()
    def OnStyleNeeded(self, event):
        #self.StyleClearAll()
        #self.Update()
        self.StartStyling(0, 0xff)
        self.SetStyling(self.GetLength(), 0)
        for regexpr, style in ((self.chord_re,1),(self.directive_re,2),
                                    (self.bar_re,3),(self.comment_re,4)):
            for match in regexpr.finditer(self.GetText()):
                x,y = match.span()
                self.StartStyling(x, 0xff)
                self.SetStyling(y-x, style)
    def OnChange(self, event):
        self.modified = True
    def OnDestroy(self, event):
        # This is how the clipboard contents can be preserved after
        # the app has exited.
        wx.TheClipboard.Flush()
        event.Skip()
    def OnStartDrag(self, event):
        pass
        #print "OnStartDrag: %d, %s\n" % (event.GetDragAllowMove(), event.GetDragText())
    def OnDragOver(self, event):
        pass
        #print "OnDragOver: x,y=(%d, %d)  pos: %d  DragResult: %d\n" % \
        #    (event.GetX(), event.GetY(), event.GetPosition(), event.GetDragResult())
    def OnDoDrop(self, event):
        pass
        #print "OnDoDrop: x,y=(%d, %d)  pos: %d  DragResult: %d\n\ttext: %s\n" \
        #        % (event.GetX(), event.GetY(), event.GetPosition(), event.GetDragResult(),
        #                  event.GetDragText())


class AboutViewer(wx.html.HtmlWindow):
    def __init__(self, parent, ID):
        wx.html.HtmlWindow.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE|wx.SUNKEN_BORDER)
        #self.homefile = os.path.join(progdir, 'docs/about.html')
        #self.LoadPage(self.homefile)
        text = """<html><body><center>
            <br />
            <img src="docs/images/cs_shadow.png" />
            <dev align=right><font size=+3><b><i>%(version)s</i></b></font></div>
            <br />
            Copyright (C) 2004 Blake T. Garretson<br />All Rights Reserved.
            <br />
            <a href="mailto:blakeg@freeshell.org">blakeg@freeshell.org</a> --
            <a href="http://blakeg.freeshell.org">http://blakeg.freeshell.org</a>
            <br /><br />
            Go to <a href="http://chordshop.sourceforge.net">http://chordshop.sourceforge.net</a>
            <br />
            for the latest info and downloads.
            <br /><br />
            <table border="0" cellspacing="20" >
            <tr><td>
            Free use of this software is granted under the terms of the
            GNU General Public License (GPL). See the licenses.html
            documentation file in the distributed package for details.
            </td><td>
            If you are running the binary distribution of Chordshop, then
            additional software has been packaged with Chordshop.
            See licenses.html for the copyrights and licenses of the included
            software packages as well.
            </td>
            </tr>
            </table>
            </center></body></html>""" % {'version':VERSION}
        self.SetPage(text)


class HelpViewer(wx.Panel):
    def __init__(self, parent, ID):
        wx.Panel.__init__(self, parent, ID)
        self.parent = parent
        self.makeToolbar()
        self.html = wx.html.HtmlWindow(self, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE|wx.SUNKEN_BORDER)
        #self.html.SetRelatedStatusBar(0)
        self.homefile = os.path.join(progdir, 'docs/index.html')
        self.html.LoadPage(self.homefile)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.toolbar, 0, wx.EXPAND)
        box.Add(self.html, 1, wx.EXPAND)
        self.SetAutoLayout(1)
        self.SetSizer(box)
    def makeToolbar(self):
        self.toolbar = wx.ToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                       wx.TB_HORIZONTAL | wx.TB_NODIVIDER | wx.TB_FLAT )
        self.toolbar.SetToolBitmapSize(wx.Size(24,24))
        i = self.toolbar.AddSimpleTool(-1, get_icon('home'), "Home", "Go to main index")
        self.Bind(wx.EVT_TOOL, self.home, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('back'), "Back", "Go to previous page")
        self.Bind(wx.EVT_TOOL, self.back, i)
        i = self.toolbar.AddSimpleTool(-1, get_icon('forward'), "Forward", "Go to next page")
        self.Bind(wx.EVT_TOOL, self.forward, i)
        self.toolbar.AddSeparator()
        self.toolbar.Realize()
    def home(self, event):
        self.html.LoadPage(self.homefile)
    def back(self, event):
        self.html.HistoryBack()
    def forward(self, event):
        self.html.HistoryForward()


class Notebook(wx.Notebook):
    def __init__(self, parent, id):
        wx.Notebook.__init__(self, parent, id)
        self.parent = parent

        self.cppeditor = ChordProPlusEditor(self, -1)
        self.AddPage(self.cppeditor, "Song Editor")

        self.options_panel2 = wx.Panel(self, -1)
        self.AddPage(self.options_panel2, "Songbook Editor")

        self.chordexplorer = ChordExplorer(self, -1)
        self.AddPage(self.chordexplorer, "Chord Explorer")

        self.helpviewer = HelpViewer(self, -1)
        self.AddPage(self.helpviewer, "Help Viewer")

        self.aboutviewer = AboutViewer(self, -1)
        self.AddPage(self.aboutviewer, "About")

        self.Fit()
        wx.EVT_NOTEBOOK_PAGE_CHANGED(self, self.GetId(), self.OnPageChanged)
    def OnPageChanged(self, event):
        event.Skip()
        #print "debug 1"

class MainFrame(wx.Frame):
    def __init__(self, parent, ID, title):
        wx.Frame.__init__(self, parent, ID, title,
                         wx.DefaultPosition, wx.Size(760, 600))
        self.frame = self
        self.CreateStatusBar()
        self.SetStatusText("Welcome to Chordshop")
        self.SetMenuBar(self.make_menubar())
        #
        self.chordnotebook = Notebook(self,wx.NewId())
        #
        wx.EVT_CLOSE(self, self.Quit)
        wx.EVT_MENU(self, WID.open, self.Quit)
        wx.EVT_MENU(self, WID.exit, self.Quit)
        self.Fit()        #
    def make_menubar(self):
        menuBar = wx.MenuBar()
        Filemenu = wx.Menu()
        Filemenu.Append(WID.open, "&Open...","Open ChordPro file")
        Filemenu.Append(WID.save, "&Save","Save ChordPro file")
        Filemenu.AppendSeparator()
        Filemenu.Append(WID.exit, "E&xit", "Terminate the program")
        menuBar.Append(Filemenu, "&File")
        #
        #Helpmenu = wx.Menu()
        #Helpmenu.Append(WID.about, "&About",
        #            "About program, author, and copyrights/licensing.")
        #menuBar.Append(Helpmenu, "&About")
        return menuBar
    def Quit(self, event):
        cont = 1
        if self.chordnotebook.cppeditor.editor.modified:
            cont = self.chordnotebook.cppeditor.confirmSave()
        if cont:
            self.Destroy()


class Chordshop(wx.App):
    def OnInit(self):
        #wx.InitAllImageHandlers()
        wx.lib.colourdb.updateColourDB()
        frame = MainFrame(None, -1, conf.title_str)
        self.loadFile = frame.chordnotebook.cppeditor.loadFile
        self.SetTopWindow(frame)
        frame.Fit()
        frame.CenterOnScreen()
        frame.Show()
        return True

if __name__ == '__main__':
    app = Chordshop(0)
    if len(sys.argv) > 1:
        app.loadFile(sys.argv[1])
    app.MainLoop()

