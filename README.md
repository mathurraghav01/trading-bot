# Algorithmic Trading Bot with Real-Time Dashboard

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)
![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS-38B2AC)
![WebSocket](https://img.shields.io/badge/Protocol-WebSocket-yellow)

A full-stack automated trading system featuring multi-strategy algorithms, real-time market simulation, and an interactive dashboard.

[![Demo](https://img.shields.io/badge/Live-Demo-red)](https://your-demo-link.com) 
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

![](https://github.com/yourusername/trading-bot/blob/main/screenshots/dashboard-preview.png?raw=true)

##  Key Features

- **Dual Trading Strategies**  
   Mean Reversion (Bollinger Bands + RSI)  
  Trend Following (MACD + EMA Crossover)  

- **Real-Time Dashboard**  
   Interactive price charts (Chart.js)  
   Color-coded trade execution log  
   Portfolio P&L tracking  

- **Technical Indicators**  
   RSI, MACD, EMA(20/50), Bollinger Bands  
   Simulated market with normal distribution  

- **Modern Tech Stack**  
   FastAPI backend with WebSocket streaming  
   Tailwind CSS responsive UI  
   TA-Lib powered analysis  

##  Quick Start

```bash
# Clone repo
git clone https://github.com/yourusername/algorithmic-trading-bot.git
cd algorithmic-trading-bot

# Install dependencies
pip install -r requirements.txt

# Launch server
uvicorn main:app --reload
