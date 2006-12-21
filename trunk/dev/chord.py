#!/usr/bin/env python
import re, os, sys#, config
#progdir = os.path.dirname(__file__)
if globals().has_key('__file__') and (__name__ == '__main__') :
    progdir = os.path.dirname(__file__)
else:
    progdir = os.path.dirname(os.path.abspath(sys.argv[0]))

instrdir = os.path.join(progdir,"instruments")
preffile = os.path.join(progdir,"chords.cfg")

# Read config file
preferred_chords = {}
switches = {'use_preferred':1}
chord_aliases = {}
chord_construction = {}
def parse_config():
    f = open(preffile)
    section_type = None
    for line in f:
        line = line.strip()
        if line.startswith('['):
            section_type = line
        elif not line:
            pass # blank line
        elif line.startswith('#'):
            pass # comment
        else:
            if section_type == "[switches]":
                var, val = line.split('=')
                switches[var.strip()] = val.strip()
            elif section_type == "[preferred]":
                var, val = line.split(':')
                preferred_chords[var.strip()] = val.strip()
            elif section_type == "[define]":
                names, constr = line.split(':')
                namelist = names.split(',')
                primary = namelist[0]
                aliases = namelist[1:]
                chord_construction[primary] = constr.split()
                for x in aliases:
                    chord_aliases[x] = primary
parse_config()

chord_re = re.compile(r'([ABCDEFG](?:b|#)?)((?:6/9)|(?:[\+\d\w]*))(?:/([ABCDEFG](?:b|#)?$))?')
#note  C   D   E F   G   A    B
#index 0 1 2 3 4 5 6 7 8 9 10 11
#inter 1   2   3 4   5   6    7
#      8   9   1011  12  13
chromatic_scale = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
interval_to_scaleindex = { '1':0, '2':2, '3':4, '4':5, '5':7, '6':9,
                            '7':11, '9':2, '11':5, '13':9}
