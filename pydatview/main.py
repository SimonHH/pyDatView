from __future__ import division, unicode_literals, print_function, absolute_import
from builtins import map, range, chr, str
from io import open
from future import standard_library
standard_library.install_aliases()

import numpy as np
import os.path 
import sys
import traceback 
import gc
try:
    import pandas as pd
except:
    print('')
    print('')
    print('Error: problem loading pandas package:')
    print('  - Check if this package is installed ( e.g. type: `pip install pandas`)')
    print('  - If you are using anaconda, try `conda update python.app`')
    print('  - If none of the above work, contact the developer.')
    print('')
    print('')
    sys.exit(-1)
    #raise


#  GUI
import wx
from .GUIPlotPanel import PlotPanel
from .GUISelectionPanel import SelectionPanel,SEL_MODES,SEL_MODES_ID
from .GUISelectionPanel import ColumnPopup,TablePopup
from .GUIInfoPanel import InfoPanel
from .GUIToolBox import GetKeyString, TBAddTool
from .Tables import TableList, Table
# Helper
from .common import *
from .GUICommon import *
# Pluggins
from .plugins import dataPlugins

try:
    import weio.weio as weio# File Formats and File Readers
except:
    print('')
    print('Error: the python package `weio` was not imported successfully.\n')
    print('Most likely the submodule `weio` was not cloned with `pyDatView`')
    print('Type the following command to retrieve it:\n')
    print('   git submodule update --init --recursive\n')
    print('Alternatively re-clone this repository into a separate folder:\n')
    print('   git clone --recurse-submodules https://github.com/ebranlard/pyDatView\n')
    sys.exit(-1)

from .appdata import loadAppData, saveAppData, configFilePath, defaultAppData

# --------------------------------------------------------------------------------}
# --- GLOBAL 
# --------------------------------------------------------------------------------{
PROG_NAME='pyDatView'
PROG_VERSION='v0.3-local'
SIDE_COL       = [160,160,300,420,530]
SIDE_COL_LARGE = [200,200,360,480,600]
BOT_PANL =85

#matplotlib.rcParams['text.usetex'] = False
# matplotlib.rcParams['font.sans-serif'] = 'DejaVu Sans'
#matplotlib.rcParams['font.family'] = 'Arial'
#matplotlib.rcParams['font.sans-serif'] = 'Arial'
# matplotlib.rcParams['font.family'] = 'sans-serif'





# --------------------------------------------------------------------------------}
# --- Drag and drop 
# --------------------------------------------------------------------------------{
# Implement File Drop Target class
class FileDropTarget(wx.FileDropTarget):
   def __init__(self, parent):
      wx.FileDropTarget.__init__(self)
      self.parent = parent
   def OnDropFiles(self, x, y, filenames):
      filenames = [f for f in filenames if not os.path.isdir(f)]
      filenames.sort()
      if len(filenames)>0:
          # If Ctrl is pressed we add
          bAdd= wx.GetKeyState(wx.WXK_CONTROL);
          iFormat=self.parent.comboFormats.GetSelection()
          if iFormat==0: # auto-format
              Format = None
          else:
              Format = self.parent.FILE_FORMATS[iFormat-1]
          self.parent.load_files(filenames, fileformats=[Format]*len(filenames), bAdd=bAdd)
      return True




