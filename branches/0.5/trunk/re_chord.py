#!/usr/bin/env python
import re, os, sys#, config
#progdir = os.path.dirname(__file__)
if globals().has_key('__file__') and (__name__ == '__main__') :
    progdir = os.path.dirname(__file__)
else:
    progdir = os.path.dirname(os.path.abspath(sys.argv[0]))

instrdir = os.path.join(progdir,"instruments")
preffile = os.path.join(progdir,"chordprefs.cfg")
#config = config.Config(default_configfile)

# default init settings
chord_aliases = {
                "+":"aug",
                "7+":"7aug",
                "o":"dim",
                "o7":"dim7",
                "sus":"sus4",
                "7sus":"7sus4",
                "2":"sus2",
                "add2":"add9",
                "M7":"maj7",
                "6":"maj6",
                }

preferred_chords = {}

def init(config):
    """Configure module
    """
    # preferred chords
    global preferred_chords
    preferred_chords = {}
    if config.chord.use_preferred:
        l = config.chord.preferred.split(",")
        for pair in l:
            c, pc = pair.split(':')
            preferred_chords[c.strip()] = pc.strip()
    # chord aliases


re_text = [
      r"(?P<root>^\w[#b]?)",
      r"(?P<minor>m(?!aj)|min|minor)?",
      r"((M|maj|MAJ)(?P<majN>7|9|11|13))?",
      r"(?P<number>\d+(?!/9))?",
      r"(", #These can be in any order
      r"(?:dim|o)(?P<dim>\d?)",
      r"|",
      r"(?P<sixnine>6/9)",
      r"|",
      r"(?P<aug>aug|\+5|\+(?!\d))",
      r"|",
      r"(?P<sus>sus\d?)",
      r"|",
      r"add(?P<add>\d)",
      r")*",
      r"(/(?P<bass>\w[#b]?)$)?",
      ]

chord_re = re.compile("".join(re_text))
construction_re = re.compile(r"(?P<mod>b|#)?(?P<num>\d+)") #  'b3' or '#5'

#~ equivalent_keys = {
                #~ 'C':['Am'],
                #~ 'G':['Em'],
                #~ 'D':['Bm'],
                #~ 'A':['F#m'],
                #~ 'E':['C#m'],
                #~ 'B':['G#m','Abm','Cb'],
                #~ 'F#':['Gb','D#m','Ebm'],
                #~ 'C#':['Db','A#m','Bbm'],
                #~ 'A#':['Fm'],
                #~ 'Eb':['Cm'],
                #~ 'Bb':['Gm'],
                #~ 'F':['Dm'],
                    #~ }
#~ for k in equivalent_keys.keys():
    #~ for item in equivalent_keys[k]:
        #~ equivalent_keys[item] = equivalent_keys[k][:]+[k]
        #~ equivalent_keys[item].remove(item)

valid_notes = ['C','D','E','F','G','A','B']
chromatic_scale = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
interval_to_scaleindex = { '1':0, '2':2, '3':4, '4':5, '5':7, '6':9,
                            '7':11, '9':2, '11':5, '13':9}
