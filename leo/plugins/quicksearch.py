#@+leo-ver=5-thin
#@+node:ville.20090314215508.4: * @file quicksearch.py
#@+<< docstring >>
#@+node:ville.20090314215508.5: ** << docstring >>
''' Adds a fast-to-use search widget, like the "Find in files" feature of many editors.

Just load the plugin, activate "Nav" tab, enter search text and press enter.

Usage
=====

The pattern to search for is, by default, a case *insensitive* fnmatch pattern
(e.g. foo*bar), because they are typically easier to type than regexps. If you
want to search for a regexp, use 'r:' prefix, e.g. r:foo.*bar.

Regexp matching is case sensitive; if you want to do a case-insensitive regular
expression search (or any kind of case-sensitive search in the first place), do it
by searching for "r:(?i)Foo". (?i) is a standard feature of Python regular expression
syntax, as documented in 

http://docs.python.org/library/re.html#regular-expression-syntax

Commands
========

This plugin defines the following commands that can be bound to keys:
    
- find-quick:
  Opens the Nav tab.

- find-quick-selected:
  Opens the Nav tab with the selected text as the search string.

- focus-to-nav:
  Puts focus in Nav tab.

- find-quick-test-failures:
  Lists nodes in c.db.get('unittest/cur/fail')

- find-quick-timeline:
  Lists all nodes in reversed gnx order, basically newest to oldest, creation wise,
  not modification wise.

- history:
  Lists nodes from c.nodeHistory.
    
- marked-list:
  List all marked nodes.

'''
#@-<< docstring >>

__version__ = '0.0'
#@+<< version history >>
#@+node:ville.20090314215508.6: ** << version history >>
#@@killcolor
#@+at
# 
# 0.1 Ville M. Vainio <vivainio@gmail.com>: Fully functional version,
# 
#@-<< version history >>

#@+<< imports >>
#@+node:ville.20090314215508.7: ** << imports >>
import leo.core.leoGlobals as g

g.assertUi('qt')

from leo.core import leoNodes
    # Uses leoNodes.posList.

from PyQt4.QtGui import QListWidget, QListWidgetItem
from PyQt4 import QtCore
from PyQt4 import QtGui

import fnmatch, re

from leo.plugins import qt_quicksearch

global qsWidget
#@-<< imports >>

#@+others
#@+node:ville.20090314215508.8: ** init
def init ():

    ok = g.app.gui.guiName() == "qt"

    if ok:
        g.registerHandler('after-create-leo-frame',onCreate)
        g.plugin_signon(__name__)

    return ok
#@+node:ville.20090314215508.9: ** onCreate
def onCreate (tag, keys):

    c = keys.get('c')
    if not c: return

    install_qt_quicksearch_tab(c)

#@+node:tbrown.20111011152601.48461: ** show_unittest_failures
def show_unittest_failures(event):
    c = event.get('c')
    fails = c.db.get('unittest/cur/fail')
    # print(fails)
    nav = c.frame.nav
    #print nav

    nav.scon.clear()
    if fails:
        for gnx, stack in fails:
            pos = None
            # sucks
            for p in c.all_positions():
                if p.gnx == gnx:
                    pos = p.copy()
                    break
    
            def mkcb(pos, stack):
                def focus():            
                    g.es(stack)
                    c.selectPosition(pos)        
                return focus
    
            it = nav.scon.addGeneric(pos.h, mkcb(pos,stack))
            it.setToolTip(stack)

    c.k.simulateCommand('focus-to-nav')
