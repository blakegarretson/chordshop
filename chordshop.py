import json
import math
import re
import sys
import os
from pathlib import Path
from PyQt6.QtCore import (QCoreApplication, QEvent, QMargins, QPoint, QFile, QTextStream,
                          QRegularExpression, QSize, Qt, QTimer)
from PyQt6.QtGui import (QAction, QColor, QFont, QFontDatabase, QIcon,
                         QKeySequence, QPixmap, QShortcut, QSyntaxHighlighter,
                         QTextCharFormat, QTextOption, QTextCursor)
from PyQt6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QToolTip, QFileDialog,
                             QDialog, QDialogButtonBox, QFontComboBox, QFrame, QMenu, QTabWidget,
                             QGroupBox, QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem,
                             QMainWindow, QMessageBox, QPushButton, QTableWidget, QPlainTextEdit,
                             QRadioButton, QSizePolicy, QSpinBox, QSplitter, QHeaderView,
                             QStatusBar, QStyle, QTextEdit, QToolBar, QToolButton, QSizePolicy,
                             QVBoxLayout, QWidget, QScrollBar)

import chord
import chordpro

home = Path().home() / ".config" / "chordshop"
settings_file = home / 'settings.json'


class settingsdict(dict):
    """Dict class with dot notation for ease of use"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__  # type: ignore
    __delattr__ = dict.__delitem__  # type: ignore


def save_settings(settings):
    with settings_file.open('w') as jsonfile:
        json.dump(dict(settings), jsonfile, indent=2)


def load_settings():
    with settings_file.open() as jsonfile:
        return settingsdict(json.load(jsonfile))


default_themes = {
    'Monokai': dict(
        theme='Monokai',
        color_text="#fefaf4",
        color_background="#262728",
        color_comment="#ff6289",
        color_section="#fd9967",
        color_chord="#aadc76",
        color_directive="#ffd866",
        color_x="#79dce8",
        color_y="#ab9df3",
        color_z="#fd9967",
    ),
    'Light': dict(
        theme='Light',
        color_text='#55555b',
        color_background='#ffffff',
        color_comment='#c76a2f',  # #comment
        color_section='#ee6997',
        color_directive='#464386',  # sin(), pi
        color_chord='#e56c96',  # + - / etc
        color_x='#64ae4e',
        color_y='#5f6abf',
        color_z='#e99b42',
    )
}

default_settings = dict(
    voicing_frets=16,
    voicing_fingers=4,
    voicing_reach=3,
    voicing_bass_low=0,
    voicing_skippable_bass=2,
    voicing_include=[0, 1, -1],
    font='',
    font_size=16,
    font_bold=False,
) | default_themes['Monokai']


def initililize_config():
    if not home.exists():
        home.mkdir(parents=True)

    if settings_file.exists():
        settings = load_settings()
    else:
        settings = settingsdict(default_settings.copy())
        save_settings(settings)
    return settings


class ChordshopSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, settings, parent=None):
        super().__init__(parent)  # type: ignore

        self.rules = []
        rule_pairs = [  # order matters below, more general go first and are overridden by more specific
            (r'\[.*?\]', settings.color_chord, 900),  # units
            (r'{.*?}', settings.color_directive, None),  # %
            (r'^.*?:\s*$', settings.color_section, None),  # units
            (r'^\s*\(.*?\)\s*$', settings.color_comment, None),  # operator
        ]
        for regexp, color, weight in rule_pairs:
            rule_format = QTextCharFormat()
            rule_format.setForeground(QColor(color))
            if weight:
                rule_format.setFontWeight(weight)
            self.rules.append((QRegularExpression(regexp), rule_format))

    def highlightBlock(self, text):
        for pattern, char_format in self.rules:
            regex = QRegularExpression(pattern)
            match_iterator = regex.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(),
                               match.capturedLength(), char_format)


class ChordshopTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                self.parent._openFile(file_path)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    re_zeropoint = re.compile(r"[. ]|$")
    re_incomplete = re.compile(r'(.*?\s*)\b(\w+)$')
    re_functionname = re.compile(r'\b(\w+)\($')

    def __init__(self, settings):
        super().__init__()
        self.filename = None

        self.setUnifiedTitleAndToolBarOnMac(True)
        self.settings = settings
        self.setWindowTitle("Chordshop")
        self.resize(800, 600)

        font_families = QFontDatabase.families()
        if settings.font not in font_families:
            for fontname in ['Consolas', 'Andale Mono', 'Courier New', 'Noto Sans Mono', 'Monospace', 'Courier']:
                if fontname in font_families:
                    self.settings.font = fontname
                    break

        self.textbox = ChordshopTextEdit(self)
        self.textbox.setAcceptRichText(False)
        self.syntax_highlighter_out = ChordshopSyntaxHighlighter(
            self.settings, self.textbox.document())
        self.updateFont()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.textbox)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setObjectName("Container")
        container.setLayout(layout)
        self.mainwidget = container
        self.setCentralWidget(container)
        self.updateStyle()
        self.create_toolbars()

    def create_toolbars(self):
        self.newAction = QAction("&New", self)
        self.newAction.triggered.connect(self.newFile)
        self.openAction = QAction("&Open...", self)
        self.openAction.triggered.connect(self.openFile)
        self.saveAction = QAction("&Save", self)
        # Edit actions
        self.transposeUpAction = QAction("+1", self)
        self.transposeUpAction.triggered.connect(self.transposeUp)
        self.transposeDownAction = QAction("-1", self)
        self.transposeDownAction.triggered.connect(self.transposeDown)
        self.chords2proAction = QAction("Chords>Pro", self)
        self.chords2proAction.triggered.connect(self.chords2pro)
        self.pro2chordsAction = QAction("Pro>Chords", self)
        self.pro2chordsAction.triggered.connect(self.pro2chords)
        self.undoAction = QAction("UndoConvert", self)
        self.undoAction.triggered.connect(self.undo)
        self.bracket_to_colonAction = QAction("[section]>section:", self)
        self.bracket_to_colonAction.triggered.connect(self.bracket_to_colon)

        self.fileToolBar = self.addToolBar("File")
        self.fileToolBar.addAction(self.newAction)
        self.fileToolBar.addAction(self.openAction)
        self.fileToolBar.addAction(self.saveAction)
        # Edit toolbar
        self.toolsToolBar = QToolBar("Tools", self)
        self.addToolBar(self.toolsToolBar)
        self.toolsToolBar.addWidget(QLabel("Transpose"))
        self.toolsToolBar.addAction(self.transposeUpAction)
        self.toolsToolBar.addAction(self.transposeDownAction)
        self.toolsToolBar.addAction(self.chords2proAction)
        self.toolsToolBar.addAction(self.pro2chordsAction)
        self.toolsToolBar.addAction(self.undoAction)
    def bracket_to_colon(self):
        self.undo_text = self.textbox.toPlainText()
        c = chordpro.ChordPro(self.textbox.toPlainText())
        c.
        self.textbox.setText(c.text)
    def undo(self):
        self.textbox.setText(self.undo_text)

    def chords2pro(self):
        self.undo_text = self.textbox.toPlainText()
        c = chordpro.ChordPro(self.textbox.toPlainText())
        cursor = self.textbox.textCursor()
        current_line = cursor.blockNumber()

        cursor1 = self.textbox.textCursor()
        start_position = cursor1.selectionStart()
        cursor1.setPosition(start_position)
        startline = cursor1.blockNumber()

        cursor2 = self.textbox.textCursor()
        end_position = cursor2.selectionEnd()
        cursor2.setPosition(end_position)
        endline = cursor2.blockNumber()+1

        # print(current_line,startline, endline, '>', start_position-end_position))
        print("???",endline-startline)
        if end_position-start_position == 0: # do whole file
            c.chords_to_chordpro()
        elif (endline-startline==1): # selected part of only one line, force it to chords with no lyrics
            print(start_position,end_position)
            c.chords_to_chordpro(start_position,end_position, forcechords=True)
        else:
            c.chords_to_chordpro(startline, endline)
        self.textbox.setText(c.text)

    def pro2chords(self):
        self.undo_text = self.textbox.toPlainText()
        c = chordpro.ChordPro(self.textbox.toPlainText())
        c.chordpro_to_chords()
        self.textbox.setText(c.text)

    def transpose(self, halfsteps):
        c = chordpro.ChordPro(self.textbox.toPlainText())
        c.transpose(halfsteps)
        self.textbox.setText(c.text)

    def transposeUp(self):
        self.transpose(1)

    def transposeDown(self):
        self.transpose(-1)

    def _openFile(self, filename):
        with open(filename, 'rb') as file:
            content = file.read().decode('utf8', 'replace')
        self.textbox.setText(content)
        self.filename = filename

    def openFile(self):
        fname = QFileDialog.getOpenFileName(
            self,
            "Open File",
            os.getenv("HOME"),
            "All Files (*);; Text Files (*.txt);; Crd Files (*.crd);; ChordPro Files (*.pro *.chopro)",
        )
        print(fname)
        filename = fname[0]
        if filename:
            self._openFile(filename)

    def newFile(self):
        self.textbox.setText("")
        self.filename = None

    def updateStyle(self):
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {self.settings.color_text};
                padding: 0px;
            }}
            """)
        self.mainwidget.setStyleSheet(
            f"#Container {{ background: {self.settings.color_background} ;}}")

    def updateFont(self):
        font = QFont()
        font.setFamily(self.settings.font)  # type: ignore
        font.setPointSize(self.settings.font_size)  # type: ignore
        font.setWeight(800 if self.settings.font_bold else 400)
        font.setBold(True if self.settings.font_bold else False)
        self.textbox.setFont(font)


app = QApplication(sys.argv)
app.setStyle('Fusion')
# app.setWindowIcon(QIcon(":icon.svg"))
window = MainWindow(initililize_config())
window.show()
app.exec()
