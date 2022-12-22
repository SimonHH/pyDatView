import wx
import numpy as np
from pydatview.GUITools import GUIToolPanel, TOOL_BORDER
from pydatview.common import CHAR, Error, Info, pretty_num_short
from pydatview.common import DummyMainFrame
from pydatview.plotdata import PlotData
from pydatview.pipeline import PlotDataAction
import platform
# --------------------------------------------------------------------------------}
# --- Data
# --------------------------------------------------------------------------------{
_DEFAULT_DICT={
    'active':False, 
    'medianDeviation':5
}
# --------------------------------------------------------------------------------}
# --- Action
# --------------------------------------------------------------------------------{
def removeOutliersAction(label, mainframe=None, data=None):
    """
    Return an "action" for the current plugin, to be used in the pipeline.
    The action is also edited and created by the GUI Editor
    """
    if data is None:
        # NOTE: if we don't do copy below, we will end up remembering even after the action was deleted
        #       its not a bad feature, but we might want to think it through
        #       One issue is that "active" is kept in memory
        data=_DEFAULT_DICT
        data['active'] = False #<<< Important

    guiCallback=None
    if mainframe is not None:
        guiCallback = mainframe.redraw

    action = PlotDataAction(
            name             = label,
            plotDataFunction = removeOutliersXY,
            guiEditorClass   = RemoveOutliersToolPanel,
            guiCallback      = guiCallback,
            data             = data,
            mainframe        = mainframe
            )
    return action
# --------------------------------------------------------------------------------}
# --- Main method
# --------------------------------------------------------------------------------{
def removeOutliersXY(x, y, opts):
    from pydatview.tools.signal_analysis import reject_outliers
    try:
        x, y = reject_outliers(y, x, m=opts['medianDeviation'])
    except:
        raise Exception('Warn: Outlier removal failed. Desactivate it or use a different signal. ')
    return x, y

# --------------------------------------------------------------------------------}
# --- GUI to edit plugin and control the action
# --------------------------------------------------------------------------------{
class RemoveOutliersToolPanel(GUIToolPanel):

    def __init__(self, parent, action):
        GUIToolPanel.__init__(self, parent)

        # --- Creating "Fake data" for testing only!
        if action is None:
            print('[WARN] Calling GUI without an action! Creating one.')
            mainframe = DummyMainFrame(parent)
            action = binningAction(label='dummyAction', mainframe=mainframe)

        # --- Data
        self.parent = parent # parent is GUIPlotPanel
        self.mainframe = action.mainframe
        self.data = action.data
        self.action = action
        # --- GUI elements
        self.btClose = self.getBtBitmap(self,'Close','close',self.destroy)
        self.btApply = self.getToggleBtBitmap(self,'Apply','cloud',self.onToggleApply)

        lb1 = wx.StaticText(self, -1, 'Median deviation:')
#         self.tMD = wx.TextCtrl(self, wx.ID_ANY,, size = (30,-1), style=wx.TE_PROCESS_ENTER)
        self.tMD = wx.SpinCtrlDouble(self, value='11', size=wx.Size(60,-1))
        self.tMD.SetValue(5)
        self.tMD.SetRange(0.0, 1000)
        self.tMD.SetIncrement(0.5)
        self.tMD.SetDigits(1)
        self.lb = wx.StaticText( self, -1, '')
        
        # --- Layout        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.btClose,0,flag = wx.LEFT|wx.CENTER,border = 1)
        self.sizer.Add(self.btApply,0,flag = wx.LEFT|wx.CENTER,border = 5)
        self.sizer.Add(lb1         ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        self.sizer.Add(self.tMD    ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        self.sizer.Add(self.lb     ,0,flag = wx.LEFT|wx.CENTER,border = 5)
        self.SetSizer(self.sizer)

        # --- Events
        self.Bind(wx.EVT_SPINCTRLDOUBLE, self.onParamChangeArrow, self.tMD)
        self.Bind(wx.EVT_TEXT_ENTER,     self.onParamChangeEnter, self.tMD)

        if platform.system()=='Windows':
            # See issue https://github.com/wxWidgets/Phoenix/issues/1762
            self.spintxt = self.tMD.Children[0]
            assert isinstance(self.spintxt, wx.TextCtrl)
            self.spintxt.Bind(wx.EVT_CHAR_HOOK, self.onParamChangeChar)
            
        # --- Init triggers
        self._Data2GUI()        
        self.onToggleApply(init=True)

    # --- Implementation specific

    # --- Bindings for plot triggers on parameters changes
    def onParamChange(self, event=None):
        self._GUI2Data()
        if self.data['active']:
            self.parent.load_and_draw() # Data will change

    def onParamChangeArrow(self, event):
        self.onParamChange()
        event.Skip()

    def onParamChangeEnter(self, event):
        self.onParamChange()
        event.Skip()

    def onParamChangeChar(self, event):
        event.Skip()  
        code = event.GetKeyCode()
        if code in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            #print(self.spintxt.Value)
            self.tMD.SetValue(self.spintxt.Value)
            self.onParamChangeEnter(event)

    # --- Table related
    # --- External Calls
    def cancelAction(self, redraw=True):
        """ do cancel the action"""
        self.lb.SetLabel('Click on "Apply" to remove outliers on the fly for all new plot.')
        self.btApply.SetLabel(CHAR['cloud']+' Apply')
        self.btApply.SetValue(False)
        self.data['active'] = False     
        if redraw:
            self.parent.load_and_draw() # Data will change based on plotData 

    # --- Fairly generic
    def _GUI2Data(self):
        self.data['medianDeviation'] = float(self.tMD.Value)

    def _Data2GUI(self):
        self.tMD.SetValue(self.data['medianDeviation'])

    def onToggleApply(self, event=None, init=False):

        if not init:
            self.data['active'] = not self.data['active']

        if self.data['active']:
            self._GUI2Data()
            self.lb.SetLabel('Outliers are now removed on the fly. Click "Clear" to stop.')
            self.btApply.SetLabel(CHAR['sun']+' Clear')
            self.btApply.SetValue(True)            
            # The action is now active we add it to the pipeline, unless it's already in it
            if self.mainframe is not None:
                self.mainframe.addAction(self.action, cancelIfPresent=True)
            if not init:
                self.parent.load_and_draw() # filter will be applied in plotData.py
        else:
            # We remove our action from the pipeline
            if not init:
                if self.mainframe is not None:
                    self.mainframe.removeAction(self.action)          
            self.cancelAction(redraw= not init)

