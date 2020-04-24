import sys
from PyQt5 import QtWidgets, QtCore, QtGui, uic
import pyqtgraph as pg
from pyqtgraph import plot
from IBTradingApp import TradingApp
import numpy as np

import time

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
        

        headerLabels = ["OrderID", "Stock", "Buy/Sell?", "Price", "Quantity"]
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
        
        
        self.Timer = QtCore.QTimer()
        self.Timer.setInterval(1000)
        self.Timer.timeout.connect(self.update_plot_data)
        self.Timer.timeout.connect(self.fillLongTable)
        self.Timer.timeout.connect(self.fillShortTable)
        self.Timer.timeout.connect(self.fillHistogram)
        self.Timer.timeout.connect(self.checkPosition)
        self.Timer.timeout.connect(self.updateOrder)
        self.Timer.timeout.connect(self.updateStats)
        self.Timer.start()            
            
        self.connectionTimer = QtCore.QTimer()
        self.connectionTimer.setInterval(5000)
        self.connectionTimer.timeout.connect(self.checkConn)
        self.connectionTimer.start()

        
    def start(self):
        
        
        self.thread.start()
        
        
    def stop(self):
        
        self.thread.IBapp.reqGlobalCancel()
        self.thread.IBapp.done = True
        self.thread.IBapp.disconnect()
        
        self.statusBar().showMessage("You have disconnected from TWS. All open orders have been cancelled")
        
    def close(self):
        
        sys.exit() 
        
    def checkConn(self):
        
        if self.thread.IBapp.isConnected():
            
            self.statusBar().showMessage("You are now connected to TWS, recieving market data now")
            self.connectionTimer.stop()
        
        else:
            
            self.statusBar().showMessage("Awaiting connection to TWS....")
        
    
    def onStockPressed(self):
        
        self.thread.IBapp.contract.symbol = self.stockInput.text()
        self.statusBar().showMessage("Stock has been entered")
        
    def onShortPressed(self):
        
        self.thread.IBapp.short_window = int(self.shortInput.text())
        self.statusBar().showMessage("Short Window has been entered")
        
    def onLongPressed(self):
        
        self.thread.IBapp.long_window = int(self.longInput.text())
        self.statusBar().showMessage("Long Window has been entered")
        
    def update_plot_data(self):
        
        self.data_line.setData(self.thread.IBapp.times,self.thread.IBapp.prices)
        self.long_line.setData(self.thread.IBapp.times[self.thread.IBapp.long_window-1:],
                               moving_average(self.thread.IBapp.prices, self.thread.IBapp.long_window))
        self.small_line.setData(self.thread.IBapp.times[self.thread.IBapp.short_window-1:],
                                moving_average(self.thread.IBapp.prices, self.thread.IBapp.short_window))
        
    def updateStats(self):
        
        tradeDist = self.thread.IBapp.tradeDist
        initialTime = self.thread.IBapp.current_time
        prices = np.asarray(self.thread.IBapp.prices)
        long_window = self.thread.IBapp.long_window
        short_window = self.thread.IBapp.short_window
        
        
        if len(prices) > 1 and len(prices) < short_window:
        
            self.currentPrice.setText(str(prices[-1]))
            
            mean_time_prices = (time.time()-initialTime)/len(prices)
            self.vol.setText(str(np.std(np.log(prices[1:]/prices[:-1]))*np.sqrt(7711200/mean_time_prices)))
            
        elif len(prices) < long_window and len(prices) > short_window:
            
            self.currentPrice.setText(str(prices[-1]))
            self.shortMA.setText(str(moving_average(prices, short_window)[-1]))
            
            mean_time_prices = (time.time()-initialTime)/len(prices)
            self.vol.setText(str(np.std(np.log(prices[1:]/prices[:-1]))*np.sqrt(7711200/mean_time_prices)))
        
        elif len(prices) > long_window:
            
            self.currentPrice.setText(str(prices[-1]))
            self.shortMA.setText(str(moving_average(prices, short_window)[-1]))
            self.longMA.setText(str(moving_average(prices, long_window)[-1]))
            
            mean_time_prices = (time.time()-initialTime)/len(prices)
            self.vol.setText(str(np.std(np.log(prices[1:]/prices[:-1]))*np.sqrt(7711200/mean_time_prices)))
        
        if len(tradeDist) > 0:
            
            self.totalProfit.setText(str(np.sum(tradeDist)))
            self.avgProfit.setText(str(np.mean(tradeDist)))
            self.std.setText(str(np.std(tradeDist)))
            self.maxProfit.setText(str(np.max(tradeDist)))
            self.minProfit.setText(str(np.min(tradeDist)))
    
    def checkPosition(self):
        
        
        if self.thread.IBapp.pos:
            
            quantText = str(self.thread.IBapp.quantity)
            self.posLabel.setText("LONG " + quantText)
            
        else:
            
            self.posLabel.setText("NO POSITION")
        
    def fillHistogram(self):
        
        tradeDist = self.thread.IBapp.tradeDist
        
        if len(tradeDist) > 0:
            
            bins = np.linspace(min(1.5*min(tradeDist),min(tradeDist) - 1.5*max(tradeDist)),
                               max(1.5*max(tradeDist),max(tradeDist) - 1.5*min(tradeDist)),30) 
            self.tradeDistWidget.canvas.axes.clear()
            self.tradeDistWidget.canvas.axes.hist(tradeDist, bins)                
            self.tradeDistWidget.canvas.axes.set_ylabel("Frequency")
            self.tradeDistWidget.canvas.axes.set_xlabel("Trade Profit ($)")
            self.tradeDistWidget.canvas.draw()
        
        else:
            
            bins = np.linspace(-10,10,40)
            self.tradeDistWidget.canvas.axes.clear()
            self.tradeDistWidget.canvas.axes.hist(tradeDist, bins)                
            self.tradeDistWidget.canvas.axes.set_ylabel("Frequency")
            self.tradeDistWidget.canvas.axes.set_xlabel("Trade Profit ($)")
            self.tradeDistWidget.canvas.draw()
            

        
    def fillLongTable(self):
        
        
        num_rows = np.shape(self.thread.IBapp.long_trades)[1]
        
        self.buyExecTable.setRowCount(num_rows)
        
        for row in range(num_rows):
            
            self.buyExecTable.setItem(row, 0, QtGui.QTableWidgetItem(str(int(self.thread.IBapp.long_trades[1,row]))))
            self.buyExecTable.setItem(row, 1, QtGui.QTableWidgetItem(self.thread.IBapp.contract.symbol))
            self.buyExecTable.setItem(row, 2, QtGui.QTableWidgetItem("BOUGHT"))
            self.buyExecTable.setItem(row, 3, QtGui.QTableWidgetItem(str(self.thread.IBapp.long_trades[0,row])))
            self.buyExecTable.setItem(row, 4, QtGui.QTableWidgetItem(str(self.thread.IBapp.quantity)))
            
    def fillShortTable(self):
        
        num_rows = np.shape(self.thread.IBapp.short_trades)[1]
        
        self.sellExecTable.setRowCount(num_rows)
        
        for row in range(num_rows):
            
            self.sellExecTable.setItem(row, 0, QtGui.QTableWidgetItem(str(int(self.thread.IBapp.short_trades[1,row]))))
            self.sellExecTable.setItem(row, 1, QtGui.QTableWidgetItem(self.thread.IBapp.contract.symbol))
            self.sellExecTable.setItem(row, 2, QtGui.QTableWidgetItem("SOLD"))
            self.sellExecTable.setItem(row, 3, QtGui.QTableWidgetItem(str(self.thread.IBapp.short_trades[0,row])))
            self.sellExecTable.setItem(row, 4, QtGui.QTableWidgetItem(str(self.thread.IBapp.quantity)))
    
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