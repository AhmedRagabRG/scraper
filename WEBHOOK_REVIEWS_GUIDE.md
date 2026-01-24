# Google Maps Reviews Scraper - Webhook Guide

## Overview
The reviews scraper now sends **real-time webhooks** for each review as it's extracted, plus a final completion webhook with place information.

## Webhook Payload Structure

### 1. Individual Review Webhook (Real-time)
Sent after each review is extracted:

```json
{
  "job_id": "abc123def456",
  "status": "processing",
  "current_review": 5,
  "total_expected": 50,
  "place_name": "Kochen & Braten",
  "place_url": "https://www.google.com/maps/place/...",
  "review": {
    "reviewer_name": "John Doe",
    "review_date": "2 months ago",
    "rating": 5,
    "review_text": "Great place! Highly recommended.",
    "pictures": "yes",
    "company_reply": "no"
  },
  "timestamp": "2026-01-24T10:30:00"
}
```

### 2. Completion Webhook
Sent when scraping is complete:

```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "place_name": "Kochen & Braten",
  "place_url": "https://www.google.com/maps/place/...",
  "total_results": 50,
  "completed_at": "2026-01-24T10:35:00",
  "download_url": "/download/abc123def456",
  "message": "Reviews scraping completed! 50 reviews extracted and 50 sent to webhook."
}
```

## API Request Example

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://maps.app.goo.gl/cqSuYGUaTVG5gpqh8",
    "max_reviews": 50,
    "headless": true,
    "webhook_url": "https://your-server.com/webhook"
  }'
```

## Response
```json
{
  "job_id": "abc123def456",
  "status": "pending",
  "message": "Reviews scraping job started"
}
```

## Key Features

### Place Information
- **place_name**: Name of the business/restaurant/location
- **place_url**: Full Google Maps URL (can be used to share)

### Real-time Updates
- Each review is sent to webhook immediately after extraction
- No need to wait for all reviews to complete
- Track progress with `current_review` and `total_expected`

### Database Integration Example
```python
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    
    if data['status'] == 'processing':
        # Save individual review to database
        review = data['review']
        db.reviews.insert({
            'job_id': data['job_id'],
            'place_name': data['place_name'],
            'place_url': data['place_url'],
            'reviewer_name': review['reviewer_name'],
            'review_date': review['review_date'],
            'rating': review['rating'],
            'review_text': review['review_text'],
            'pictures': review['pictures'],
            'company_reply': review['company_reply'],
            'received_at': datetime.now()
        })
    
    elif data['status'] == 'completed':
        # Update job status
        db.jobs.update(
            {'job_id': data['job_id']},
            {'status': 'completed', 'total_reviews': data['total_results']}
        )
    
    return {'status': 'ok'}, 200
```

## Testing Locally

### 1. Start the webhook receiver:
```bash
python3 webhook_receiver_example.py
```

### 2. In another terminal, start the API:
```bash
python3 api.py
```

### 3. Send a scraping request:
```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://maps.app.goo.gl/YOUR_LINK_HERE",
    "max_reviews": 10,
    "headless": false,
    "webhook_url": "http://localhost:5000/webhook"
  }'
```

## Benefits

1. **Real-time Processing**: Process reviews as they arrive
2. **Progress Tracking**: Know exactly how many reviews have been scraped
3. **Place Context**: Every review includes the place name and URL
4. **Database Friendly**: Easy to insert into database row by row
5. **Error Recovery**: If scraping stops, you still have partial data
6. **Scalable**: Can handle large numbers of reviews without memory issues

## Error Handling

If scraping fails, you'll receive:
```json
{
  "job_id": "abc123def456",
  "status": "failed",
  "error": "Error message here",
  "completed_at": "2026-01-24T10:30:00"
}
```

## Notes
- The webhook is called for EACH review (can be many calls for large scrapes)
- Make sure your webhook endpoint can handle high request volumes
- Implement rate limiting if needed
- The completion webhook confirms the total count
