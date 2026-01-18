#!/usr/bin/env python3
"""
Google Maps Scraper API
FastAPI server for Google Maps scraping via HTTP requests
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import uuid

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import pandas as pd

from scraper import scrape_google_maps

# Initialize FastAPI app
app = FastAPI(
    title="Google Maps Scraper API",
    description="API for scraping business information from Google Maps",
    version="1.0.0"
)

# Store job status in memory (use Redis/DB for production)
jobs: Dict[str, Dict] = {}


class ScrapeRequest(BaseModel):
    query: str = Field(..., description="Search query (e.g., 'Coffee Shops in Cairo')")
    max_results: Optional[int] = Field(None, description="Maximum number of results to scrape")
    headless: bool = Field(True, description="Run browser in headless mode")
    webhook_url: Optional[str] = Field(None, description="Webhook URL to send results when completed")


class ScrapeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    query: Optional[str] = None
    progress: Optional[str] = None
    total_results: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    download_url: Optional[str] = None


def generate_output_filename(job_id: str) -> str:
    """Generate output filename with job ID."""
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    return str(output_dir / f'results_{job_id}.csv')


def save_to_csv(data: List[Dict], output_path: str):
    """Save scraped data to CSV file."""
    if not data:
        return
    
    df = pd.DataFrame(data)
    
    # Reorder columns
    column_order = [
        'business_name',
        'rating',
        'review_count',
        'five_star',
        'four_star',
        'three_star',
        'two_star',
        'one_star',
        'phone',
        'email',
        'website',
        'address'
    ]
    
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]
    
    # Save to CSV
    df.to_csv(output_path, index=False, encoding='utf-8-sig')


async def send_webhook(webhook_url: str, job_id: str, results: List[Dict], status: str):
    """Send results to webhook URL."""
    try:
        payload = {
            "job_id": job_id,
            "status": status,
            "total_results": len(results) if results else 0,
            "completed_at": datetime.now().isoformat(),
            "results": results if results else []
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                print(f"✅ Webhook sent successfully to {webhook_url}")
                return True
            else:
                print(f"⚠️ Webhook failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")
        return False


async def run_scraper(job_id: str, query: str, max_results: Optional[int], headless: bool, webhook_url: Optional[str] = None):
    """Background task to run the scraper."""
    try:
        jobs[job_id]['status'] = 'running'
        jobs[job_id]['progress'] = 'Starting scraper...'
        
        # Run scraper
        results = await scrape_google_maps(
            search_term=query,
            headless=headless,
            max_results=max_results
        )
        
        if results:
            # Save to CSV
            output_path = generate_output_filename(job_id)
            save_to_csv(results, output_path)
            
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['total_results'] = len(results)
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            jobs[job_id]['download_url'] = f"/download/{job_id}"
            jobs[job_id]['progress'] = f'Completed! {len(results)} results'
            
            # Send webhook if URL provided
            if webhook_url:
                jobs[job_id]['progress'] = 'Sending webhook...'
                webhook_sent = await send_webhook(webhook_url, job_id, results, 'completed')
                jobs[job_id]['webhook_sent'] = webhook_sent
                if webhook_sent:
                    jobs[job_id]['progress'] = f'Completed! {len(results)} results (webhook sent)'
                else:
                    jobs[job_id]['progress'] = f'Completed! {len(results)} results (webhook failed)'
        else:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['total_results'] = 0
            jobs[job_id]['completed_at'] = datetime.now().isoformat()
            jobs[job_id]['progress'] = 'No results found'
            
            # Send webhook even if no results
            if webhook_url:
                await send_webhook(webhook_url, job_id, [], 'completed')
            
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        # Send webhook with error status
        if webhook_url:
            try:
                error_payload = {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat()
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(webhook_url, json=error_payload)
            except:
                pass


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Google Maps Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "POST /scrape": "Start a new scraping job",
            "GET /status/{job_id}": "Get job status",
            "GET /download/{job_id}": "Download results as CSV",
            "GET /results/{job_id}": "Get results as JSON",
            "GET /jobs": "List all jobs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Start a new scraping job.
    
    - **query**: Search query (e.g., "Coffee Shops in Cairo")
    - **max_results**: Maximum number of results (optional)
    - **headless**: Run browser in headless mode (default: true)
    - **webhook_url**: Webhook URL to send results when completed (optional)
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Store job info
    jobs[job_id] = {
        'job_id': job_id,
        'status': 'pending',
        'query': request.query,
        'max_results': request.max_results,
        'webhook_url': request.webhook_url,
        'created_at': datetime.now().isoformat(),
        'progress': 'Job created, waiting to start...'
    }
    
    # Add scraper task to background
    background_tasks.add_task(
        run_scraper,
        job_id=job_id,
        query=request.query,
        max_results=request.max_results,
        headless=request.headless,
        webhook_url=request.webhook_url
    )
    
    message = f"Scraping job started. Use /status/{job_id} to check progress."
    if request.webhook_url:
        message += f" Results will be sent to your webhook."
    
    return ScrapeResponse(
        job_id=job_id,
        status="pending",
        message=message
    )


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    """Get the status of a scraping job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**jobs[job_id])


@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """Download scraping results as CSV file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    output_path = generate_output_filename(job_id)
    
    if not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Results file not found")
    
    return FileResponse(
        output_path,
        media_type='text/csv',
        filename=f'google_maps_results_{job_id}.csv'
    )


@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get scraping results as JSON."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if jobs[job_id]['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    output_path = generate_output_filename(job_id)
    
    if not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Results file not found")
    
    # Read CSV and return as JSON
    df = pd.read_csv(output_path)
    results = df.to_dict('records')
    
    return {
        "job_id": job_id,
        "total_results": len(results),
        "results": results
    }


@app.get("/jobs")
async def list_jobs():
    """List all scraping jobs."""
    return {
        "total_jobs": len(jobs),
        "jobs": list(jobs.values())
    }


@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete CSV file if exists
    output_path = generate_output_filename(job_id)
    if Path(output_path).exists():
        Path(output_path).unlink()
    
    # Remove from jobs dict
    del jobs[job_id]
    
    return {"message": f"Job {job_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
