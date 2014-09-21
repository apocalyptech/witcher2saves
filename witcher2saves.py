#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:
# 
# Copyright (c) 2014, CJ Kucera
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the development team nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL CJ KUCERA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Apologies if much of this is terrible.

import os
import sys
import time
from PyQt4 import QtGui, QtCore

def sizeof_fmt(num):
    """
    Taken from somewhere online, probably stackexchange
    """
    for x in ['b','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')

class Savegame(object):
    """
    Data class to hold what we want to know about the
    savegame files.  A bit lame, whatever.
    """

    def __init__(self, basename, filename_full):
        self.filename = filename_full
        self.basename = basename
        if self.basename[:4] == 'Auto':
            self.manualsave = False
            self.savetype = 'Auto'
            self.number = int(self.basename[9:])
        else:
            self.manualsave = True
            self.savetype = 'Manual'
            self.number = int(self.basename[11:])
        self.mtime = os.path.getmtime(filename_full)
        self.size = os.path.getsize(filename_full)
        self.size_base = self.size
        self.bmpfilename = None

    def set_screenshot(self, bmpfilename):
        """
        We read the screenshot filenames after the .sav files
        themselves, so we don't have it at initialization time
        """
        self.bmpfilename = bmpfilename
        self.size = self.size_base + os.path.getsize(bmpfilename)

    def __cmp__(self, other):
        """
        By default these'll sort by time
        """
        return cmp(self.mtime, other.mtime)

    def delete(self):
        """
        Deletes the files associated with this savegame.  Best to
        discard this object afterwards, since it'll no longer be
        accurate, really.
        """
        if os.path.exists(self.filename):
            os.unlink(self.filename)
        if self.bmpfilename is not None and os.path.exists(self.bmpfilename):
            os.unlink(self.bmpfilename)
        self.size = 0
        self.size_base = 0
        self.mtime = 0

class SavegameCollection(object):
    """
    Holds a collection of savegames
    """

    def __init__(self, basedir=None):

        self.load_savegames(basedir)

    def load_savegames(self, basedir=None):
        """
        Load a bunch of savegames from the given directory.  Will default
        to the known usual savegame dir.
        """

        if basedir is None:
            basedir = os.path.expanduser('~/.local/share/cdprojektred/witcher2/GameDocuments/Witcher 2/gamesaves')
        self.basedir = basedir

        self.savegames = {}
        if os.path.isdir(self.basedir):
            for filename in sorted(os.listdir(self.basedir)):
                if filename[-4:] == '.sav':
                    basename = filename[:-4]
                    savegame = Savegame(basename, os.path.join(self.basedir, filename))
                    self.savegames[basename] = savegame
                elif filename[-12:] == '_640x360.bmp':
                    basename = filename[:-12]
                    self.savegames[basename].set_screenshot(os.path.join(self.basedir, filename))
                #else:
                #    print 'Unknown file: %s' % (filename)

        # May as well keep track of how much room we're taking up, total.
        self.total_size = 0
        for savegame in self:
            self.total_size += savegame.size

    def refresh(self):
        """
        Refreshes our collection (without updating the current basedir)
        """
        self.load_savegames(self.basedir)

    def __len__(self):
        """
        How many items do we have?
        """
        return len(self.savegames)

    def __iter__(self):
        """
        Make this object iterable.
        """
        for key in sorted(self.savegames.keys()):
            yield self.savegames[key]

class OpenSavegameDialog(QtGui.QFileDialog):
    """
    Class to open up a new savegame dir
    """

    def __init__(self, parent, directory, *args):

        super(OpenSavegameDialog, self).__init__(parent=parent,
                caption='Open a Witcher 2 Savegame Dir',
                directory=directory,
                filter='Savegame Files (*.sav)')

        self.setFileMode(self.Directory)

class SaveItemModel(QtGui.QStandardItemModel):
    """
    Small little class for the model we're using on the main save
    selection QTableView.  Mostly just sets our headers.
    """

    def __init__(self, sort_role, changed_signal, *args):

        super(SaveItemModel, self).__init__(*args)

        self.clear()
        self.setSortRole(sort_role)
        self.itemChanged.connect(changed_signal)

    def clear(self):
        """
        Clears ourself, but reinstates our header labels
        """
        super(SaveItemModel, self).clear()
        self.setHorizontalHeaderLabels(['Type', 'Num', 'Size', 'Date'])

