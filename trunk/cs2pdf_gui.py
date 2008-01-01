#!/usr/bin/env python
import sys, cs2pdf

def errorGUI(message):
    import wx
    class StandAloneErrorDialog(wx.App):
        def OnInit(self):
            frame = wx.MessageDialog(None, message, 'Chordshop Error', wx.OK | wx.ICON_ERROR)
            frame.ShowModal()
            return True
    err = StandAloneErrorDialog(0)
    err.MainLoop()

if __name__ == '__main__':
    try:
        for f in sys.argv[1:]:
            cs2pdf.process_file(f)
    except cs2pdf.Error, error:
        errorGUI(error.message)
    except:
        c,i,t = sys.exc_info()
        errorGUI("Unexpected Error:\n\n%s\n\nType: %s" % (str(i),str(c)))