sharp_to_flat = { 'C#':'Db', 'D#':'Eb', 'F#':'Gb', 'G#':'Ab', 'A#':'Bb'}
flat_to_sharp = { 'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
chord_formulas = {
        'minor': {'-':['3'],'+':['b3']},
        '6': {'-':[], '+':['6']},
        '7': {'-':[], '+':['b7']},
        '9': {'-':[], '+':['b7','9']},
        '11': {'-':[], '+':['b7','9','11']},
        '13': {'-':[], '+':['b7','9','11','13']},
        'maj7': {'-':[], '+':['7']},
        'maj9': {'-':[], '+':['7','9']},
        'maj11': {'-':[], '+':['7','9','11']},
        'maj13': {'-':[], '+':['7','9','11','13']},
        'aug': {'-':['5'], '+':['#5']},
        'dim': {'-':['3','5'], '+':['b3','b5']},
        'dim7': {'-':['3','5'], '+':['b3','b5','6']},
        'sus4': {'-':['3'], '+':['4']},
        'sus2': {'-':['3'], '+':['2']},
        '6add9': {'-':[], '+':['6','9']},
        '5': {'-':['3'], '+':[]},
        }
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

class Chord:
    """
    1. If no scale pref is passed in during creation:
       1. If the root is flat, then flat scale is used; same with sharp
       2. Otherwise, assume sharp.
    2. If pref is passed in during creation:
       1. If the root is flat/sharp, it is forced to preferred scale
       2. otherwise, just used preferred scale.
    3. Pref can be changed with use_sharps, use_flats
    """
    def __init__(self, name, sharps=None, flats=None):
        self.name = name
        self.invalid = self.check_for_invalid_chords()
        self.sharps = sharps
        self.flats = flats
        if not self.invalid:
            self.parse_chord_name()
            self.root = self.chord_dict['root']
            self.bass = self.chord_dict['bass']
            self.autoset_scale()
            self.construction = self._calc_chord_construction()
            self.notes = self._calc_chord_notes()
            if sharps:
                self._use_sharps_or_flats(0)
            elif flats:
                self._use_sharps_or_flats(1)
    def check_for_invalid_chords(self):
        if (self.name in ['/','\\','NC','N.C.','nc','n.c.','']) or \
            (self.name[0] not in valid_notes): # allow '' ????
            invalid = 1
        else:
            invalid = 0
        return invalid
    def _transpose_note(self, note, halfsteps=0):
        note_loc = self.scale.index(note)
        note_loc += halfsteps
        if note_loc > 11:
            note_loc = note_loc - 12
        elif note_loc < 0:
            note_loc = note_loc + 12
        return self.scale[note_loc]
    def transpose(self, halfsteps=0):
        if not self.invalid:
            old_root = self.root
            self.root = self._transpose_note(self.root, halfsteps)
            if preferred_chords.has_key(self.root):
                self.root = preferred_chords[self.root]
                self.autoset_scale()
            root_index = self.scale.index(self.root)
            self.scale = self.scale[root_index:] + self.scale[:root_index]
            self.name = self.name.replace(old_root,self.root)
            if self.bass:
                old_bass = self.bass
                self.bass = self._transpose_note(self.bass, halfsteps)
                self.name = self.name.replace("/"+old_bass,"/"+self.bass)
            self.notes = self._calc_chord_notes()
    def use_flats(self):
        self._use_sharps_or_flats(1)
        self.sharps = 0
        self.flats = 1
    def use_sharps(self):
        self._use_sharps_or_flats(0)
        self.sharps = 1
        self.flats = 0
    def _use_sharps_or_flats(self,use_flats):
        if not self.invalid:
            old_root = self.root
            self.scale = self.normalize_notes(self.scale, use_flats)
            self.root = self.normalize_notes([self.root], use_flats)[0]
            self.bass = self.normalize_notes([self.bass], use_flats)[0]
            self.notes = self._calc_chord_notes()
            self.name = self.name.replace(old_root,self.root)
    def autoset_scale(self):
        """The root sign always overrides use_flats
        Use sharp scale unless the root is a flat.
        """
        use_flats = 0
        if len(self.root) > 1:
            if self.root[-1] == 'b':
                use_flats = 1
            else:
                use_flats = 0
        if use_flats:
            root_index = chromatic_scale.index(flat_to_sharp[self.root])
        else:
            root_index = chromatic_scale.index(self.root)
        scale = chromatic_scale[root_index:] + chromatic_scale[:root_index]
        self.scale = self.normalize_notes(scale, use_flats)
        self.root = self.scale[0]
    def parse_chord_name(self):
        modifiers = chord_re.search(self.name)
        self.chord_dict = modifiers.groupdict()
    def get_note_by_interval(self, interval):
        """Used to get intervals in scale.
        To get a major chord, ask for 1, 3, and 5.
        """
        offset = 0
        if interval[0] == 'b':
            offset = -1
            interval = interval[1:]
        elif interval[0] == '#':
            offset = 1
            interval = interval[1:]
        index = interval_to_scaleindex[interval]
        return self.scale[index+offset]
    def normalize_notes(self, notelist, use_flats=0):
        if use_flats:
           conversion_dict = sharp_to_flat
        else:
            conversion_dict = flat_to_sharp
        new_notelist = []
        for note in notelist:
            if conversion_dict.has_key(note):
                note = conversion_dict[note]
            new_notelist.append(note)
        return new_notelist
    def _calc_chord_notes(self):
        notes = []
        for interval in self.construction:
            notes.append(self.get_note_by_interval(interval))
        return notes
    def get_chord_notes(self):
        return self.notes
    def modify_chord_construction(self, construction, mod_dict):
        for item in mod_dict['-']:
            construction.remove(item)
        for item in mod_dict['+']:
            construction.append(item)
        #re-sort
        pairs = []
        for item in construction:
            r = construction_re.search(item)
            n = r.group('num')
            m = r.group('mod')
            if not m:
                m = ''
            pairs.append((int(n),m))
        pairs.sort()
        construction = [y+str(x) for x,y in pairs]
        return construction
    def _calc_chord_construction(self):
        """takes chord dict that had already been parsed"""
        c = ['1','3','5'] #start with major chord
        if self.chord_dict['minor']:
            c = self.modify_chord_construction(c, chord_formulas['minor'])
        if self.chord_dict['number']:
            n = self.chord_dict['number']
            if n in ['2','4']:
                c = self.modify_chord_construction(c,
                    chord_formulas['sus%s' % n])
            else:
                c = self.modify_chord_construction(c,
                    chord_formulas['%s' % n])
        if self.chord_dict['majN']:
            c = self.modify_chord_construction(c,
                chord_formulas['maj%s' % self.chord_dict['majN']])
        if self.chord_dict['dim'] != None:
            c = self.modify_chord_construction(c,
                    chord_formulas['dim%s' % self.chord_dict['dim']])
        if self.chord_dict['sus'] != None:
            if len(self.chord_dict['sus']) > 3:
                c = self.modify_chord_construction(c,
                    chord_formulas[self.chord_dict['sus']])
            else:
                c = self.modify_chord_construction(c,
                    chord_formulas['sus4'])
        if self.chord_dict['aug']:
            c = self.modify_chord_construction(c, chord_formulas['aug'])
        if self.chord_dict['add']:
            c = self.modify_chord_construction(c,
                {'-':[],'+':[self.chord_dict['add']]} )
        if self.chord_dict['sixnine']:
            c = self.modify_chord_construction(c, chord_formulas['6add9'])
        return c
    def get_chord_construction(self):
        return self.construction

class Voicings(Chord):
    def __init__(self, chordname, tuning=['E', 'A', 'D', 'G', 'B', 'E'],
            frets=16, fingers=4, reach=3, bass_low=0, skippable_bass=2,
            include=[0,1,-1], sharps=None, flats=None):
        """
        'fingers' limits fingered notes, but bars are allowed
        'bass_low' requires the lowest note to be the bass of the chord
        'no_muted' refers to strings in the middle, not the out side strings

        'include' ensures certain notes are played.  0 is the root. -1 is last item.
        """
        Chord.__init__(self,chordname, sharps=sharps, flats=flats)
        self.frets = frets
        self.fingers = fingers
        self.reach = reach
        self.skippable_bass_strings = skippable_bass
        self.tuning = tuning
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
                note = self.next_note(note)
        return note
    def next_note(self, note):
        if self.sharps:
            return next_sharp_note[note]
        elif self.flats:
            return next_flat_note[note]
        else:
            return next_sharp_note[note]
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
            #bass_note = self.get_note_from_fingering(bassfret,v.index(bassfret))
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
                s = self.next_note(s)
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
            t = self.next_note(t)
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
        chordlist = ['C13']
    for c in chordlist:
        C = Chord(c)
        print c
        print "  Const:", ",".join(C.get_chord_construction())
        print "  Notes:", ",".join(C.get_chord_notes())
        print "  Transposed up 2 steps:"
        C.transpose(2)
        print "  Name:", C.name
        print "  Const:", ",".join(C.get_chord_construction())
        print "  Notes:", ",".join(C.get_chord_notes())
        #raw_input("Done.")