class SaveTableView(QtGui.QTableView):
    """
    Main widget that allows us to choose a savegame.  We pass in a
    QLabel which is where we'll show the preview image.
    """

    ROLE_SORT = QtCore.Qt.UserRole+1
    ROLE_OBJ = QtCore.Qt.UserRole+2

    COL_TYPE = 0
    COL_NUM = 1
    COL_SIZE = 2
    COL_DATE = 3

    def __init__(self, image_label, checked_label, *args):
        """
        image_label should be the QLabel where the preview image goes
        """

        super(SaveTableView, self).__init__(*args)

        self.image_label = image_label

        # Some widget defaults
        self.setSelectionBehavior(QtGui.QTableView.SelectRows)
        self.setSelectionMode(QtGui.QTableView.SingleSelection)
        self.verticalHeader().hide()
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setTabKeyNavigation(False);
        self.checked_label = checked_label

        # Stretch header across whole widget width
        self.horizontalHeader().setStretchLastSection(True)

        # Decrease our font size a little bit
        font = self.font()
        font.setPointSize(font.pointSize() - 2)
        self.setFont(font)

        # Set up a model
        self.model = SaveItemModel(self.ROLE_SORT, self.row_checked)
        self.setModel(self.model)

        # Clear us out (sets a few other variables as well)
        self.clear()

    def clear(self):
        """
        Clears out the view, and some other internal variables, to boot.
        """
        self.model.clear()
        self.checked_size = 0
        self.update_checked_label()
        self.current_selected_item = None

    def load_savegames(self, savegames):
        """
        Load in a set of savegames to our model.
        """

        # Clear ourselves first
        self.clear()

        # Loop through all our savegames and add them in
        for savegame in savegames:
            item_type = QtGui.QStandardItem(savegame.savetype)
            item_type.setData(savegame.savetype, self.ROLE_SORT)
            item_type.setCheckable(True)
            item_type.setData(savegame, self.ROLE_OBJ)
            item_type.setEditable(False)

            item_num = QtGui.QStandardItem(str(savegame.number))
            item_num.setData(savegame.number, self.ROLE_SORT)
            item_num.setEditable(False)

            item_size = QtGui.QStandardItem(sizeof_fmt(savegame.size))
            item_size.setData(savegame.size, self.ROLE_SORT)
            item_size.setEditable(False)

            item_date = QtGui.QStandardItem(time.ctime(savegame.mtime))
            item_date.setData(savegame.mtime, self.ROLE_SORT)
            item_date.setEditable(False)

            self.model.appendRow([item_type, item_num, item_size, item_date])

        # Do some operations which only make sense once we have data
        self.sortByColumn(self.COL_NUM, QtCore.Qt.DescendingOrder)
        self.resizeColumnsToContents()

        # Select the first row, if we have one
        if self.model.rowCount() > 0:
            self.selectRow(0)
        else:
            self.clear_image()

    def update_checked_label(self):
        """
        Updates our checked_label QLabel, which will display the size of all the
        currently-selected savegames.
        """
        self.checked_label.setText('<b>%s</b>' % (sizeof_fmt(self.checked_size)))

    def selectionChanged(self, selected, deselected):
        """
        Previously, before I'd pulled this into its own class, I'd set this up
        basically like so, out in the main "Gui" class:

        self.connect(tv.selectionModel(),
                QtCore.SIGNAL('selectionChanged(QItemSelection, QItemSelection)'),
                self.selection_changed)

        A bit voodoo, certainly, but it did the trick.
        """
        super(SaveTableView, self).selectionChanged(selected, deselected)

        if not selected.isEmpty():
            selected_item = selected.indexes()[self.COL_TYPE]
            self.current_selected_item = self.model.itemFromIndex(selected_item)
            savegame = selected_item.data(self.ROLE_OBJ).toPyObject()
            if savegame.bmpfilename is not None:
                self.image_label.setPixmap(QtGui.QPixmap(savegame.bmpfilename))
                return
        
        # Fallback, clear out the image
        self.clear_image()

    def clear_image(self):
        """
        Clears our preview image (or, more accurately, fills it with black)
        """
        pixmap = self.image_label.pixmap()
        if not pixmap:
            pixmap = QtGui.QPixmap(640, 360)
        pixmap.fill(QtCore.Qt.black)
        self.image_label.setPixmap(pixmap)

    def select_all(self, signal_bool=False, set_checked=True):
        if set_checked:
            to_state = QtCore.Qt.Checked
        else:
            to_state = QtCore.Qt.Unchecked
        for row in range(self.model.rowCount()):
            self.model.item(row).setCheckState(to_state)

    def invert_selection(self):
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item.checkState() != QtCore.Qt.Checked:
                item.setCheckState(QtCore.Qt.Checked)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)

    def delete_checked(self):
        """
        Deletes all checked items
        """
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                savegame = item.data(self.ROLE_OBJ).toPyObject()
                savegame.delete()

    def row_checked(self, item):
        """
        What to do when a row is checked.  Mostly just updating our label
        """
        savegame = item.data(self.ROLE_OBJ).toPyObject()
        if item.checkState() == QtCore.Qt.Checked:
            self.checked_size += savegame.size
        else:
            self.checked_size -= savegame.size
        
        # A bit of sanity check, though this would indicate weird issues
        if self.checked_size < 0:
            print "WARNING: negative checked_size encountered.  This shouldn't happen"
            self.checked_size = 0

        # Update our label
        self.update_checked_label()

    def keyPressEvent(self, e):
        """
        Detects key presses, to enable toggling the checkbox of the currently-
        selected item
        """

        if e.key() == QtCore.Qt.Key_Space:
            if self.current_selected_item is not None:
                if self.current_selected_item.checkState() == QtCore.Qt.Checked:
                    self.current_selected_item.setCheckState(QtCore.Qt.Unchecked)
                else:
                    self.current_selected_item.setCheckState(QtCore.Qt.Checked)
        else:
            super(SaveTableView, self).keyPressEvent(e)

