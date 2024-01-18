"""
2-line chord:
C       D    G
This is an example

Chordpro:
[C]This [D]is an ex[G]ample

"""

import chord, re

not_chordpro = r'\[([A-Za-z0-9+]+)\]'
not_chordpro_re = re.compile(not_chordpro)
bracket_section = r'^\[([A-Za-z0-9 ]+)\]\s*$'
bracket_section_re = re.compile(bracket_section, re.MULTILINE)

def is_chord_line(line):
    """Determine if line is only chords or chord-like e.g. C, Dm, /, -. NC."""
    items = line.strip().split()
    if items:
        return all([chord.chordline_re.search(x) for x in items])
    else:
        return False


class ChordPro():
    def __init__(self, text=''):
        self.setText(text)

    def setText(self, text):
        self.text = text

    def _weave_chords(self, line, chord_positions):
        new_line = []
        # lengthen with spaces if necessary
        if len(line) < chord_positions[-1][0]:
            line = line+" "*(chord_positions[-1][0]-len(line))

        previous_loc = 0
        for pos, crd in chord_positions:
            print(pos, crd)
            loc_pos = pos - previous_loc
            new_line.append(line[:loc_pos])
            new_line.append(f'[{crd}]')
            line = line[loc_pos:]
            previous_loc = pos
        new_line.append(line)
        print(">>", new_line)
        return "".join(new_line).strip()

    def chords_to_chordpro(self, start=0, end=1000000, forcechords=False):
        if forcechords: # just force the single line to chords without lyrics
            line = self.text[start:end]            
            while r := not_chordpro_re.search(line):
                print(r)
                print(dir(r))
                line = line[:r.span()[0]] +f'[{r.group()}]'+ line[r.span()[1]:]
            self.text = self.text[:start] + line + self.text[end:]
        else:
            lines = self.text.splitlines()
            pre = lines[:start]
            process = lines[start:end]
            post = lines[end:]

            processed_lines = []
            chord_positions = []
            for line in process:
                if is_chord_line(line):
                    if chord_positions:
                        # this is a chord line AND the previous on was too.
                        # the prev line of chords has no words
                        processed_lines.append(
                            self._weave_chords(line, chord_positions))
                        chord_positions = []
                    r = chord.chordline_re.finditer(line)
                    for x in r:
                        chord_positions.append((x.start(), x.group()))
                    continue
                else:
                    if chord_positions:  # previous line was a chord line
                        processed_lines.append(
                            self._weave_chords(line, chord_positions))
                        chord_positions = []  # clear
                    else:  # not a chord line, previous line wasn't chords either. Just add it.
                        processed_lines.append(line)
            self.text = "\n".join(pre+processed_lines+post)

    def chordpro_to_chords(self):
        pass
    def bracket_to_colon(self):
        """Transform sections designated with brackets to sections with a colon.
        e.g.
        [Verse 1] becomes Verse 1:
        
        This is useful for songs cut and pasted from some tab sites."""
        
        while r:=bracket_section_re.search(self.text):
            self.text = self.text[:r.span()[0]] + f'{r.groups()[0]}:' + self.text[r.span()[1]:]
        

    def transpose(self, halftones):
        text = self.text[:]
        newtext = ""
        while result := chord.bracket_chords_re.search(text):
            print(result)
            chordname = result.groups()[0]
            start, end = result.span()
            c = chord.Chord(chordname)
            c.transpose(halftones)
            newtext += text[:start] + f'[{c.name}]'
            text = text[end:]
        newtext += text
        self.text = newtext


test = """
G             Cm    G            C   G                   C     G            C   
Longer boats are coming to win us coming to win us  their comeing to win us  

G             C    G            C  G           C   G      D                    
Longer boats are coming to win us  hold on to the shore......                 
             C                     G    C G G C G G C G                        
They'll be taking the key from the door.............                           
"""
test2 = """
{t:BITTERBLUE}
{st:Cat Stevens}
{comment: Trancribed by Namrud}

{comment: intro}
[C] [G] [Em] [F]
 
I ga[C]ve my last chance to you
don't hand it back to me bitter[G]blue
no bitterblue
Yes, [Cmaj]I've done all one man can do
don't pass me up oh bitter[G]blue
my bitterblue
[D]cause I've been running a l[G]ong time
o[C7/G]n this travelling gr[A]ound  [D]
w[D]ishing hard to be f[G]ree"""

test3= """
"How Can I Tell You"   (Cat Stevens)

intro: Em A D G

[Verse 1]
Em           A               D G D G      Em  A
How can I tell you that I love  you, I love you
      D     G        D              G
But I can't think of right words to say
Em              A               D G    D        G
I long to tell you that I am always thinking of you,

[Chorus]
    Em                 A
I'm always thinking of you,
       D     G     D       G  D G D        G
But my words just blow away,     just blow away
   Em                   A
It always ends up to one thing, honey,
      D     G     D                 G    Em A
And I can't think of right words to say.

2.)
Wherever I am, girl,
I am always walking with you,
I am always walking with you,
But I look and you're not there,
Whoever I'm with I'm always,"""

# print([is_chord_line(line) for line in test.splitlines() if line])

# c = ChordPro(test2)
# c.transpose(2)
# print(c.text)
# z0="G             C    G            C   G                   C     G            C"
# z1="             C    G            C   G                   C     G            C"
# z2="             Cmaj7    G            C   Gm                   C     G            C"

# for z in z0,z1,z2:
#     print(is_chord_line(z))
#     r = chord.chordline_re.finditer(z)
#     print(r)
#     for x in r:
#         print (x)
#         print(x.start(),x.group())
#     print(r)
# test="""
#       D     G        D              G
# But I can't think of right words to say
# """

c = ChordPro(test3)
c.bracket_to_colon()
# c.chords_to_chordpro()
print(c.text)
# c = ChordPro(test)
# c.chords_to_chordpro(12, 25, forcechords=True)
# print(c.text)
