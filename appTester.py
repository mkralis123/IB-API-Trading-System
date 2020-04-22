import sys
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import pyqtgraph as pg
from pyqtgraph import plot
from IBTradingApp import TradingApp
import numpy as np

from ibapi.contract import Contract

 
def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

qtCreatorFile = "IBTradingApp.ui" # Enter file here.
 
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)
 
class MyApp( QtWidgets.QMainWindow, Ui_MainWindow ):
    
    def __init__(self, *args, **kwargs):
        
        super(MyApp,self).__init__(*args,**kwargs)
#        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        
        self.connectbtn.clicked.connect(self.start)
        self.disconnectbtn.clicked.connect(self.stop)
        self.exitbtn.clicked.connect(self.close)
        self.stockInput.returnPressed.connect(self.onStockPressed)
        self.shortInput.returnPressed.connect(self.onShortPressed)
        self.longInput.returnPressed.connect(self.onLongPressed)
        

        headerLabels = ["Stock", "Buy/Sell?", "Price", "Quantity"]
        orderHeaderLabels = ["OrderId", "Buy/Sell?", "Status"]
        
        self.buyExecTable.setHorizontalHeaderLabels(headerLabels)
        self.sellExecTable.setHorizontalHeaderLabels(headerLabels)
        self.orderStatusTable.setHorizontalHeaderLabels(orderHeaderLabels)
        
        self.orderStatusTable.setRowCount(1)
        
        contract = Contract()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.primaryExchange = "NASDAQ"
        
        
        self.thread = WorkerThread(contract, 10, 3, 100)
        
        
        self.priceGraphWidget.addLegend(size = (10,10))
        self.data_line = self.priceGraphWidget.plot(self.thread.IBapp.times, self.thread.IBapp.prices, 
                                                    pen = 'b', name = 'Stock Price')
        self.long_line = self.priceGraphWidget.plot(self.thread.IBapp.times[self.thread.IBapp.long_window-1:],
                                                    moving_average(self.thread.IBapp.prices, self.thread.IBapp.long_window),
                                                    pen = 'r', name = 'Long Moving Average')
        self.small_line = self.priceGraphWidget.plot(self.thread.IBapp.times[self.thread.IBapp.short_window-1:],
                                                    moving_average(self.thread.IBapp.prices, self.thread.IBapp.short_window),
                                                    pen = 'g', name = 'Short Moving Average')
        self.priceGraphWidget.setLabel('left', 'Price', color = 'grey')
        self.priceGraphWidget.setLabel('bottom', 'Time Elapsed (s)', color = 'grey')
        
        
        self.stockPriceTimer = QtCore.QTimer()
        self.stockPriceTimer.setInterval(1000)
        self.stockPriceTimer.timeout.connect(self.update_plot_data)
        self.stockPriceTimer.start()
        
        self.buyTableTimer = QtCore.QTimer()
        self.buyTableTimer.setInterval(1000)
        self.buyTableTimer.timeout.connect(self.fillLongTable)
        self.buyTableTimer.start()
        
        self.shortTableTimer = QtCore.QTimer()
        self.shortTableTimer.setInterval(1000)
        self.shortTableTimer.timeout.connect(self.fillShortTable)
        self.shortTableTimer.start()
        
        self.histogramTimer = QtCore.QTimer()
        self.histogramTimer.setInterval(1000)
        self.histogramTimer.timeout.connect(self.fillHistogram)
        self.histogramTimer.start()
        
        self.posTimer = QtCore.QTimer()
        self.posTimer.setInterval(1000)
        self.posTimer.timeout.connect(self.checkPosition)
        self.posTimer.start()
        
        self.orderTimer = QtCore.QTimer()
        self.orderTimer.setInterval(1000)
        self.orderTimer.timeout.connect(self.updateOrder)
        self.orderTimer.start()

        
    def start(self):
        
        
        self.thread.start()
        
        
    def stop(self):
        
        self.thread.IBapp.reqGlobalCancel()
        self.thread.IBapp.done = True
        self.thread.IBapp.disconnect()
        
    def close(self):
        
        sys.exit() 
    
    def onStockPressed(self):
        
        self.thread.IBapp.contract.symbol = self.stockInput.text()
        
    def onShortPressed(self):
        
        self.thread.IBapp.short_window = int(self.shortInput.text())
        
    def onLongPressed(self):
        
        self.thread.IBapp.long_window = int(self.longInput.text())
        
    def update_plot_data(self):
        
        self.data_line.setData(self.thread.IBapp.times,self.thread.IBapp.prices)
        self.long_line.setData(self.thread.IBapp.times[self.thread.IBapp.long_window-1:],
                               moving_average(self.thread.IBapp.prices, self.thread.IBapp.long_window))
        self.small_line.setData(self.thread.IBapp.times[self.thread.IBapp.short_window-1:],
                                moving_average(self.thread.IBapp.prices, self.thread.IBapp.short_window))
        
    def checkPosition(self):
        
        
        if self.thread.IBapp.pos:
            
            quantText = str(self.thread.IBapp.quantity)
            self.posLabel.setText("LONG " + quantText)
            
        else:
            
            self.posLabel.setText("NO POSITION")
        
    def fillHistogram(self):
        
        if len(self.thread.IBapp.long_trades) >0 and len(self.thread.IBapp.short_trades) > 0:
        
            if len(self.thread.IBapp.long_trades)==len(self.thread.IBapp.short_trades):
                
                values = self.thread.IBapp.short_trades-self.thread.IBapp.long_trades
                bins = np.linspace(1.5*min(values),1.5*max(values),40)           
            
            elif len(self.thread.IBapp.long_trades)>len(self.thread.IBapp.short_trades):
                
                values = self.thread.IBapp.short_trades-self.thread.IBapp.long_trades[:-1]
                bins = np.linspace(1.5*min(values),1.5*max(values),40) 
                
            elif len(self.thread.IBapp.long_trades)<len(self.thread.IBapp.short_trades):
                
                values = self.thread.IBapp.short_trades[1:]-self.thread.IBapp.long_trades
                bins = np.linspace(1.5*min(values),1.5*max(values),40) 
        
            self.tradeDistWidget.canvas.axes.clear()
            self.tradeDistWidget.canvas.axes.hist(values, bins)                
            self.tradeDistWidget.canvas.axes.set_ylabel("Frequency")
            self.tradeDistWidget.canvas.axes.set_xlabel("Trade Profit ($)")
            self.tradeDistWidget.canvas.draw()
        
        else:
            
            bins = np.linspace(-10,10,40)
            values = np.array([])
            
            self.tradeDistWidget.canvas.axes.clear()
            self.tradeDistWidget.canvas.axes.hist(values, bins)                
            self.tradeDistWidget.canvas.axes.set_ylabel("Frequency")
            self.tradeDistWidget.canvas.axes.set_xlabel("Trade Profit ($)")
            self.tradeDistWidget.canvas.draw()
            

        
    def fillLongTable(self):
        
        num_rows = len(self.thread.IBapp.long_trades)
        
        self.buyExecTable.setRowCount(num_rows)
        
        for row in range(num_rows):
            
            self.buyExecTable.setItem(row, 0, QtGui.QTableWidgetItem(self.thread.IBapp.contract.symbol))
            self.buyExecTable.setItem(row, 1, QtGui.QTableWidgetItem("BOUGHT"))
            self.buyExecTable.setItem(row, 2, QtGui.QTableWidgetItem(str(self.thread.IBapp.long_trades[row])))
            self.buyExecTable.setItem(row, 3, QtGui.QTableWidgetItem(str(self.thread.IBapp.quantity)))
            
    def fillShortTable(self):
        
        num_rows = len(self.thread.IBapp.short_trades)
        
        self.sellExecTable.setRowCount(num_rows)
        
        for row in range(num_rows):
            
            self.sellExecTable.setItem(row, 0, QtGui.QTableWidgetItem(self.thread.IBapp.contract.symbol))
            self.sellExecTable.setItem(row, 1, QtGui.QTableWidgetItem("SOLD"))
            self.sellExecTable.setItem(row, 2, QtGui.QTableWidgetItem(str(self.thread.IBapp.short_trades[row])))
            self.sellExecTable.setItem(row, 3, QtGui.QTableWidgetItem(str(self.thread.IBapp.quantity)))
    
    def updateOrder(self):
        
        
        self.orderStatusTable.setItem(0,0, QtGui.QTableWidgetItem(str(self.thread.IBapp.currentOrderId)))
        self.orderStatusTable.setItem(0,2, QtGui.QTableWidgetItem(self.thread.IBapp.currentOrderStatus))
        self.orderStatusTable.setItem(0,1, QtGui.QTableWidgetItem(self.thread.IBapp.currentOrderType))
    
    
    
class WorkerThread(QtCore.QThread):
    
    def __init__(self, contract, longwindow, shortwindow, quantity, parent = None):
        super(WorkerThread, self).__init__(parent)
        
        self.IBapp = TradingApp(contract, longwindow, shortwindow, quantity)
        
    def run(self):
        
        self.IBapp.connect("127.0.0.1", 7497, clientId=0)

        self.IBapp.reqMarketDataType(3)
        self.IBapp.reqMktData(1, self.IBapp.contract, "", False, False, [])
        self.IBapp.reqPositions()
        
        self.IBapp.run()
    
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())