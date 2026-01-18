# 📡 API Request Examples

## cURL Examples

### 1. Start Scraping Job

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 10,
    "headless": true
  }'
```

### 1b. Start Scraping Job with Webhook

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 10,
    "headless": true,
    "webhook_url": "https://n8n.tadfoq.com/webhook/4994019d-b24e-46f5-a1e3-8dfd6e5f626e"
  }'
```

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Scraping job started. Results will be sent to your webhook."
}
```

### 2. Check Status

```bash
curl http://localhost:8000/status/e3f68a2a
```

### 3. Download CSV

```bash
curl http://localhost:8000/download/abc123 -o results.csv
```

### 4. Get JSON Results

```bash
curl http://localhost:8000/results/abc123 | jq
```

### 5. List All Jobs

```bash
curl http://localhost:8000/jobs | jq
```

### 6. Delete Job

```bash
curl -X DELETE http://localhost:8000/job/abc123
```

---

## Python Examples

### Basic Usage

```python
import requests
import time

# Start scraping
response = requests.post('http://localhost:8000/scrape', json={
    'query': 'Restaurants in Cairo',
    'max_results': 20
})

job_id = response.json()['job_id']
print(f"Job ID: {job_id}")

# Wait for completion
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Status: {status['status']}")
    
    if status['status'] in ['completed', 'failed']:
        break
    time.sleep(5)

# Get results
results = requests.get(f'http://localhost:8000/results/{job_id}').json()
print(f"Total: {results['total_results']}")
```

### Advanced with Error Handling

```python
import requests
import time
from typing import Optional, Dict, List

class GoogleMapsScraper:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def scrape(self, query: str, max_results: Optional[int] = None) -> str:
        """Start scraping job and return job_id"""
        response = requests.post(f"{self.base_url}/scrape", json={
            'query': query,
            'max_results': max_results,
            'headless': True
        })
        response.raise_for_status()
        return response.json()['job_id']
    
    def wait_for_completion(self, job_id: str, timeout: int = 600) -> Dict:
        """Wait for job completion and return final status"""
        start = time.time()
        
        while time.time() - start < timeout:
            status = self.get_status(job_id)
            
            if status['status'] == 'completed':
                return status
            elif status['status'] == 'failed':
                raise Exception(f"Job failed: {status.get('error')}")
            
            time.sleep(5)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
    
    def get_status(self, job_id: str) -> Dict:
        """Get job status"""
        response = requests.get(f"{self.base_url}/status/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def get_results(self, job_id: str) -> List[Dict]:
        """Get results as list of dictionaries"""
        response = requests.get(f"{self.base_url}/results/{job_id}")
        response.raise_for_status()
        return response.json()['results']
    
    def download_csv(self, job_id: str, filename: str):
        """Download results as CSV"""
        response = requests.get(f"{self.base_url}/download/{job_id}")
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(response.content)

# Usage
scraper = GoogleMapsScraper()

# Scrape and wait
job_id = scraper.scrape("Hotels in Cairo", max_results=15)
print(f"Started job: {job_id}")

status = scraper.wait_for_completion(job_id)
print(f"Completed with {status['total_results']} results")

# Get results
results = scraper.get_results(job_id)
for business in results:
    print(f"{business['business_name']}: {business['rating']}⭐")

# Download CSV
scraper.download_csv(job_id, 'hotels_cairo.csv')
```

---

## JavaScript/Node.js Examples

### Basic Usage

```javascript
const axios = require('axios');

async function scrapeGoogleMaps(query, maxResults = null) {
  const baseUrl = 'http://localhost:8000';
  
  // Start job
  const startResponse = await axios.post(`${baseUrl}/scrape`, {
    query: query,
    max_results: maxResults,
    headless: true
  });
  
  const jobId = startResponse.data.job_id;
  console.log(`Job started: ${jobId}`);
  
  // Wait for completion
  while (true) {
    const statusResponse = await axios.get(`${baseUrl}/status/${jobId}`);
    const status = statusResponse.data;
    
    console.log(`Status: ${status.status} - ${status.progress || ''}`);
    
    if (status.status === 'completed') {
      break;
    } else if (status.status === 'failed') {
      throw new Error(`Job failed: ${status.error}`);
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  // Get results
  const resultsResponse = await axios.get(`${baseUrl}/results/${jobId}`);
  return resultsResponse.data;
}

// Usage
scrapeGoogleMaps('Coffee Shops in Cairo', 10)
  .then(data => {
    console.log(`Total results: ${data.total_results}`);
    data.results.forEach(business => {
      console.log(`${business.business_name}: ${business.rating}⭐`);
    });
  })
  .catch(err => console.error(err));
```

### TypeScript with Types

```typescript
import axios from 'axios';

interface ScrapeRequest {
  query: string;
  max_results?: number;
  headless?: boolean;
}

interface Business {
  business_name: string;
  rating?: number;
  review_count?: number;
  five_star?: number;
  four_star?: number;
  three_star?: number;
  two_star?: number;
  one_star?: number;
  phone?: string;
  email?: string;
  website?: string;
  address?: string;
}

interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  query?: string;
  progress?: string;
  total_results?: number;
  created_at?: string;
  completed_at?: string;
  error?: string;
  download_url?: string;
}

class GoogleMapsScraper {
  private baseUrl: string;
  
  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }
  
  async scrape(request: ScrapeRequest): Promise<string> {
    const response = await axios.post<{job_id: string}>(`${this.baseUrl}/scrape`, request);
    return response.data.job_id;
  }
  
  async getStatus(jobId: string): Promise<JobStatus> {
    const response = await axios.get<JobStatus>(`${this.baseUrl}/status/${jobId}`);
    return response.data;
  }
  
  async waitForCompletion(jobId: string, timeout: number = 600000): Promise<JobStatus> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const status = await this.getStatus(jobId);
      
      if (status.status === 'completed') {
        return status;
      } else if (status.status === 'failed') {
        throw new Error(`Job failed: ${status.error}`);
      }
      
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
    
    throw new Error(`Timeout waiting for job ${jobId}`);
  }
  
  async getResults(jobId: string): Promise<Business[]> {
    const response = await axios.get<{results: Business[]}>(`${this.baseUrl}/results/${jobId}`);
    return response.data.results;
  }
  
  async downloadCsv(jobId: string, filename: string): Promise<void> {
    const response = await axios.get(`${this.baseUrl}/download/${jobId}`, {
      responseType: 'arraybuffer'
    });
    
    const fs = require('fs');
    fs.writeFileSync(filename, response.data);
  }
}

