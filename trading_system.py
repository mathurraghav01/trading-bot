# backend/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime
import asyncio
import random
import uvicorn
import json

app = FastAPI()

# Mock trading data
symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
current_prices = {symbol: round(random.uniform(100, 500), 2) for symbol in symbols}

# Store WebSocket connections
connections = []

class TradingBot:
    def __init__(self):
        self.balance = 10000
        self.portfolio = {symbol: 0 for symbol in symbols}
        self.trade_history = []
    
    async def execute_trade(self, symbol, action):
        price = current_prices[symbol]
        amount = random.randint(1, 5)
        cost = price * amount
        
        if action == "BUY" and self.balance >= cost:
            self.balance -= cost
            self.portfolio[symbol] += amount
            trade = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "action": action,
                "price": price,
                "quantity": amount,
                "status": "EXECUTED"
            }
        elif action == "SELL" and self.portfolio[symbol] >= amount:
            self.balance += cost
            self.portfolio[symbol] -= amount
            trade = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "action": action,
                "price": price,
                "quantity": amount,
                "status": "EXECUTED"
            }
        else:
            trade = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "action": action,
                "price": price,
                "quantity": amount,
                "status": "FAILED"
            }
        
        self.trade_history.append(trade)
        return trade

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <html>
        <head>
            <title>Trading Bot Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { display: flex; }
                .panel { margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                #prices { width: 30%; }
                #trades { width: 40%; }
                #portfolio { width: 30%; }
                .success { color: green; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1>Automated Trading Bot</h1>
            <div class="container">
                <div id="prices" class="panel">
                    <h2>Current Prices</h2>
                    <div id="price-data"></div>
                </div>
                <div id="trades" class="panel">
                    <h2>Trade History</h2>
                    <div id="trade-data"></div>
                </div>
                <div id="portfolio" class="panel">
                    <h2>Portfolio</h2>
                    <div id="portfolio-data"></div>
                </div>
            </div>
            <script>
                const ws = new WebSocket(`ws://${window.location.host}/ws`);
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'prices') {
                        document.getElementById('price-data').innerHTML = 
                            data.prices.map(p => `${p.symbol}: $${p.price}`).join('<br>');
                    }
                    if (data.type === 'trade') {
                        const trade = data.trade;
                        const statusClass = trade.status === 'EXECUTED' ? 'success' : 'error';
                        document.getElementById('trade-data').innerHTML = 
                            `[${trade.time}] ${trade.action} ${trade.quantity} ${trade.symbol} @ $${trade.price} 
                            <span class="${statusClass}">${trade.status}</span><br>` + 
                            document.getElementById('trade-data').innerHTML;
                    }
                    if (data.type === 'portfolio') {
                        document.getElementById('portfolio-data').innerHTML = 
                            `Balance: $${data.balance.toFixed(2)}<br>` +
                            data.portfolio.map(p => `${p.symbol}: ${p.quantity} shares`).join('<br>');
                    }
                };
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
            # Update prices every 2 seconds for visualization
            for symbol in symbols:
                current_prices[symbol] = round(current_prices[symbol] * random.uniform(0.99, 1.01), 2)
            
            # Send price updates
            price_data = [{"symbol": s, "price": p} for s, p in current_prices.items()]
            await websocket.send_json({"type": "prices", "prices": price_data})
            
            # Execute trade every 2 minutes (120 seconds)
            if int(datetime.now().timestamp()) % 120 == 0:
                symbol = random.choice(symbols)
                action = random.choice(["BUY", "SELL"])
                trade = await bot.execute_trade(symbol, action)
                await websocket.send_json({"type": "trade", "trade": trade})
                
                # Send portfolio update
                portfolio_data = [{"symbol": s, "quantity": q} for s, q in bot.portfolio.items() if q > 0]
                await websocket.send_json({
                    "type": "portfolio",
                    "balance": bot.balance,
                    "portfolio": portfolio_data
                })
            
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        connections.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)