# --------------------------------------------------------------------------------}
# --- Main Frame  
# --------------------------------------------------------------------------------{
class MainFrame(wx.Frame):
    def __init__(self, data=None):
        # Parent constructor
        wx.Frame.__init__(self, None, -1, PROG_NAME+' '+PROG_VERSION)
        # Hooking exceptions to display them to the user
        sys.excepthook = MyExceptionHook
        # --- Data
        self.tabList=TableList()
        self.restore_formulas = []
        self.systemFontSize = self.GetFont().GetPointSize()
        self.data = loadAppData(self)
        self.datareset = False
        # Global variables...
        setFontSize(self.data['fontSize'])
        setMonoFontSize(self.data['monoFontSize'])

        # --- GUI
        #font = self.GetFont()
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #font.SetFamily(wx.FONTFAMILY_DEFAULT)
        #font.SetFamily(wx.FONTFAMILY_MODERN)
        #font.SetFamily(wx.FONTFAMILY_SWISS)
        #font.SetPointSize(8)
        #print(font.GetFamily(),font.GetStyle(),font.GetPointSize())
        #self.SetFont(font) 
        self.SetFont(getFont(self))
        # --- Menu
        menuBar = wx.MenuBar()

        fileMenu = wx.Menu()
        loadMenuItem  = fileMenu.Append(wx.ID_NEW,"Open file" ,"Open file"           )
        exptMenuItem  = fileMenu.Append(-1        ,"Export table" ,"Export table"           )
        saveMenuItem  = fileMenu.Append(wx.ID_SAVE,"Save figure" ,"Save figure"           )
        exitMenuItem  = fileMenu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        menuBar.Append(fileMenu, "&File")
        self.Bind(wx.EVT_MENU,self.onExit  ,exitMenuItem)
        self.Bind(wx.EVT_MENU,self.onLoad  ,loadMenuItem)
        self.Bind(wx.EVT_MENU,self.onExport,exptMenuItem)
        self.Bind(wx.EVT_MENU,self.onSave  ,saveMenuItem)

        dataMenu = wx.Menu()
        menuBar.Append(dataMenu, "&Data")
        self.Bind(wx.EVT_MENU, lambda e: self.onShowTool(e, 'Mask')  , dataMenu.Append(wx.ID_ANY, 'Mask'))
        self.Bind(wx.EVT_MENU, lambda e: self.onShowTool(e,'Outlier'), dataMenu.Append(wx.ID_ANY, 'Outliers removal'))
        self.Bind(wx.EVT_MENU, lambda e: self.onShowTool(e,'Filter') , dataMenu.Append(wx.ID_ANY, 'Filter'))
        self.Bind(wx.EVT_MENU, lambda e: self.onShowTool(e,'Resample') , dataMenu.Append(wx.ID_ANY, 'Resample'))
        self.Bind(wx.EVT_MENU, lambda e: self.onShowTool(e,'FASTRadialAverage'), dataMenu.Append(wx.ID_ANY, 'FAST - Radial average'))

        # --- Data Plugins
        for string, function, isPanel in dataPlugins:
            self.Bind(wx.EVT_MENU, lambda e, s_loc=string: self.onDataPlugin(e, s_loc), dataMenu.Append(wx.ID_ANY, string))

        toolMenu = wx.Menu()
        menuBar.Append(toolMenu, "&Tools")
        self.Bind(wx.EVT_MENU,lambda e: self.onShowTool(e, 'CurveFitting'), toolMenu.Append(wx.ID_ANY, 'Curve fitting'))
        self.Bind(wx.EVT_MENU,lambda e: self.onShowTool(e, 'LogDec')      , toolMenu.Append(wx.ID_ANY, 'Damping from decay'))

        helpMenu = wx.Menu()
        aboutMenuItem = helpMenu.Append(wx.NewId(), 'About', 'About')
        resetMenuItem = helpMenu.Append(wx.NewId(), 'Reset options', 'Rest options')
        menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU,self.onAbout, aboutMenuItem)
        self.Bind(wx.EVT_MENU,self.onReset, resetMenuItem)


        self.FILE_FORMATS, errors= weio.fileFormats(ignoreErrors=True, verbose=False)
        if len(errors)>0:
            for e in errors:
                Warn(self, e)

        self.FILE_FORMATS_EXTENSIONS = [['.*']]+[f.extensions for f in self.FILE_FORMATS]
        self.FILE_FORMATS_NAMES      = ['auto (any supported file)'] + [f.name for f in self.FILE_FORMATS]
        self.FILE_FORMATS_NAMEXT     =['{} ({})'.format(n,','.join(e)) for n,e in zip(self.FILE_FORMATS_NAMES,self.FILE_FORMATS_EXTENSIONS)]

        # --- ToolBar
        tb = self.CreateToolBar(wx.TB_HORIZONTAL|wx.TB_TEXT|wx.TB_HORZ_LAYOUT)
        self.toolBar = tb 
        self.comboFormats = wx.ComboBox(tb, choices = self.FILE_FORMATS_NAMEXT, style=wx.CB_READONLY)  
        self.comboFormats.SetSelection(0)
        self.comboMode = wx.ComboBox(tb, choices = SEL_MODES, style=wx.CB_READONLY)  
        self.comboMode.SetSelection(0)
        self.Bind(wx.EVT_COMBOBOX, self.onModeChange, self.comboMode )
        tb.AddSeparator()
        tb.AddControl( wx.StaticText(tb, -1, 'Mode: ' ) )
        tb.AddControl( self.comboMode ) 
        tb.AddStretchableSpace()
        tb.AddControl( wx.StaticText(tb, -1, 'Format: ' ) )
        tb.AddControl(self.comboFormats ) 
        tb.AddSeparator()
        #bmp = wx.Bitmap('help.png') #wx.Bitmap("NEW.BMP", wx.BITMAP_TYPE_BMP) 
        TBAddTool(tb,"Open"  ,wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN),self.onLoad)
        TBAddTool(tb,"Reload",wx.ArtProvider.GetBitmap(wx.ART_REDO),self.onReload)
        try:
            TBAddTool(tb,"Add"   ,wx.ArtProvider.GetBitmap(wx.ART_PLUS),self.onAdd)
        except:
            TBAddTool(tb,"Add"   ,wx.ArtProvider.GetBitmap(wx.FILE_OPEN),self.onAdd)
        #self.AddTBBitmapTool(tb,"Debug" ,wx.ArtProvider.GetBitmap(wx.ART_ERROR),self.onDEBUG)
        tb.AddStretchableSpace()
        tb.Realize() 

        # --- Status bar
        self.statusbar=self.CreateStatusBar(3, style=0)
        self.statusbar.SetStatusWidths([200, -1, 70])

        # --- Main Panel and Notebook
        self.MainPanel = wx.Panel(self)
        #self.MainPanel = wx.Panel(self, style=wx.RAISED_BORDER)
        #self.MainPanel.SetBackgroundColour((200,0,0))

        #self.nb = wx.Notebook(self.MainPanel)
        #self.nb.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_change)


        sizer = wx.BoxSizer()
        #sizer.Add(self.nb, 1, flag=wx.EXPAND)
        self.MainPanel.SetSizer(sizer)

        # --- Drag and drop
        dd = FileDropTarget(self)
        self.SetDropTarget(dd)

        # --- Main Frame (self)
        self.FrameSizer = wx.BoxSizer(wx.VERTICAL)
        slSep = wx.StaticLine(self, -1, size=wx.Size(-1,1), style=wx.LI_HORIZONTAL)
        self.FrameSizer.Add(slSep         ,0, flag=wx.EXPAND|wx.BOTTOM,border=0)
        self.FrameSizer.Add(self.MainPanel,1, flag=wx.EXPAND,border=0)
        self.SetSizer(self.FrameSizer)

        self.SetSize(self.data['windowSize'])
        self.Center()
        self.Show()
        self.Bind(wx.EVT_SIZE, self.OnResizeWindow)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # Shortcuts
        idFilter=wx.NewId()
        self.Bind(wx.EVT_MENU, self.onFilter, id=idFilter)

        accel_tbl = wx.AcceleratorTable(
                [(wx.ACCEL_CTRL,  ord('F'), idFilter )]
                )
        self.SetAcceleratorTable(accel_tbl)

    def onFilter(self,event):
        if hasattr(self,'selPanel'):
            self.selPanel.colPanel1.tFilter.SetFocus()
        event.Skip()

    def clean_memory(self,bReload=False):
        #print('Clean memory')
        # force Memory cleanup
        self.tabList.clean()
        if not bReload:
            if hasattr(self,'selPanel'):
                self.selPanel.clean_memory()
            if hasattr(self,'infoPanel'):
                self.infoPanel.clean()
            if hasattr(self,'plotPanel'):
                self.plotPanel.cleanPlot()
        gc.collect()

    def load_files(self, filenames=[], fileformats=None, bReload=False, bAdd=False):
        """ load multiple files, only trigger the plot at the end """
        if bReload:
            if hasattr(self,'selPanel'):
                self.selPanel.saveSelection() # TODO move to tables

        if not bAdd:
            self.clean_memory(bReload=bReload)


        if fileformats is None:
            fileformats=[None]*len(filenames)
        assert type(fileformats)==list, 'fileformats must be a list'
        assert len(fileformats)==len(filenames), 'fileformats and filenames must have the same lengths'

        # Sorting files in alphabetical order in base_filenames order
        base_filenames = [os.path.basename(f) for f in filenames]
        I = np.argsort(base_filenames)
        filenames   = list(np.array(filenames)[I])
        fileformats = list(np.array(fileformats)[I])
        #filenames = [f for __, f in sorted(zip(base_filenames, filenames))]

        # Load the tables
        warnList = self.tabList.load_tables_from_files(filenames=filenames, fileformats=fileformats, bAdd=bAdd)
        if bReload:
            # Restore formulas that were previously added
            for tab in self.tabList:
                if tab.raw_name in self.restore_formulas.keys():
                    for f in self.restore_formulas[tab.raw_name]:
                        tab.addColumnByFormula(f['name'], f['formula'], f['pos']-1)
            self.restore_formulas = {}
        # Display warnings
        for warn in warnList: 
            Warn(self,warn)
        # Load tables into the GUI
        if self.tabList.len()>0:
            self.load_tabs_into_GUI(bReload=bReload, bAdd=bAdd, bPlot=True)

    def load_df(self, df, name=None, bAdd=False, bPlot=True):
        if bAdd:
            self.tabList.append(Table(data=df, name=name))
        else:
            self.tabList = TableList( [Table(data=df, name=name)] )
        self.load_tabs_into_GUI(bAdd=bAdd, bPlot=bPlot)
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(SEL_MODES_ID[self.comboMode.GetSelection()])

    def load_dfs(self, dfs, names, bAdd=False):
        self.tabList.from_dataframes(dataframes=dfs, names=names, bAdd=bAdd)
        self.load_tabs_into_GUI(bAdd=bAdd, bPlot=True)
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(SEL_MODES_ID[self.comboMode.GetSelection()])

    def load_tabs_into_GUI(self, bReload=False, bAdd=False, bPlot=True):
        if bAdd:
            if not hasattr(self,'selPanel'):
                bAdd=False

        if (not bReload) and (not bAdd):
            self.cleanGUI()
        self.Freeze()
        # Setting status bar
        self.setStatusBar()

        if bReload or bAdd:
            self.selPanel.update_tabs(self.tabList)
        else:
            mode = SEL_MODES_ID[self.comboMode.GetSelection()]
            #self.vSplitter = wx.SplitterWindow(self.nb)
            self.vSplitter = wx.SplitterWindow(self.MainPanel)
            self.selPanel = SelectionPanel(self.vSplitter, self.tabList, mode=mode, mainframe=self)
            self.tSplitter = wx.SplitterWindow(self.vSplitter)
            #self.tSplitter.SetMinimumPaneSize(20)
            self.infoPanel = InfoPanel(self.tSplitter, data=self.data['infoPanel'])
            self.plotPanel = PlotPanel(self.tSplitter, self.selPanel, self.infoPanel, self)
            self.tSplitter.SetSashGravity(0.9)
            self.tSplitter.SplitHorizontally(self.plotPanel, self.infoPanel)
            self.tSplitter.SetMinimumPaneSize(BOT_PANL)
            self.tSplitter.SetSashGravity(1)
            self.tSplitter.SetSashPosition(400)

            self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
            self.vSplitter.SetMinimumPaneSize(SIDE_COL[0])
            self.tSplitter.SetSashPosition(SIDE_COL[0])

            #self.nb.AddPage(self.vSplitter, "Plot")
            #self.nb.SendSizeEvent()

            sizer = self.MainPanel.GetSizer()
            sizer.Add(self.vSplitter, 1, flag=wx.EXPAND,border=0)
            self.MainPanel.SetSizer(sizer)
            self.FrameSizer.Layout()

            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.colPanel1.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.colPanel1.lbColumns)
            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.colPanel2.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.colPanel2.lbColumns)
            self.Bind(wx.EVT_COMBOBOX, self.onColSelectionChange, self.selPanel.colPanel3.comboX   )
            self.Bind(wx.EVT_LISTBOX , self.onColSelectionChange, self.selPanel.colPanel3.lbColumns)
            self.Bind(wx.EVT_LISTBOX , self.onTabSelectionChange, self.selPanel.tabPanel.lbTab)
            self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onSashChangeMain, self.vSplitter)

            self.selPanel.tabPanel.lbTab.Bind(wx.EVT_RIGHT_DOWN, self.OnTabPopup)

        # plot trigger
        if bPlot:
            self.mainFrameUpdateLayout()
            self.onColSelectionChange(event=None)
        try:
            self.Thaw()
        except:
            pass
        # Hack
        #self.onShowTool(tool='Filter')
        #self.onShowTool(tool='Resample')
        #self.onDataPlugin(toolName='Bin data')

    def setStatusBar(self, ISel=None):
        nTabs=self.tabList.len()
        if ISel is None:
            ISel = list(np.arange(nTabs))
        if nTabs<0:
            self.statusbar.SetStatusText('', 0) # Format
            self.statusbar.SetStatusText('', 1) # Filenames
            self.statusbar.SetStatusText('', 2) # Shape
        elif nTabs==1:
            self.statusbar.SetStatusText(self.tabList.get(0).fileformat_name,  0)
            self.statusbar.SetStatusText(self.tabList.get(0).filename  ,  1)
            self.statusbar.SetStatusText(self.tabList.get(0).shapestring, 2)
        elif len(ISel)==1:
            self.statusbar.SetStatusText(self.tabList.get(ISel[0]).fileformat_name , 0)
            self.statusbar.SetStatusText(self.tabList.get(ISel[0]).filename   , 1)
            self.statusbar.SetStatusText(self.tabList.get(ISel[0]).shapestring, 2)
        else:
            self.statusbar.SetStatusText(''                                   ,0) 
            self.statusbar.SetStatusText(", ".join(list(set([self.tabList.filenames[i] for i in ISel]))),1)
            self.statusbar.SetStatusText('',2)

    def renameTable(self, iTab, newName):
        oldName = self.tabList.renameTable(iTab, newName)
        self.selPanel.renameTable(iTab, oldName, newName)

    def sortTabs(self, method='byName'):
        self.tabList.sort(method=method)
        # Updating tables
        self.selPanel.update_tabs(self.tabList)
        # Trigger a replot
        self.onTabSelectionChange()


    def deleteTabs(self, I):
        self.tabList.deleteTabs(I)

        # Invalidating selections
        self.selPanel.tabPanel.lbTab.SetSelection(-1)
        # Until we have something better, we empty plot
        self.plotPanel.empty()
        self.infoPanel.empty()
        self.selPanel.clean_memory()
        # Updating tables
        self.selPanel.update_tabs(self.tabList)
        # Trigger a replot
        self.onTabSelectionChange()

    def exportTab(self, iTab):
        tab=self.tabList.get(iTab)
        default_filename=tab.basename +'.csv'
        with wx.FileDialog(self, "Save to CSV file",defaultFile=default_filename,
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
                #, wildcard="CSV files (*.csv)|*.csv",
            dlg.CentreOnParent()
            if dlg.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            tab.export(dlg.GetPath())

    def onShowTool(self, event=None, tool=''):
        """ 
        Show tool
        tool in 'Outlier', 'Filter', 'LogDec','FASTRadialAverage', 'Mask', 'CurveFitting'
        """
        if not hasattr(self,'plotPanel'):
            Error(self,'Plot some data first')
            return
        self.plotPanel.showTool(tool)

    def onDataPlugin(self, event=None, toolName=''):
        """ 
        Dispatcher to apply plugins to data:
          - simple plugins are directly exectued
          - plugins that are panels are sent over to plotPanel to show them
        TODO merge with onShowTool
        """
        if not hasattr(self,'plotPanel'):
            Error(self,'Plot some data first')
            return

        for thisToolName, function, isPanel in dataPlugins:
            if toolName == thisToolName:
                if isPanel:
                    panelClass = function(self, event, toolName) # getting panelClass
                    self.plotPanel.showToolPanel(panelClass)
                else:
                    function(self, event, toolName) # calling the data function
                return
        raise NotImplementedError('Tool: ',toolName)


    def onSashChangeMain(self,event=None):
        pass
        # doent work because size is not communicated yet
        #if hasattr(self,'selPanel'):
        #    print('ON SASH')
        #    self.selPanel.setEquiSash(event)

    def OnTabPopup(self,event):
        menu = TablePopup(self,self.selPanel.tabPanel.lbTab)
        self.PopupMenu(menu, event.GetPosition())
        menu.Destroy()

    def onTabSelectionChange(self,event=None):
        # TODO This can be cleaned-up
        ISel=self.selPanel.tabPanel.lbTab.GetSelections()
        if len(ISel)>0:
            # Letting seletion panel handle the change
            self.selPanel.tabSelectionChanged()
            # Update of status bar
            self.setStatusBar(ISel)
            # Trigger the colSelection Event
            self.onColSelectionChange(event=None)

    def onColSelectionChange(self,event=None):
        if hasattr(self,'plotPanel'):
            # Letting selection panel handle the change
            self.selPanel.colSelectionChanged()
            # Redrawing
            self.plotPanel.load_and_draw()
            # --- Stats trigger
            #self.showStats()

    def redraw(self):
        if hasattr(self,'plotPanel'):
            self.plotPanel.load_and_draw()
#     def showStats(self):
#         self.infoPanel.showStats(self.plotPanel.plotData,self.plotPanel.pltTypePanel.plotType())

    def onExit(self, event):
        self.Close() 

    def onClose(self, event):
        saveAppData(self, self.data)
        event.Skip()

    def cleanGUI(self, event=None):
        if hasattr(self,'plotPanel'):
            del self.plotPanel
        if hasattr(self,'selPanel'):
            del self.selPanel
        if hasattr(self,'infoPanel'):
            del self.infoPanel
        #self.deletePages()
        try:
            self.MainPanel.GetSizer().Clear(delete_windows=True) # Delete Windows
        except:
            self.MainPanel.GetSizer().Clear()
        self.FrameSizer.Layout()
        gc.collect()

    def onSave(self, event=None):
        # using the navigation toolbar save functionality
        self.plotPanel.navTB.save_figure()

    def onAbout(self, event=None):
        defaultDir = weio.defaultUserDataDir() # TODO input file options
        About(self,PROG_NAME+' '+PROG_VERSION+'\n\n'
                'pyDatView config file:\n     {}\n'.format(configFilePath())+
                'weio data directory:     \n     {}\n'.format(os.path.join(defaultDir,'weio'))+
                '\n\nVisit http://github.com/ebranlard/pyDatView for documentation.')

    def onReset (self, event=None):
        configFile = configFilePath()
        result = YesNo(self,
                'The options of pyDatView will be reset to default.\nThe changes will be noticeable the next time you open pyDatView.\n\n'+
                'This action will overwrite the user settings file:\n   {}\n\n'.format(configFile)+
                'pyDatView will then close.\n\n'
                'Are you sure you want to continue?', caption = 'Reset settings?')
        if result:
            try:
                os.remove(configFile)
            except:
                pass
            self.data = defaultAppData(self)
            self.datareset = True
            self.onExit(event=None)

    def onReload(self, event=None):
        filenames, fileformats = self.tabList.filenames_and_formats
        if len(filenames)>0:
            # Save formulas to restore them after reload with sorted tabs
            self.restore_formulas = {}
            for tab in self.tabList._tabs:
                f = tab.formulas # list of dict('pos','formula','name')
                f = sorted(f, key=lambda k: k['pos']) # Sort formulae by position in list of formua
                self.restore_formulas[tab.raw_name]=f # we use raw_name as key
            # Actually load files (read and add in GUI)
            self.load_files(filenames, fileformats=fileformats, bReload=True,bAdd=False)
        else:
           Error(self,'Open one or more file first.')

    def onDEBUG(self, event=None):
        #self.clean_memory()
        self.plotPanel.ctrlPanel.Refresh()
        self.plotPanel.cb_sizer.ForceRefresh()

    def onExport(self, event=None):
        ISel=[]
        try:
            ISel = self.selPanel.tabPanel.lbTab.GetSelections()
        except:
            pass
        if len(ISel)>0:
            self.exportTab(ISel[0])
        else:
           Error(self,'Open a file and select a table first.')

    def onLoad(self, event=None):
        self.selectFile(bAdd=False)

    def onAdd(self, event=None):
        self.selectFile(bAdd=self.tabList.len()>0)

    def selectFile(self,bAdd=False):
        # --- File Format extension
        iFormat=self.comboFormats.GetSelection()
        sFormat=self.comboFormats.GetStringSelection()
        if iFormat==0: # auto-format
            Format = None
            #wildcard = 'all (*.*)|*.*'
            wildcard='|'.join([n+'|*'+';*'.join(e) for n,e in zip(self.FILE_FORMATS_NAMEXT,self.FILE_FORMATS_EXTENSIONS)])
            #wildcard = sFormat + extensions+'|all (*.*)|*.*'
        else:
            Format = self.FILE_FORMATS[iFormat-1]
            extensions = '|*'+';*'.join(self.FILE_FORMATS[iFormat-1].extensions)
            wildcard = sFormat + extensions+'|all (*.*)|*.*'

        with wx.FileDialog(self, "Open file", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as dlg:
            #other options: wx.CHANGE_DIR
            #dlg.SetSize((100,100))
            #dlg.Center()
           if dlg.ShowModal() == wx.ID_CANCEL:
               return     # the user changed their mind
           filenames = dlg.GetPaths()
           self.load_files(filenames,fileformats=[Format]*len(filenames),bAdd=bAdd)

    def onModeChange(self, event=None):
        if hasattr(self,'selPanel'):
            self.selPanel.updateLayout(SEL_MODES_ID[self.comboMode.GetSelection()])
        self.mainFrameUpdateLayout()
        # --- Trigger to check number of columns
        self.onTabSelectionChange()

    def mainFrameUpdateLayout(self, event=None):
        if hasattr(self,'selPanel'):
            nWind=self.selPanel.splitter.nWindows
            if self.Size[0]<=800:
                sash=SIDE_COL[nWind]
            else:
                sash=SIDE_COL_LARGE[nWind]
            self.resizeSideColumn(sash)

    def OnResizeWindow(self, event):
        try:
            self.mainFrameUpdateLayout()
            self.Layout()
        except:
            pass
        # NOTE: doesn't work...
        #if hasattr(self,'plotPanel'):
            # Subplot spacing changes based on figure size
            #print('>>> RESIZE WINDOW')
            #self.redraw()  

    # --- Side column
    def resizeSideColumn(self,width):
        # To force the replot we do an epic unsplit/split...
        #self.vSplitter.Unsplit()
        #self.vSplitter.SplitVertically(self.selPanel, self.tSplitter)
        self.vSplitter.SetMinimumPaneSize(width)
        self.vSplitter.SetSashPosition(width)
        #self.selPanel.splitter.setEquiSash()

    # --- NOTEBOOK 
    #def deletePages(self):
    #    for index in reversed(range(self.nb.GetPageCount())):
    #        self.nb.DeletePage(index)
    #    self.nb.SendSizeEvent()
    #    gc.collect()
    #def on_tab_change(self, event=None):
    #    page_to_select = event.GetSelection()
    #    wx.CallAfter(self.fix_focus, page_to_select)
    #    event.Skip(True)
    #def fix_focus(self, page_to_select):
    #    page = self.nb.GetPage(page_to_select)
    #    page.SetFocus()

#----------------------------------------------------------------------
def MyExceptionHook(etype, value, trace):
    """
    Handler for all unhandled exceptions.
    :param `etype`: the exception type (`SyntaxError`, `ZeroDivisionError`, etc...);
    :type `etype`: `Exception`
    :param string `value`: the exception error message;
    :param string `trace`: the traceback header, if any (otherwise, it prints the
     standard Python header: ``Traceback (most recent call last)``.
    """
    from wx._core import wxAssertionError
    # Printing exception
    traceback.print_exception(etype, value, trace)
    if etype==wxAssertionError:
        if wx.Platform == '__WXMAC__':
            # We skip these exceptions on macos (likely bitmap size 0)
            return
    # Then showing to user the last error
    frame = wx.GetApp().GetTopWindow()
    tmp = traceback.format_exception(etype, value, trace)
    if tmp[-1].find('Exception: Error:')==0:
        Error(frame,tmp[-1][18:])
    elif tmp[-1].find('Exception: Warn:')==0:
        Warn(frame,tmp[-1][17:])
    else:
        exception = 'The following exception occured:\n\n'+ tmp[-1]  + '\n'+tmp[-2].strip()
        Error(frame,exception)
    try:
        frame.Thaw() # Make sure any freeze event is stopped
    except:
        pass

# --------------------------------------------------------------------------------}
# --- Tests 
# --------------------------------------------------------------------------------{
def test(filenames=None):
    if filenames is not None:
        app = wx.App(False)
        frame = MainFrame()
        frame.load_files(filenames,fileformats=None)
        return
 
# --------------------------------------------------------------------------------}
# --- Wrapped WxApp
# --------------------------------------------------------------------------------{
class MyWxApp(wx.App):
    def __init__(self, redirect=False, filename=None):
        try:
            wx.App.__init__(self, redirect, filename)
        except:
            if wx.Platform == '__WXMAC__':
                #msg = """This program needs access to the screen.
                #          Please run with 'pythonw', not 'python', and only when you are logged
                #          in on the main display of your Mac."""
               msg= """
MacOS Error:
  This program needs access to the screen. Please run with a
  Framework build of python, and only when you are logged in
  on the main display of your Mac.

pyDatView help:
  You see the error above because you are using a Mac and 
  the python executable you are using does not have access to
  your screen. This is a Mac issue, not a pyDatView issue.
  Instead of calling 'python pyDatView.py', you need to find
  another python and do '/path/python pyDatView.py'
  You can try './pythonmac pyDatView.py', a script provided
  in this repository to detect the path (in some cases)
  
  You can find additional help in the file 'README.md'.
  
  For quick reference, here are some typical cases:
  - Your python was installed with 'brew', then likely use   
       /usr/lib/Cellar/python/XXXXX/Frameworks/python.framework/Versions/XXXX/bin/pythonXXX;
  - Your python is an anaconda python, use something like:;
       /anaconda3/bin/python.app   (NOTE: the '.app'!
  - You are using a python 2 version, you can use the system one:
       /Library/Frameworks/Python.framework/Versions/XXX/bin/pythonXXX
       /System/Library/Frameworks/Python.framework/Versions/XXX/bin/pythonXXX
"""

            elif wx.Platform == '__WXGTK__':
                msg ="""
Error:
  Unable to access the X Display, is $DISPLAY set properly?

pyDatView help:
  You are probably running this application on a server accessed via ssh.
  Use `ssh -X` or `ssh -Y` to access the server. 
  Else, try setting up $DISPLAY before doing the ssh connection.
"""
            else:
                msg = 'Unable to create GUI' # TODO: more description is needed for wxMSW...
            raise SystemExit(msg)

# --------------------------------------------------------------------------------}
# --- Mains 
# --------------------------------------------------------------------------------{
def showApp(firstArg=None,dataframe=None,filenames=[]):
    """
    The main function to start the data frame GUI.
    """
    app = MyWxApp(False)
    frame = MainFrame()
    # Optional first argument
    if firstArg is not None:
        if isinstance(firstArg,list):
            filenames=firstArg
        elif isinstance(firstArg,str):
            filenames=[firstArg]
        elif isinstance(firstArg, pd.DataFrame):
            dataframe=firstArg
    #
    if (dataframe is not None) and (len(dataframe)>0):
        #import time
        #tstart = time.time()
        frame.load_df(dataframe)
        #tend = time.time()
        #print('PydatView time: ',tend-tstart)
    elif len(filenames)>0:
        frame.load_files(filenames, fileformats=None)
    app.MainLoop()

def cmdline():
    if len(sys.argv)>1:
        pydatview(filename=sys.argv[1])
    else:
        pydatview()