class Gui(QtGui.QMainWindow):

    def __init__(self):
        super(Gui, self).__init__()
        self.savegames = SavegameCollection()
        self.initUI()

    def initUI(self):

        # Open a new dir on Ctrl-O
        openAction = QtGui.QAction('&Open', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.open_new_gamedir)

        # Exit on Ctrl-Q
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)

        # Menu
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)

        # StatusBar
        self.statusBar().setStyleSheet('QStatusBar { background-color: %s; border: 1px solid %s }' %
                (self.palette().light().color().name(), self.palette().dark().color().name()))

        # Set up a main hbox to use
        hbox = QtGui.QHBoxLayout()
        main = QtGui.QWidget()
        main.setLayout(hbox)
        self.setCentralWidget(main)

        # Vbox to live inside the main hbox
        vbox = QtGui.QVBoxLayout()
        hbox.addLayout(vbox)

        # Image Preview Area
        self.image_label = QtGui.QLabel(self)
        hbox.addWidget(self.image_label)

        # Main selection QTableView
        self.size_label_checked = QtGui.QLabel('<b>%s</b>' % (sizeof_fmt(0)))
        self.tv = SaveTableView(self.image_label, self.size_label_checked)
        self.load_savegames()
        vbox.addWidget(self.tv)

        # Control Button Area
        btn_grid = QtGui.QGridLayout(self)
        vbox.addLayout(btn_grid)

        # Size info grid
        size_grid = QtGui.QGridLayout(self)
        btn_grid.addLayout(size_grid, 0, 0, 2, 1)

        size_grid.addWidget(QtGui.QLabel('<i>Total Savegame Size:</i>'), 0, 0)
        size_grid.addWidget(QtGui.QLabel('<i>Checked Savegame Size:</i>'), 1, 0)

        self.size_label_total = QtGui.QLabel('<b>%s</b>' % (sizeof_fmt(0)))
        size_grid.addWidget(self.size_label_total, 0, 1)
        self.update_total_size()

        # self.size_label_checked is defined above so it can be passed to SaveTableView
        size_grid.addWidget(self.size_label_checked, 1, 1)

        # Now the actual control buttons...
        btn = QtGui.QPushButton('Select All')
        btn.clicked.connect(self.tv.select_all)
        btn_grid.addWidget(btn, 0, 1)

        btn = QtGui.QPushButton('Invert Selection')
        btn.clicked.connect(self.tv.invert_selection)
        btn_grid.addWidget(btn, 1, 1)

        btn = QtGui.QPushButton('Delete Checked')
        btn.clicked.connect(self.delete_checked)
        btn_grid.addWidget(btn, 2, 0)

        btn = QtGui.QPushButton('Refresh')
        btn.clicked.connect(self.refresh)
        btn_grid.addWidget(btn, 2, 1)

        # Global Parameters
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('CleanLooks'))
        self.setMinimumSize(1100, 700)
        self.setWindowTitle('Witcher 2 Savegame Manager')
        self.show()

    def refresh(self):
        """
        Refreshes our list of savegames
        """
        self.savegames.refresh()
        self.load_savegames()
        self.update_total_size()

    def load_savegames(self):
        """
        Loads our savegames and updates our status bar
        """
        self.tv.load_savegames(self.savegames)
        if len(self.savegames) == 1:
            plural = ''
        else:
            plural = 's'
        self.statusBar().showMessage('%d savegame%s in %s' % (len(self.savegames), plural, self.savegames.basedir))

    def delete_checked(self):
        """
        Deletes our checked savegames.  Will automatically refresh afterwards.
        """
        self.tv.delete_checked()
        self.refresh()

    def update_total_size(self):
        """
        Updates our "total size" label
        """
        self.size_label_total.setText('<b>%s</b>' % (sizeof_fmt(self.savegames.total_size)))

    def open_new_gamedir(self):
        """
        Opens an arbitrary gamedir location
        """
        dialog = OpenSavegameDialog(self, self.savegames.basedir)
        if dialog.exec_():
            filenames = dialog.selectedFiles()
            self.savegames.load_savegames(str(filenames[0]))
            self.load_savegames()
            self.update_total_size()

def main():

    app = QtGui.QApplication(sys.argv)
    gui = Gui()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