#@+node:tbrown.20111011152601.48462: ** install_qt_quicksearch_tab (Creates commands)
def install_qt_quicksearch_tab(c):
    
    #tabw = c.frame.top.tabWidget

    wdg = LeoQuickSearchWidget(c)
    qsWidgent = wdg
    c.frame.log.createTab("Nav", widget = wdg)
    #tabw.addTab(wdg, "QuickSearch")

    def focus_quicksearch_entry(event):
        c.frame.log.selectTab('Nav')
        wdg.ui.lineEdit.selectAll()
        wdg.ui.lineEdit.setFocus()

    def focus_to_nav(event):
        c.frame.log.selectTab('Nav')
        wdg.ui.listWidget.setFocus()
        
    def find_selected(event):
        text = c.frame.body.getSelectedText()
        if text.strip():
            wdg.ui.lineEdit.setText(text)
            wdg.returnPressed()
            focus_to_nav(event)
        else:
            focus_quicksearch_entry(event)
            
    def nodehistory(event):
        c.frame.log.selectTab('Nav')
        wdg.scon.doNodeHistory()

    def timeline(event):
        c.frame.log.selectTab('Nav')
        wdg.scon.doTimeline()

    c.k.registerCommand(
        'find-quick',None,focus_quicksearch_entry)
    c.k.registerCommand(
        'find-quick-selected','Ctrl-Shift-f',find_selected)
    c.k.registerCommand(
        'focus-to-nav', None,focus_to_nav)
    c.k.registerCommand(
        'find-quick-test-failures', None,show_unittest_failures)
    c.k.registerCommand(
        'find-quick-timeline', None, timeline)
    c.k.registerCommand(
        'history', None, nodehistory)

    @g.command('marked-list')
    def showmarks(event):
        """ List marked nodes in nav tab """
        #c.frame.log.selectTab('Nav')
        wdg.scon.doShowMarked()

    c.frame.nav = wdg            

    # make activating this tab activate the input box
    def activate_input(idx, c=c):
        wdg = c.frame.nav
        tab_widget = wdg.parent().parent()
        if tab_widget.currentWidget() == wdg:
            wdg.ui.lineEdit.selectAll()
            wdg.ui.lineEdit.setFocus()

    # Careful: we may be unit testing.
    if wdg and wdg.parent():
        tab_widget = wdg.parent().parent()
        tab_widget.connect(tab_widget,
            QtCore.SIGNAL("currentChanged(int)"), activate_input)
#@+node:ekr.20111015194452.15716: ** class QuickSearchEventFilter
class QuickSearchEventFilter(QtCore.QObject):

    #@+others
    #@+node:ekr.20111015194452.15718: *3*  ctor (leoQtEventFilter)
    def __init__(self,c,w):

        # Init the base class.
        QtCore.QObject.__init__(self)
        
        self.c = c
        self.w = w
    #@+node:ekr.20111015194452.15719: *3* eventFilter
    def eventFilter(self,obj,event):

        eventType = event.type()
        ev = QtCore.QEvent
        
        # QLineEdit generates ev.KeyRelease only on Windows,Ubuntu
        kinds = [ev.KeyPress,ev.KeyRelease]
        
        g.trace(eventType,eventType in kinds)
        
        if eventType in kinds:
            self.w.onKeyPress(event)
            
        return False
    #@-others
#@+node:ville.20090314215508.2: ** class LeoQuickSearchWidget (QWidget)
class LeoQuickSearchWidget(QtGui.QWidget):
    
    """ 'Find in files'/grep style search widget """

    #@+others
    #@+node:ekr.20111015194452.15695: *3*  ctor
    def __init__(self,c,parent=None):
        
        QtGui.QWidget.__init__(self, parent)

        self.ui = qt_quicksearch.Ui_LeoQuickSearchWidget()
        self.ui.setupUi(self)

        w = self.ui.listWidget
        
        cc = QuickSearchController(c,w)
        self.scon = cc

        self.connect(self.ui.lineEdit,
            QtCore.SIGNAL("returnPressed()"),
            self.returnPressed)

        self.c = c

    #@+node:ekr.20111015194452.15696: *3* returnPressed
    def returnPressed(self):

        t = g.u(self.ui.lineEdit.text())
        if not t.strip():
            return

        if t == g.u('m'):
            self.scon.doShowMarked()
        else:        
            self.scon.doSearch(t)

        if self.scon.its:
            self.ui.listWidget.blockSignals(True) # don't jump to first hit
            self.ui.listWidget.setFocus()
            self.ui.listWidget.blockSignals(False) # ok, respond if user moves
    #@-others
#@+node:ekr.20111014074810.15659: ** matchLines
def matchlines(b, miter):

    res = []
    for m in miter:
        st, en = g.getLine(b, m.start())
        li = b[st:en].strip()
        res.append((li, (m.start(), m.end() )))
    return res