// Usage
const scraper = new GoogleMapsScraper();

(async () => {
  const jobId = await scraper.scrape({
    query: 'Restaurants in Cairo',
    max_results: 20
  });
  
  console.log(`Job started: ${jobId}`);
  
  const status = await scraper.waitForCompletion(jobId);
  console.log(`Completed: ${status.total_results} results`);
  
  const results = await scraper.getResults(jobId);
  results.forEach(business => {
    console.log(`${business.business_name}: ${business.rating}⭐`);
  });
  
  await scraper.downloadCsv(jobId, 'results.csv');
})();
```

---

## PHP Example

```php
<?php

class GoogleMapsScraper {
    private $baseUrl;
    
    public function __construct($baseUrl = 'http://localhost:8000') {
        $this->baseUrl = $baseUrl;
    }
    
    public function scrape($query, $maxResults = null) {
        $data = [
            'query' => $query,
            'max_results' => $maxResults,
            'headless' => true
        ];
        
        $ch = curl_init($this->baseUrl . '/scrape');
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true)['job_id'];
    }
    
    public function getStatus($jobId) {
        $ch = curl_init($this->baseUrl . '/status/' . $jobId);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true);
    }
    
    public function waitForCompletion($jobId, $timeout = 600) {
        $start = time();
        
        while (time() - $start < $timeout) {
            $status = $this->getStatus($jobId);
            
            if ($status['status'] === 'completed') {
                return $status;
            } elseif ($status['status'] === 'failed') {
                throw new Exception('Job failed: ' . $status['error']);
            }
            
            sleep(5);
        }
        
        throw new Exception('Timeout');
    }
    
    public function getResults($jobId) {
        $ch = curl_init($this->baseUrl . '/results/' . $jobId);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true)['results'];
    }
}

// Usage
$scraper = new GoogleMapsScraper();

$jobId = $scraper->scrape('Coffee Shops in Cairo', 10);
echo "Job started: $jobId\n";

$status = $scraper->waitForCompletion($jobId);
echo "Completed: {$status['total_results']} results\n";

$results = $scraper->getResults($jobId);
foreach ($results as $business) {
    echo "{$business['business_name']}: {$business['rating']}⭐\n";
}
?>
```

---

## Postman Collection

Import this JSON into Postman:

```json
{
  "info": {
    "name": "Google Maps Scraper API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Start Scraping",
      "request": {
        "method": "POST",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"Coffee Shops in Cairo\",\n  \"max_results\": 10,\n  \"headless\": true\n}"
        },
        "url": {"raw": "{{base_url}}/scrape", "host": ["{{base_url}}"], "path": ["scrape"]}
      }
    },
    {
      "name": "Get Status",
      "request": {
        "method": "GET",
        "url": {"raw": "{{base_url}}/status/{{job_id}}", "host": ["{{base_url}}"], "path": ["status", "{{job_id}}"]}
      }
    },
    {
      "name": "Download CSV",
      "request": {
        "method": "GET",
        "url": {"raw": "{{base_url}}/download/{{job_id}}", "host": ["{{base_url}}"], "path": ["download", "{{job_id}}"]}
      }
    }
  ],
  "variable": [
    {"key": "base_url", "value": "http://localhost:8000"}
  ]
}
```

---

## Shell Script Example

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
QUERY="Hotels in Cairo"
MAX_RESULTS=15

# Start job
echo "Starting scraping job..."
RESPONSE=$(curl -s -X POST "$BASE_URL/scrape" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"max_results\": $MAX_RESULTS}")

JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
echo "Job ID: $JOB_ID"

# Wait for completion
echo "Waiting for completion..."
while true; do
  STATUS=$(curl -s "$BASE_URL/status/$JOB_ID")
  CURRENT_STATUS=$(echo $STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  
  echo "Status: $CURRENT_STATUS"
  
  if [ "$CURRENT_STATUS" = "completed" ] || [ "$CURRENT_STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

# Download results
if [ "$CURRENT_STATUS" = "completed" ]; then
  echo "Downloading results..."
  curl -s "$BASE_URL/download/$JOB_ID" -o "results_$JOB_ID.csv"
  echo "Done! Results saved to results_$JOB_ID.csv"
fi
```
