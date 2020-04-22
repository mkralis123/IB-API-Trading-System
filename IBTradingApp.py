from ibapi import wrapper
from ibapi import client
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.ticktype import TickTypeEnum
from ibapi.execution import ExecutionFilter

import numpy as np

import time

def avg(lst):
    
    return sum(lst)/len(lst)

"""
EWrapper is the class used for handling and processing the information
given by TWS. These functions can be overridden to create powerful
applications which is what is demonstrated below
"""
class TestWrapper(wrapper.EWrapper):
    
    def __init__(self):
        
        wrapper.EWrapper.__init__(self)

"""
EClient class is used to send messages to TWS through the IBAPI
"""    
class TestClient(client.EClient):
    
    def __init__(self,wrapper):
    
        client.EClient.__init__(self,wrapper)

"""
This is where the Trading Application is created. The class TradingApp
is inheriting the EClient and EWrapper class to take advantage of the
full functionality of the IBAPI

Functions from EWrapper get overridden to store critical information
regarding price, volume, time, etc.

The strategy currently being implemented here is a Moving Average
Crossover Strategy
"""         
class TradingApp(TestWrapper, TestClient):
    
    def __init__(self, contract, long_window, short_window, quantity):
        
        
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper = self)
        
        #Keeps track of how long the object as been running for
        self.current_time = time.time()
        
        #Take in user input for the length of the long window
        #and the short window as well as the size of the trades
        self.long_window = long_window
        self.short_window = short_window
        self.quantity = quantity
        
        #Create arrays to store price information as well as the 
        #time that information comes in. Very useful for plots
        self.prices = []
        self.times = []
        
        #Create arrays to store the prices that buys and sells
        #were placed at. Useful for tracking profit per trade
        self.long_trades = np.array([])
        self.short_trades = np.array([])
        
        #pos and noOpenOrders will both serve as a logical que
        #orders can only be placed if noOpenOrders is True
        self.pos = False
        self.noOpenOrders = True
        
        #Stores the current order ID, status, and type
        self.currentOrderStatus = ""
        self.currentOrderType = ""
        self.currentOrderId = int
        
        #Create array of all the executed order IDs. Useful for
        #not entering duplicate entries in the long_trades
        #and short_trades arrays
        self.executedOrderIds = []
        
        #dummy variable to keep requesting executions made within the day
        self.reqExecutionId = 0
        
        #Store the contract details of what is being traded
        self.contract = contract
    
    """
    Overridden function: error
    
    Print out messages regarding connection
    """
    def error(self, reqId, errorCode, errorString):
        
        print("Error: ", reqId, " ", errorCode, " ", errorString)
    
    """    
    Overridden function: marketDataType
    
    Print the market data type and the ID of the request    
    """
    def marketDataType(self, reqId: client.TickerId, marketDataType: int):
        
        super().marketDataType(reqId, marketDataType)
        print("MarketDataType. ReqId:", reqId, "Type:", marketDataType)
    
    """
    Overridden function: tickPrice
    
    After Market request in main, store price data and time data
    into the "self.prices" and "self.times" arrays
    
    Request current positions, orderIds, executions made over the day
    
    Finally, runs the strategy  
    """
    def tickPrice(self, reqId, tickType, price, attrib):
        
        #68 denotes the tickType of lastPrice
        if tickType == 68:
            
            self.prices.append(price), self.times.append(time.time()-self.current_time)

            self.reqPositions()
            self.reqIds(-1)
            self.run_strategy(self.prices, self.contract)
            self.reqExecutions(self.reqExecutionId, ExecutionFilter())
            self.reqExecutionId +=1
    
    """        
    Overridden function: position
    
    After requesting all positions, the application stores the 
    position information as a boolean variable to "self.pos" and 
    prints whether or not there is a long position
    """
    def position(self, account, contract, position, avgCost):
        
        if contract.symbol == self.contract.symbol:
            
            print("Positions. Symbol:", contract.symbol, "Position:", position, "Avg cost:", avgCost)
            
            if position > 0:
                self.pos = True
            else:
                self.pos = False
            
            print("Long Position?: ", self.pos)
    """
    Overridden function: nextValidId
    
    After the orderID request, the self.nextOrderId gets declared
    and stores the next valid order ID available to place orders with    
    """
    def nextValidId(self, orderId):
        
        self.nextOrderId = orderId
        print("NextValidId:", orderId)
    
    """
    Self Made Function: run_strategy
    
    Preforms the Moving Average Crossover Strategy
    
    At first, checks to make sure enough data is present to cover the long window
    Then checks if there are any current orders already been placed
    Then checks if there is already a long position held
    Then undergoes the strategy      
    """
    def run_strategy( self, prices, contract ):
    
        if len(prices)>=self.long_window and self.noOpenOrders:
        
            if self.pos:
                
                if avg(prices[-self.long_window:]) > avg(prices[-self.short_window:]):
                    
                    order = Order()
                    order.action = "SELL"
                    order.orderType = "MKT"
                    order.totalQuantity = 100
                    
                    #self.currentOrderId gets updated to the orderId that gets placed
                    self.currentOrderId = self.nextOrderId
                    self.placeOrder(self.nextOrderId, contract, order)
                    
            else:
                
                if avg(prices[-self.long_window:]) < avg(prices[-self.short_window:]):
                    
                    order = Order()
                    order.action = "BUY"
                    order.orderType = "MKT"
                    order.totalQuantity = 100
                    
                    #self.currentOrderId gets updated to the orderId that gets placed
                    self.currentOrderId = self.nextOrderId
                    self.placeOrder(self.nextOrderId, contract, order)
    """
    Overridden Function: orderStatus
    
    If an order gets placed in run_strategy then order status gets
    called and will print the following details
    
    The orderId of this order is saved in the TradingApp's
    attribute named self.currentOrderId
    
    Once checked, the status of the order can be analyzed
    
    If it has not been filled, then self.noOpenOrders will remain False
    until the status of that order is "Filled" 
    
    self.currentOrderStatus will be updated accordingly
    """              
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId,
                    parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        
        print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled)
        
        if orderId == self.currentOrderId:
            
            if status != "Filled":
                
                self.noOpenOrders = False
                self.currentOrderStatus = "Not Filled"
                
            else:
                
                self.noOpenOrders = True
                self.currentOrderStatus = "Filled"
        
        print("No Open Orders?: ", self.noOpenOrders)
    
    """
    Overridden Function: openOrder
    
    If an order is made in run_strategy then openOrder gets called and
    prints the following information
    
    self.currentOrderType is also stored to keep track of the most recent order
    """
    def openOrder(self, orderId, contract, order, orderState):
        
        print("Open Order. orderId:", orderId, "Symbol:", contract.symbol,
              "Order Type:", order.action)
        
        if orderId == self.currentOrderId:
            
            self.currentOrderType = order.action
    
    """
    Overridden Function: execDetails
        
    Once an execution happened or a request for execution information
    is sent, then execDetails gets called. Here it is overridden to gain
    details about the price executed at as well as whether it was a
    buy or sell.
    
    In order to not create duplicate executions, self.executedOrderIds
    stores all of the IDs of the executed orders. If the orderId of the
    execution is already in the self.executedOrderIds array then that
    information is ignored because it already has been stored
    """
    def execDetails(self, reqId, contract, execution):
        
        print("ExecDetails. OrderId:", execution.orderId, 
              "Symbol:", contract.symbol, "Execution Price:", execution.price)
        
        if (execution.orderId not in self.executedOrderIds):
            
            if (execution.side == "BOT") and (contract.symbol == self.contract.symbol):
                
                self.long_trades = np.insert(self.long_trades, len(self.long_trades), (execution.price))
                self.executedOrderIds.append(execution.orderId)
                
            elif (execution.side == "SLD") and (contract.symbol == self.contract.symbol):
                
                self.short_trades = np.insert(self.short_trades, len(self.short_trades), (execution.price))
                self.executedOrderIds.append(execution.orderId)