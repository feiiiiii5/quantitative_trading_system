# Quantitative Trading System

A professional quantitative trading platform with backtesting, risk management, and algorithmic trading capabilities.

## Features

- **Backtesting Engine**: Event-driven and vectorized backtesting with comprehensive performance analytics
- **Risk Management**: Real-time risk monitoring, VaR calculation, and portfolio optimization
- **Strategy Development**: Multiple built-in strategies with customization support
- **Market Data**: Real-time and historical market data integration
- **Web Dashboard**: Modern React-based dashboard for monitoring and control

## Tech Stack

### Backend
- Python 3.11+
- FastAPI - Web framework
- Pandas/Polars - Data processing
- NumPy/SciPy - Scientific computing
- scikit-learn - Machine learning
- DuckDB - Analytical database

### Frontend
- React 18 with TypeScript
- Zustand - State management
- Vite - Build tool
- Tailwind CSS - Styling

### Infrastructure
- Docker & Kubernetes - Containerization
- gRPC - Service communication
- Redis - Caching
- ClickHouse - Time series storage

## Project Structure

```
.
├── api/                    # FastAPI routes and middleware
├── core/                   # Core trading engine modules
├── frontend/               # React dashboard
├── services/               # Microservices (AI, Risk, etc.)
├── proto/                  # gRPC protocol definitions
├── libs/                   # Shared libraries
├── tests/                  # Test suite
├── deploy/                 # Deployment configurations
└── docs/                   # Documentation
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional)

### Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend && npm test
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License
