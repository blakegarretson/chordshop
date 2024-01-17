#!/usr/bin/env python
import re
import sys

re_text = [
    r"(?P<root>[ABCDEFG][#b]?)",
    r"(?P<minor>m(?!aj)|min|minor)?",
    r"((M|maj|MAJ)(?P<majN>7|9|11|13))?",
    r"(?P<number>\d+(?!/9))?",
    r"(",  # These can be in any order
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
non_chords = ['/', 'NC', r'N\.C\.', 'nc', r'n\.c\.', r'\-', r'\\', r'\b\.\b']
chordline = f"({"".join(re_text)})|" + r'|'.join([fr"{x}" for x in non_chords if x])
bracket_chords = r'\[(.*?)\]'
bracket_chords_re = re.compile(bracket_chords)

chord_re = re.compile("".join(re_text))
construction_re = re.compile(r"(?P<mod>b|#)?(?P<num>\d+)")  # 'b3' or '#5'
chordline_re = re.compile(chordline)

valid_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

class ChromaticScale():
    preferred = ['F#', 'Bb', 'Ab', 'C#', 'Eb']
    def __init__(self, root, preferred=None):
        self._chromatic_scale = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self._trans = {'C#': 'Db', 'D#': 'Eb', 'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb', 'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
        self._chromatic_scale_flats = [self._trans.get(x,x) for x in self._chromatic_scale]
        # major scale
        self._interval_to_scaleindex = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11, 9: 2, 11: 5, 13: 9}
        self._scaleindex_to_interval = {b:a for a,b in reversed(self._interval_to_scaleindex.items())}

        self.root = root
        self.use_preferred_mapping(preferred)       

    def get_notes_by_interval(self, *intervals):
        return [self.scale[self._interval_to_scaleindex[int(interval)]] for interval in intervals]
    
    def get_intervals_by_note(self, *notes):
        return [self._scaleindex_to_interval.get(self.scale.index(self._note(note)), "Not in key") for note in notes]
    
    def _note(self, note, alt_scale=None):
        "Always returns note in the scale. Can provide and alternate scale instead of default"
        scale = alt_scale if alt_scale else self.scale
        if note in scale:
            return note
        else:
            return self._trans[note]
        
    def _pref_note(self, note):
        "Always returns a preferred note in the scale"
        return self._preferred_mapping.get(note,note)

    def _change_scale(self, scale, preferred=False):
        if preferred:
            basescale = [self._pref_note(x) for x in scale]*2
        else:
            basescale = scale*2

        start_of_scale = basescale.index(self._note(self.root, basescale))
        self.scale = basescale[start_of_scale:start_of_scale+12]
        self.root = self._note(self.root)

    def use_preferred_mapping(self, preferred=None):
        if preferred:
            self.preferred = preferred
        self._preferred_mapping = {self._trans[i]:i for i in self.preferred}
        self._change_scale(self._chromatic_scale, preferred=True)

    def use_flats(self):
        self._change_scale(self._chromatic_scale_flats)

    def use_sharps(self):
        self._change_scale(self._chromatic_scale)

    def transpose(self, halfsteps=0):
        self.root = self.scale[halfsteps]
        self.scale = self.scale[halfsteps:]+self.scale[:halfsteps]

chord_formulas = {
    # Assume we start with [1,3,5] notes, and add and subtract accordingly
    'minor': {'-': ['3'], '+': ['b3']},
    '6': {'-': [], '+': ['6']},
    '7': {'-': [], '+': ['b7']},
    '9': {'-': [], '+': ['b7', '9']},
    '11': {'-': [], '+': ['b7', '9', '11']},
    '13': {'-': [], '+': ['b7', '9', '11', '13']},
    'maj7': {'-': [], '+': ['7']},
    'maj9': {'-': [], '+': ['7', '9']},
    'maj11': {'-': [], '+': ['7', '9', '11']},
    'maj13': {'-': [], '+': ['7', '9', '11', '13']},
    'aug': {'-': ['5'], '+': ['#5']},
    'dim': {'-': ['3', '5'], '+': ['b3', 'b5']},
    'dim7': {'-': ['3', '5'], '+': ['b3', 'b5', '6']},
    'sus4': {'-': ['3'], '+': ['4']},
    'sus2': {'-': ['3'], '+': ['2']},
    '6add9': {'-': [], '+': ['6', '9']},
    '5': {'-': ['3'], '+': []},
}
next_sharp_note = {
    'A': 'A#',
    'A#': 'B',
    'B': 'C',
    'C': 'C#',
    'C#': 'D',
    'D': 'D#',
    'D#': 'E',
    'E': 'F',
    'F': 'F#',
    'F#': 'G',
    'G': 'G#',
    'G#': 'A',
}
next_flat_note = {
    'A': 'Bb',
    'Bb': 'B',
    'B': 'C',
    'C': 'Db',
    'Db': 'D',
    'D': 'Eb',
    'Eb': 'E',
    'E': 'F',
    'F': 'Gb',
    'Gb': 'G',
    'G': 'Ab',
    'Ab': 'A',
}


class Chord:
    def __init__(self, name, preferred=None):
        self.name = name
        self.invalid = self._check_for_invalid_chords()
        if not self.invalid:
            self.chord_dict = chord_re.search(self.name).groupdict()
            self.scale = ChromaticScale(self.chord_dict['root'], preferred)
            self.root = self.scale.root
            self.bass = self.chord_dict['bass']
            self._parse_chord()

    def get_root(self):
        return self.root
    
    def get_bass(self):
        return self.bass

    def use_preferred_chords(self, preferred):
        "Preferred is a list of five preferred accidentals: ['F#', 'Bb', 'Ab', 'C#', 'Eb']"
        self.scale.use_preferred_mapping(preferred)

    def use_flats(self):
        self.scale.use_flats()

    def use_sharps(self):
        self.scale.use_sharps()

    def _check_for_invalid_chords(self):
        if (self.name in non_chords) or \
                (self.name[0] not in valid_notes):  # allow '' ????
            return True
        else:
            return False

    def transpose(self, halfsteps=0):
        if not self.invalid:
            old_root = self.root
            if self.bass:
                bass_interval = self.scale.get_intervals_by_note(self.bass)[0]
            self.scale.transpose(halfsteps)
            self.root = self.scale.root
            self.name = self.name.replace(old_root, self.root)
            if self.bass:
                old_bass = self.bass
                self.bass = self.scale.get_notes_by_interval(bass_interval)[0]
                self.name = self.name.replace("/"+old_bass, "/"+self.bass)
            
    def get_chord_notes_w_bass(self):
        return self.get_notes(), self.bass

    def get_notes(self):
        return self.scale.get_notes_by_interval(*self.intervals)

    def _modify_chord_construction(self, construction, mod_dict):
        for item in mod_dict['-']:
            construction.remove(item)
        for item in mod_dict['+']:
            construction.append(item)
        # re-sort
        pairs = []
        for item in construction:
            r = construction_re.search(item)
            n = r.group('num')
            m = r.group('mod')
            if not m:
                m = ''
            pairs.append((int(n), m))
        pairs.sort()
        construction = [y+str(x) for x, y in pairs]
        return construction
    
    def _calculate_intervals(self):
        intervals = []
        for c in self.construction:
            offset = 0
            if c.startswith('b'):
                offset = -1
                c = c[1:]
            elif c.startswith('#'):
                offset = 1
                c = c[1:]
            intervals.append(int(c)+offset)
        return intervals

    def _parse_chord(self):
        """takes chord dict that had already been parsed"""
        c = ['1', '3', '5']  # start with major chord
        if self.chord_dict['minor']:
            c = self._modify_chord_construction(c, chord_formulas['minor'])
        if self.chord_dict['number']:
            n = self.chord_dict['number']
            if n in ['2', '4']:
                c = self._modify_chord_construction(c, chord_formulas['sus%s' % n])
            else:
                c = self._modify_chord_construction(c, chord_formulas['%s' % n])
        if self.chord_dict['majN']:
            c = self._modify_chord_construction(c, chord_formulas['maj%s' % self.chord_dict['majN']])
        if self.chord_dict['dim'] != None:
            c = self._modify_chord_construction(c, chord_formulas['dim%s' % self.chord_dict['dim']])
        if self.chord_dict['sus'] != None:
            if len(self.chord_dict['sus']) > 3:
                c = self._modify_chord_construction(c, chord_formulas[self.chord_dict['sus']])
            else:
                c = self._modify_chord_construction(c, chord_formulas['sus4'])
        if self.chord_dict['aug']:
            c = self._modify_chord_construction(c, chord_formulas['aug'])
        if self.chord_dict['add']:
            c = self._modify_chord_construction(c, {'-': [], '+': [self.chord_dict['add']]})
        if self.chord_dict['sixnine']:
            c = self._modify_chord_construction(c, chord_formulas['6add9'])
        self.construction = c
        self.intervals = self._calculate_intervals()

    def get_chord_construction(self):
        return self.construction


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        chordlist = sys.argv[1:]
    else:
        chordlist = ['C13', 'C#sus4/F#', 'Cmaj7', 'G', 'G/C']
    for c in chordlist:
        C = Chord(c)
        print(c)
        print("  Const:", ",".join(C.get_chord_construction()))
        print("  Notes:", C.get_chord_notes_w_bass())
        print("  Transposed up 2 steps:")
        C.transpose(2)
        print("     Name:", C.name)
        print("     Const:", ",".join(C.get_chord_construction()))
        print("     Notes:", C.get_chord_notes_w_bass())
        # raw_input("Done.")
