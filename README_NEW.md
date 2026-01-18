# 🗺️ Google Maps Scraper

A production-grade Google Maps scraper with REST API interface. Extract business information including ratings, reviews, contact details, and star distribution breakdown.

## ✨ Features

- 🎯 **Complete Business Data**: Name, rating, review count, phone, email, website, address
- ⭐ **Star Distribution**: Breakdown of 1-5 star reviews
- 🌐 **REST API**: Full HTTP API with job management
- 🐳 **Docker Ready**: Easy deployment with Docker/Docker Compose
- 🔄 **Background Jobs**: Async scraping with progress tracking
- 📊 **Multiple Export Formats**: CSV and JSON
- 🛡️ **Anti-Detection**: Stealth browser configuration
- 📧 **Email Extraction**: Scrapes emails from company websites

## 📋 Data Fields

| Field | Description |
|-------|-------------|
| `business_name` | Business name |
| `rating` | Rating (1-5 stars) |
| `review_count` | Total number of reviews |
| `five_star` | Number of 5-star reviews |
| `four_star` | Number of 4-star reviews |
| `three_star` | Number of 3-star reviews |
| `two_star` | Number of 2-star reviews |
| `one_star` | Number of 1-star reviews |
| `phone` | Phone number |
| `email` | Email address |
| `website` | Website URL |
| `address` | Physical address |

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Start the API
docker-compose up -d

# API is now running at http://localhost:8000
```

### Option 2: Using Quick Start Script

```bash
chmod +x start.sh
./start.sh
```

### Option 3: Manual Python Setup

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run API server
python api.py

# Or run CLI version
python main.py --query "Coffee Shops in Cairo" --max-results 10
```

## 📡 API Usage

### Start a Scraping Job

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Restaurants in Cairo",
    "max_results": 20,
    "headless": true
  }'
```

Response:
```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Scraping job started..."
}
```

### Check Job Status

```bash
curl http://localhost:8000/status/a1b2c3d4
```

### Download Results

```bash
# As CSV
curl http://localhost:8000/download/a1b2c3d4 -o results.csv

# As JSON
curl http://localhost:8000/results/a1b2c3d4
```

## 📖 Full Documentation

- **API Guide**: See [API_GUIDE.md](./API_GUIDE.md) for complete API documentation
- **Swagger UI**: Visit `http://localhost:8000/docs` when server is running
- **Arabic Guide**: See [QUICK_START_AR.md](./QUICK_START_AR.md) for Arabic instructions

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/scrape` | POST | Start scraping job |
| `/status/{job_id}` | GET | Get job status |
| `/download/{job_id}` | GET | Download CSV |
| `/results/{job_id}` | GET | Get JSON results |
| `/jobs` | GET | List all jobs |
| `/job/{job_id}` | DELETE | Delete job |

## 💻 CLI Usage

```bash
# Basic usage
python main.py --query "Hotels in Cairo"

# Limit results
python main.py --query "Coffee Shops in Cairo" --max-results 10

# With browser visible (for debugging)
python main.py --query "Restaurants in Cairo" --no-headless

# Custom output file
python main.py --query "Real Estate in Cairo" --output data/results.csv
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
docker build -t google-maps-scraper .

# Run container
docker run -d \
  --name scraper-api \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  google-maps-scraper
```

### Docker Compose

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🌍 Server Deployment

### Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Deploy to Render

1. Push to GitHub
2. Connect to [render.com](https://render.com)
3. Select "Docker" as environment
4. Deploy!

### Deploy to VPS

```bash
# Copy files to server
scp -r . user@server:/path/to/app

# On server
cd /path/to/app
docker-compose up -d

# Open firewall port
sudo ufw allow 8000
```

## 📊 Example Response

```json
{
  "job_id": "a1b2c3d4",
  "total_results": 10,
  "results": [
    {
      "business_name": "Great Coffee Shop",
      "rating": 4.5,
      "review_count": 250,
      "five_star": 180,
      "four_star": 50,
      "three_star": 15,
      "two_star": 3,
      "one_star": 2,
      "phone": "+20123456789",
      "email": "info@coffee.com",
      "website": "https://greatcoffee.com",
      "address": "123 Main St, Cairo, Egypt"
    }
  ]
}
```

## 🛠️ Tech Stack

- **Python 3.11+**
- **Playwright**: Browser automation
- **FastAPI**: REST API framework
- **Pandas**: Data processing
- **Uvicorn**: ASGI server
- **Docker**: Containerization

## ⚡ Performance

- Scrapes 10-50 businesses in 2-5 minutes (depends on query)
- Async processing for multiple requests
- Background job queue
- Automatic retry on failures

## 🔒 Security Features

- Stealth browser configuration
- Random delays between requests
- User-agent rotation
- Cookie consent handling
- Rate limiting ready

## 📝 Requirements

```
playwright>=1.48.0
pandas>=2.2.0
python-dotenv>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use for your projects!

## 🐛 Troubleshooting

### Browser not found
```bash
playwright install chromium
playwright install-deps chromium
```

### Port already in use
```bash
PORT=8080 python api.py
```

### Timeout errors
- Reduce `max_results`
- Run with `--no-headless` to debug
- Check internet connection

## 💡 Tips

1. Start with small `max_results` (5-10) for testing
2. Use headless mode in production for better performance
3. Monitor logs for any issues
4. Set up proper error handling for production use

## 📧 Support

For issues and questions, please open a GitHub issue.

---

Made with ❤️ for efficient web scraping