#@+node:ville.20090314215508.12: ** QuickSearchController
class QuickSearchController:
    
    #@+others
    #@+node:ekr.20111015194452.15685: *3* __init__
    def __init__(self,c,listWidget):

        self.c = c
        self.lw = w = listWidget # A QListWidget.
        self.its = {} # Keys are id(w),values are tuples (p,pos)

        # we want both single-clicks and activations (press enter)
        w.connect(w,
            QtCore.SIGNAL("itemActivated(QListWidgetItem*)"),
            self.onActivated)
          
        w.connect(w,                                  
            QtCore.SIGNAL("itemPressed(QListWidgetItem*)"),
            self.onSelectItem)
            
        w.connect(w,
            QtCore.SIGNAL("currentItemChanged(QListWidgetItem*,QListWidgetItem *)"),
            self.onSelectItem)
            
        # Doesn't work.
        # ev_filter = QuickSearchEventFilter(c,w)
        # w.installEventFilter(ev_filter)
    #@+node:ekr.20111015194452.15689: *3* addBodyMatches
    def addBodyMatches(self, poslist):
                
        for p in poslist:
            it = QListWidgetItem(p.h, self.lw)
            f = it.font()
            f.setBold(True)
            it.setFont(f)

            self.its[id(it)] = (p, None)
            ms = matchlines(p.b, p.matchiter)
            for ml, pos in ms:
                #print "ml",ml,"pos",pos
                it = QListWidgetItem(ml, self.lw)   
                self.its[id(it)] = (p,pos)
    #@+node:ekr.20111015194452.15690: *3* addGeneric
    def addGeneric(self, text, f):
        
        """ Add generic callback """

        it = id(QListWidgetItem(text, self.lw))
        self.its[id(it)] = f
        return it
    #@+node:ekr.20111015194452.15688: *3* addHeadlineMatches
    def addHeadlineMatches(self, poslist):

        for p in poslist:
            it = QListWidgetItem(p.h, self.lw)   
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            self.its[id(it)] = (p,None)
    #@+node:ekr.20111015194452.15691: *3* clear
    def clear(self):

        self.its = {}
        self.lw.clear()

    #@+node:ekr.20111015194452.15693: *3* doNodeHistory
    def doNodeHistory(self):

        nh = leoNodes.poslist(po[0] for po in self.c.nodeHistory.beadList)
        nh.reverse()
        self.clear()
        self.addHeadlineMatches(nh)
    #@+node:tbrown.20120220091254.45207: *3* doTimeline
    def doTimeline(self):

        c = self.c
        timeline = [p.copy() for p in c.all_unique_positions()]
        timeline.sort(key=lambda x: x.gnx, reverse=True)
        self.clear()
        self.addHeadlineMatches(timeline)
    #@+node:ekr.20111015194452.15692: *3* doSearch
    def doSearch(self, pat):

        self.clear()

        if not pat.startswith('r:'):
            hpat = fnmatch.translate('*'+ pat + '*').replace(r"\Z(?ms)","")
            bpat = fnmatch.translate(pat).rstrip('$').replace(r"\Z(?ms)","")
            flags = re.IGNORECASE
        else:
            hpat = pat[2:]
            bpat = pat[2:]
            flags = 0

        hm = self.c.find_h(hpat, flags)
        self.addHeadlineMatches(hm)
        bm = self.c.find_b(bpat, flags)
        self.addBodyMatches(bm)

        self.lw.insertItem(0, "%d hits"%self.lw.count())
    #@+node:ekr.20111015194452.15687: *3* doShowMarked
    def doShowMarked(self):

        self.clear()
        c = self.c
        pl = leoNodes.poslist()
        for p in c.all_positions():
            if p.isMarked():
                pl.append(p.copy())
        self.addHeadlineMatches(pl)
    #@+node:ekr.20111015194452.15700: *3* Event handlers
    #@+node:ekr.20111015194452.15686: *4* onSelectItem
    def onSelectItem(self, it, it_prev=None):
        
        c = self.c
            
        tgt = self.its.get(it and id(it))

        if not tgt: return

        # generic callable
        if callable(tgt):
            tgt()
        elif len(tgt) == 2:            
            p, pos = tgt
            c.selectPosition(p)
            if pos is not None:
                st, en = pos
                w = c.frame.body.bodyCtrl
                w.setSelectionRange(st,en)
                w.seeInsertPoint()
                
            self.lw.setFocus()
    #@+node:tbrown.20111018130925.3642: *4* onActivated
    def onActivated (self,event):
        
        c = self.c

        c.bodyWantsFocusNow()
    #@-others
#@-others
#@-leo
