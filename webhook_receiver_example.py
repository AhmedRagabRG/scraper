#!/usr/bin/env python3
"""
Example Webhook Receiver
Simple Flask server to receive webhook data from the scraper
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook_receiver():
    """
    Receive webhook data from scraper
    """
    try:
        # Get JSON data
        data = request.get_json()
        
        print("=" * 80)
        print(f"🔔 Webhook received at {datetime.now().isoformat()}")
        print("=" * 80)
        
        # Print job info
        print(f"📊 Job ID: {data.get('job_id')}")
        print(f"✅ Status: {data.get('status')}")
        
        # Print place info (for reviews)
        if data.get('place_name'):
            print(f"🏪 Place Name: {data.get('place_name')}")
        if data.get('place_url'):
            print(f"🔗 Place URL: {data.get('place_url')}")
        
        # Check if it's a single review or completion
        if data.get('status') == 'processing':
            # Single review webhook
            print(f"📝 Review {data.get('current_review')}/{data.get('total_expected')}")
            review = data.get('review', {})
            print(f"   Name: {review.get('reviewer_name', 'N/A')}")
            print(f"   Date: {review.get('review_date', 'N/A')}")
            print(f"   Rating: {review.get('rating', 'N/A')}")
            print(f"   Text: {review.get('review_text', 'N/A')[:100]}...")
        
        elif data.get('status') == 'completed':
            # Completion webhook
            print(f"📝 Total Results: {data.get('total_results')}")
            print(f"⏰ Completed At: {data.get('completed_at')}")
            print(f"💬 Message: {data.get('message', 'N/A')}")
            
            if data.get('download_url'):
                print(f"⬇️  Download URL: {data.get('download_url')}")
        
        # Save to file (optional)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"webhook_data_{data.get('job_id')}_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Data saved to {output_file}")
        
        print("=" * 80)
        
        # Return success response
        return jsonify({
            "status": "success",
            "message": "Webhook received successfully",
            "received_at": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    print("🚀 Starting Webhook Receiver Server...")
    print("📡 Listening on http://localhost:5000/webhook")
    print("💡 Use this URL as webhook_url in your scraper requests")
    print()
    app.run(host='0.0.0.0', port=5000, debug=True)
