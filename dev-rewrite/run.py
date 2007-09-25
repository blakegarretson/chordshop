import profile, chord#, chord2

#profile.run("""print chord2.Voicings("C", reach=2)""")
#print "============================================================="
profile.run("""print chord.Voicings("C13", reach=2)""")
#print chord.Voicings("C", reach=2)
raw_input("")