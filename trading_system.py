# backend/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import asyncio
import random
import uvicorn
import json
import numpy as np
import pandas as pd
from ta import add_all_ta_features
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
current_prices = {symbol: round(random.uniform(100, 500), 2) for symbol in symbols}
price_history = {symbol: [] for symbol in symbols}
connections = []

class TradingBot:
    def __init__(self):
        self.balance = 10000
        self.portfolio = {symbol: {"shares": 0, "avg_price": 0} for symbol in symbols}
        self.trade_history = []
        self.indicators = {}
    
    def calculate_indicators(self, symbol):
        if len(price_history[symbol]) < 20:
            return None
        
        df = pd.DataFrame(price_history[symbol][-50:], columns=['close'])
        
        # Calculate technical indicators
        rsi = RSIIndicator(df['close'], window=14).rsi().iloc[-1]
        macd = MACD(df['close']).macd_diff().iloc[-1]
        ema20 = EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1]
        ema50 = EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1]
        bb = BollingerBands(df['close'])
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        
        self.indicators[symbol] = {
            "rsi": round(rsi, 2),
            "macd": round(macd, 2),
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2)
        }
        return self.indicators[symbol]
    
    async def execute_strategy(self, symbol):
        current_price = current_prices[symbol]
        indicators = self.calculate_indicators(symbol)
        if not indicators:
            return None
        
        # Mean Reversion Strategy (Bollinger Bands)
        if current_price < indicators["bb_lower"] and indicators["rsi"] < 30:
            return "BUY"
        elif current_price > indicators["bb_upper"] and indicators["rsi"] > 70:
            return "SELL"
        
        # Trend Following (MACD + EMA)
        elif indicators["macd"] > 0 and indicators["ema20"] > indicators["ema50"]:
            return "BUY"
        elif indicators["macd"] < 0 and indicators["ema20"] < indicators["ema50"]:
            return "SELL"
        
        return None
    
    async def execute_trade(self, symbol, action):
        price = current_prices[symbol]
        max_shares = min(5, int(self.balance / price)) if action == "BUY" else self.portfolio[symbol]["shares"]
        
        if max_shares <= 0:
            return None
        
        shares = random.randint(1, max_shares)
        cost = price * shares
        
        if action == "BUY":
            self.balance -= cost
            total_shares = self.portfolio[symbol]["shares"] + shares
            self.portfolio[symbol]["avg_price"] = (
                (self.portfolio[symbol]["avg_price"] * self.portfolio[symbol]["shares"] + cost) / total_shares
            )
            self.portfolio[symbol]["shares"] = total_shares
        else:
            self.balance += cost
            self.portfolio[symbol]["shares"] -= shares
        
        trade = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "symbol": symbol,
            "action": action,
            "price": price,
            "quantity": shares,
            "status": "EXECUTED",
            "pnl": self.get_pnl(symbol, price) if action == "SELL" else None
        }
        
        self.trade_history.append(trade)
        return trade
    
    def get_pnl(self, symbol, current_price):
        if self.portfolio[symbol]["shares"] == 0:
            return 0
        return (current_price - self.portfolio[symbol]["avg_price"]) * self.portfolio[symbol]["shares"]

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <html>
        <head>
            <title>Advanced Trading Bot</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                .positive { color: #10B981; }
                .negative { color: #EF4444; }
                .grid-container {
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    grid-gap: 1rem;
                }
                @media (max-width: 1024px) {
                    .grid-container { grid-template-columns: 1fr; }
                }
            </style>
        </head>
        <body class="bg-gray-100 text-gray-900">
            <div class="container mx-auto px-4 py-8">
                <header class="mb-8">
                    <h1 class="text-3xl font-bold text-blue-600">
                        <i class="fas fa-robot mr-2"></i> Algorithmic Trading Bot
                    </h1>
                    <p class="text-gray-600">Real-time trading with advanced strategies</p>
                </header>
                
                <div class="grid-container">
                    <!-- Market Data Panel -->
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-xl font-semibold mb-4 border-b pb-2">
                            <i class="fas fa-chart-line mr-2"></i>Market Data
                        </h2>
                        <div id="price-data" class="space-y-2"></div>
                        <canvas id="priceChart" class="mt-4"></canvas>
                    </div>
                    
                    <!-- Trading Panel -->
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-xl font-semibold mb-4 border-b pb-2">
                            <i class="fas fa-exchange-alt mr-2"></i>Trading Activity
                        </h2>
                        <div id="trade-data" class="space-y-2 max-h-96 overflow-y-auto"></div>
                    </div>
                    
                    <!-- Portfolio Panel -->
                    <div class="bg-white rounded-lg shadow p-6">
                        <h2 class="text-xl font-semibold mb-4 border-b pb-2">
                            <i class="fas fa-wallet mr-2"></i>Portfolio
                        </h2>
                        <div id="portfolio-data"></div>
                        <div id="indicators" class="mt-4"></div>
                    </div>
                </div>
            </div>
            
            <script>
                const ws = new WebSocket(`ws://${window.location.host}/ws`);
                const priceChart = new Chart(
                    document.getElementById('priceChart'),
                    { type: 'line', data: { datasets: [] } }
                );
                
                const colors = {
                    AAPL: 'rgba(75, 192, 192, 1)',
                    GOOGL: 'rgba(54, 162, 235, 1)',
                    MSFT: 'rgba(255, 99, 132, 1)',
                    AMZN: 'rgba(255, 159, 64, 1)',
                    TSLA: 'rgba(153, 102, 255, 1)'
                };
                
                let chartData = {};
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'prices') {
                        // Update price display
                        document.getElementById('price-data').innerHTML = data.prices.map(p => `
                            <div class="flex justify-between items-center">
                                <span class="font-medium">${p.symbol}</span>
                                <span class="font-bold">$${p.price.toFixed(2)}</span>
                                <span class="text-sm ${p.change >= 0 ? 'positive' : 'negative'}">
                                    ${p.change >= 0 ? '+' : ''}${p.change.toFixed(2)}%
                                </span>
                            </div>
                        `).join('');
                        
                        // Update chart
                        updateChart(data.prices);
                    }
                    
                    if (data.type === 'trade') {
                        const trade = data.trade;
                        const tradeElement = document.createElement('div');
                        tradeElement.className = `p-3 rounded-lg ${trade.status === 'EXECUTED' ? 'bg-green-50' : 'bg-red-50'}`;
                        tradeElement.innerHTML = `
                            <div class="flex justify-between items-center">
                                <span class="font-medium ${trade.action === 'BUY' ? 'text-green-600' : 'text-red-600'}">
                                    ${trade.action} ${trade.quantity} ${trade.symbol}
                                </span>
                                <span class="text-sm">@ $${trade.price.toFixed(2)}</span>
                            </div>
                            <div class="flex justify-between text-xs mt-1">
                                <span>${trade.time}</span>
                                <span class="${trade.status === 'EXECUTED' ? 'text-green-600' : 'text-red-600'}">
                                    ${trade.status}${trade.pnl !== undefined ? ` | P&L: $${trade.pnl.toFixed(2)}` : ''}
                                </span>
                            </div>
                        `;
                        document.getElementById('trade-data').prepend(tradeElement);
                    }
                    
                    if (data.type === 'portfolio') {
                        document.getElementById('portfolio-data').innerHTML = `
                            <div class="mb-4">
                                <div class="text-2xl font-bold mb-1">$${data.balance.toFixed(2)}</div>
                                <div class="text-sm text-gray-500">Available Balance</div>
                            </div>
                            <div class="space-y-2">
                                ${data.portfolio.map(p => `
                                    <div class="flex justify-between items-center p-2 bg-gray-50 rounded">
                                        <span>${p.symbol}</span>
                                        <span class="font-medium">${p.quantity} shares</span>
                                        <span class="${p.unrealized >= 0 ? 'positive' : 'negative'}">
                                            $${p.unrealized.toFixed(2)}
                                        </span>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    }
                    
                    if (data.type === 'indicators') {
                        document.getElementById('indicators').innerHTML = `
                            <h3 class="font-medium mb-2">Technical Indicators</h3>
                            <div class="grid grid-cols-2 gap-2 text-sm">
                                ${Object.entries(data.indicators).map(([key, val]) => `
                                    <div class="bg-gray-50 p-2 rounded">
                                        <div class="text-gray-500">${key}</div>
                                        <div class="font-medium">${val}</div>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    }
                };
                
                function updateChart(prices) {
                    const now = new Date().toLocaleTimeString();
                    
                    prices.forEach(stock => {
                        if (!chartData[stock.symbol]) {
                            chartData[stock.symbol] = {
                                label: stock.symbol,
                                data: [],
                                borderColor: colors[stock.symbol],
                                tension: 0.1,
                                fill: false
                            };
                            priceChart.data.datasets.push(chartData[stock.symbol]);
                        }
                        
                        chartData[stock.symbol].data.push({
                            x: now,
                            y: stock.price
                        });
                        
                        // Keep only last 20 data points
                        if (chartData[stock.symbol].data.length > 20) {
                            chartData[stock.symbol].data.shift();
                        }
                    });
                    
                    priceChart.update();
                }
            </script>
        </body>
    </html>
    """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    bot = TradingBot()
    
    try:
        while True:
            # Update prices with more realistic movement
            for symbol in symbols:
                change = random.gauss(0, 0.5)  # Normal distribution
                current_prices[symbol] = round(current_prices[symbol] * (1 + change/100), 2)
                price_history[symbol].append(current_prices[symbol])
                
                # Keep history manageable
                if len(price_history[symbol]) > 100:
                    price_history[symbol].pop(0)
            
            # Send price updates
            price_data = [{
                "symbol": s,
                "price": p,
                "change": (p / price_history[s][-2] - 1) * 100 if len(price_history[s]) > 1 else 0
            } for s, p in current_prices.items()]
            
            await websocket.send_json({
                "type": "prices",
                "prices": price_data
            })
            
            # Execute strategies every 2 minutes
            if int(datetime.now().timestamp()) % 120 == 0:
                for symbol in symbols:
                    action = await bot.execute_strategy(symbol)
                    if action:
                        trade = await bot.execute_trade(symbol, action)
                        if trade:
                            await websocket.send_json({
                                "type": "trade",
                                "trade": trade
                            })
                
                # Send portfolio update
                portfolio_data = [{
                    "symbol": s,
                    "quantity": p["shares"],
                    "unrealized": (current_prices[s] - p["avg_price"]) * p["shares"] if p["shares"] > 0 else 0
                } for s, p in bot.portfolio.items() if p["shares"] > 0]
                
                await websocket.send_json({
                    "type": "portfolio",
                    "balance": bot.balance,
                    "portfolio": portfolio_data
                })
                
                # Send indicators for the first symbol
                if symbols:
                    indicators = bot.calculate_indicators(symbols[0])
                    if indicators:
                        await websocket.send_json({
                            "type": "indicators",
                            "symbol": symbols[0],
                            "indicators": indicators
                        })
            
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        connections.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