sharp_to_flat = { 'C#':'Db', 'D#':'Eb', 'F#':'Gb', 'G#':'Ab', 'A#':'Bb'}
flat_to_sharp = { 'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
next_sharp_note = {
            'A':'A#',
            'A#':'B',
            'B':'C',
            'C':'C#',
            'C#':'D',
            'D':'D#',
            'D#':'E',
            'E':'F',
            'F':'F#',
            'F#':'G',
            'G':'G#',
            'G#':'A',
            }
previous_sharp_note = dict([(y,x) for x,y in next_sharp_note.items()])
next_flat_note = {
            'A':'Bb',
            'Bb':'B',
            'B':'C',
            'C':'Db',
            'Db':'D',
            'D':'Eb',
            'Eb':'E',
            'E':'F',
            'F':'Gb',
            'Gb':'G',
            'G':'Ab',
            'Ab':'A',
            }
previous_flat_note = dict([(y,x) for x,y in next_flat_note.items()])

def get_next_note(note, sharp=1):
    if not note:
        return note
    note = flat_to_sharp.get(note, note)
    nextnote = next_sharp_note[note]
    if sharp:
        nextnote = flat_to_sharp.get(nextnote, nextnote)
    else:
        nextnote = sharp_to_flat.get(nextnote, nextnote)
    return nextnote
def get_previous_note(note, sharp=1):
    if not note:
        return note
    note = flat_to_sharp.get(note, note)
    previousnote = previous_sharp_note[note]
    if sharp:
        previousnote = flat_to_sharp.get(previousnote, previousnote)
    else:
        previousnote = sharp_to_flat.get(previousnote, previousnote)
    return previousnote
def get_scale(note, sharp=1):
    if sharp:
        scale = [flat_to_sharp.get(note, note)]
    else:
        scale = [sharp_to_flat.get(note, note)]
    for x in range(11):
        note = get_next_note(note,sharp)
        scale.append(note)
    return scale
def get_note_by_interval(scale, interval):
    if interval[0] in ['b', '#']:
        mod = interval[0]
        interval = interval[1:]
    else:
        mod = None
    index = interval_to_scaleindex[interval]
    if mod == 'b':
        index -= 1
    elif mod == '#':
        index += 1
    return scale[index]

class Error(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class Chord:
    """
    """
    def __init__(self, name):
        self.name = name
        result = chord_re.search(name)
        if result:
            self.root, self.chordtype, self.bass = result.groups()
            self.construction = self.calc_construction()
            self.valid = 1
        else:
            self.valid = 0
    def transpose(self, interval, sharp=1):
        if self.valid:
            if interval > 0:
                function = get_next_note
            elif interval < 0:
                function = get_previous_note
            else:
                return
            for x in range(abs(interval)):
                self.root = function(self.root, sharp)
                self.bass = function(self.bass, sharp)
            if switches['use_preferred']:
                self.root = preferred_chords.get(self.root,self.root)
                self.bass = preferred_chords.get(self.bass,self.bass)
            self.update_name()
    def update_name(self):
        l = [self.root, self.chordtype]
        if self.bass:
            l.append(self.bass)
        self.name = "".join(l)
    def get_primary_chord(self, name):
        return chord_aliases.get(name,name)
    def calc_construction(self):
        name = self.get_primary_chord(self.chordtype)
        if not chord_construction.has_key(name):
            raise Error, "Chord type '%s' is not defined." % name
        return chord_construction[name]
    def get_chord_construction(self):
        if self.valid:
            return self.construction
        else:
            return None
    def get_chord_notes(self, sharp=1, preferred=switches['use_preferred']):
        if self.valid:
            notes = []
            scale = get_scale(self.root, sharp)
            for interval in self.construction:
                n = get_note_by_interval(scale,interval)
                if preferred:
                    n = preferred_chords.get(n, n)
                notes.append(n)
            return notes
        else:
            return None
    def use_sharps(self):
        if self.valid:
            self.root = flat_to_sharp.get(self.root, self.root)
            self.bass = flat_to_sharp.get(self.bass, self.bass)
            self.update_name()
    def use_flats(self):
        if self.valid:
            self.root = sharp_to_flat.get(self.root, self.root)
            self.bass = sharp_to_flat.get(self.bass, self.bass)
            self.update_name()


class Voicings(Chord):
    def __init__(self, chordname, tuning=['E', 'A', 'D', 'G', 'B', 'E'],
            frets=16, fingers=4, reach=3, bass_low=0, skippable_bass=2,
            include=[0,1,-1]):
        """
        'fingers' limits fingered notes, but bars are allowed
        'bass_low' requires the lowest note to be the bass of the chord
        'no_muted' refers to strings in the middle, not the out side strings
        'include' ensures certain notes are played.  0 is the root. -1 is last item.

        For simplicity, all notes are converted to the sharp scale.
        """
        Chord.__init__(self,chordname)
        self.frets = frets
        self.fingers = fingers
        self.reach = reach
        self.skippable_bass_strings = skippable_bass
        self.tuning = [flat_to_sharp.get(x, x) for x in tuning]  # always use sharps
        self.notes = self.get_chord_notes(sharp=1, preferred=0)
        #
        self.calc_fret_to_note()
        self.openstrings = self.get_openstrings(tuning)
        self.allstrings = self.calculate_strings(self.inc_tuning(tuning))
        self.voicings = self.get_all_combinations()
        self.voicings = self.eliminate_unfingerable(self.voicings)
        if bass_low:
            self.voicings = self.ensure_low_bass(self.voicings)
        self.voicings = self.require_note(self.voicings, include)
        self.voicings = self.sort(self.voicings)
    def sort(self, voicings):
        dec = []
        for v in voicings:
            for x in v:
                if isinstance(x, int):
                    dec.append((x,v))
                    break
        dec.sort()
        return [y for x,y in dec]
    def calc_fret_to_note(self):
        self.fret_to_note = {}
        # access hint:  self.fret_to_note[stringnum][fretnum]
        for s in range(len(self.tuning)):
            self.fret_to_note[s] = {}
            note = self.tuning[s]
            for x in range(0,self.frets+1):
                self.fret_to_note[s][x] = note
                note = get_next_note(note, 1)
        return note
    def __repr__(self):
        s = ""
        for v in self.voicings:
            s = s+str(v)+"\n"
        return s
    def get_voicings(self):
        return self.voicings
    def fingering_to_included_notes(self, fingering):
        notes = []
        string = 0
        for item in fingering:
            if item != 'x':
                note = self.fret_to_note[string][item]
                notes.append(note)
            string += 1
        return notes
    def require_note(self, voicings, includes):
        """Note needs to be somewhere in the chord.
        """
        newvoicings = []
        required_notes = [self.notes[Z] for Z in includes]
        for v in voicings:
            notes = self.fingering_to_included_notes(v)
            for required_note in required_notes:
                if required_note not in notes:
                    break
            else:
                newvoicings.append(v)
        return newvoicings
    def ensure_low_bass(self, voicings):
        newvoicings = []
        for v in voicings:
            bassfret = self.get_bass(v)
            bass_note = self.fret_to_note[v.index(bassfret)][bassfret]
            if bass_note == self.notes[0]:
                newvoicings.append(v)
        return newvoicings
    def get_bass(self, alist):
        for x in range(len(self.tuning)):
            if alist[x] == 'x':
                continue
            else:
                return alist[x]
    def eliminate_unfingerable(self, possible_fingerings):
        newfingerings = []
        for f in possible_fingerings:
            low = 1000
            high = 0
            for x in f:
                if x == 'x':
                    continue
                if x < low and x != 0:
                    low = x
                if x > high:
                    high = x
            #
            if (high - low) > (self.reach-1): # can't reach
                #print "Reach Dropping", f
                continue
            #fingers
            start_bar = 0
            bar_possible = 1
            for s in f:
                if start_bar and bar_possible and (s in [0, 'x']):
                    bar_possible = 0
                elif (s == low) and bar_possible: # could be a bar
                    start_bar = 1
            reduced_f = []
            if bar_possible:
                exclude_list = [0, 'x', low]
            else:
                exclude_list = [0, 'x']
            for s in f:
                if s in exclude_list:
                    continue
                else:
                    reduced_f.append(s)
            fingers_used = len(reduced_f)
            if bar_possible:
                fingers_used += 1
            if fingers_used > self.fingers:
                #print "Finger Dropping", f
                continue
            #still here? then add
            newfingerings.append(f)
        return newfingerings
    def get_all_combinations(self):
        results = []
        for firstfret in self.allstrings[0]:
            string_lists = [[firstfret]]
            for s in self.allstrings[1:]:
                sublist = []
                for fret in s:
                    if fret in [0, 'x'] or (abs(fret-firstfret) < self.reach):
                        sublist.append(fret)
                string_lists.append(sublist)
            results.extend(self.permute(string_lists))
        # add skipped bass fingerings
        for x in range(self.skippable_bass_strings):
            firststring = self.allstrings[x+1]
            rest_of_strings = self.allstrings[x+2:]
            for firstfret in firststring:
                string_lists = [['x']]*(x+1)+[[firstfret]]
                for s in rest_of_strings:
                    sublist = []
                    for fret in s:
                        if fret == 0 or (abs(fret-firstfret) <= self.reach):
                            sublist.append(fret)
                    string_lists.append(sublist)
                results.extend(self.permute(string_lists))
        return results
    def calculate_strings(self, tuning):
        strings = []
        string_num = 0
        for s in tuning:
            current_string = []
            for x in range(1,self.frets+1):
                if s in self.notes:
                    current_string.append(x)
                #else:
                #    current_string.append(None)
                s = get_next_note(s, 1)
                #s = self.next_note(s)
            if string_num in self.openstrings:
                current_string.append(0)
            #if string_num < self.skippable_bass_strings:
            #    current_string.append('x')
            strings.append(tuple(current_string))
            string_num += 1
        return strings
    def permute(self, alist):
        if len(alist) < 2:
            return [[z] for z in alist[0]]
        tails = self.permute(alist[1:])
        return [[y] + x for y in alist[0] for x in tails]
    def get_openstrings(self, tuning):
        openstrings = []
        index = 0
        for t in tuning:
            if t in self.notes:
                openstrings.append(index)
            index += 1
        return openstrings
    def inc_tuning(self, tuning):
        newtuning = []
        for t in tuning:
            t = get_next_note(t, 1)
            newtuning.append(t)
        return newtuning

class Instrument:
    def __init__(self, name):
        self.name = name
        f = file(os.path.join(instrdir, name+'.cd'),'r')
        text = f.readlines()
        f.close()
        t, s = text[0].split(':')
        self.tuning = t.strip().split()
        self.strings = len(self.tuning)
        self.special = s.strip()
        self.chords = {}
        for line in text[1:]:
            chord, fingering, comments = line.strip().split(':')
            self.chords.setdefault(chord, []).append((fingering.split(),comments))
        #print self.chords
    def addFingering(self, chord, fingering, comments):
        self.chords.setdefault(chord, []).append((fingering[:],comments))
    def replaceChord(self, chordname, chordlist):
        self.chords[chordname] = chordlist[:]
    def save(self):
        pass
        #FIXME

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        chordlist = sys.argv[1:]
    else:
        chordlist = ['C#sus4/F#', 'Cmaj7']
    for c in chordlist:
        C = Chord(c)
        print c
        print "  Const:", ",".join(C.get_chord_construction())
        print "  Notes:", ",".join(C.get_chord_notes())
        #~ print "  Transposed up 2 steps:"
        #~ C.transpose(2)
        #~ print "  Name:", C.name
        #~ print "  Const:", ",".join(C.get_chord_construction())
        #~ print "  Notes:", ",".join(C.get_chord_notes())
        #~ print "  Transposed down 4 steps:"
        #~ C.transpose(-4)
        #~ print "  Name:", C.name
        #~ print "  Const:", ",".join(C.get_chord_construction())
        #~ print "  Notes:", ",".join(C.get_chord_notes(preferred=0))
        #~ v = Voicings("C")
        #~ print "  Name:", v.name
        #~ print "  Voicings:"
        #~ for  x in v.get_voicings():
            #~ print "    ", x
        #raw_input("Done.")
