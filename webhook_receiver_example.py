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
        print(f"📝 Total Results: {data.get('total_results')}")
        print(f"⏰ Completed At: {data.get('completed_at')}")
        
        # Print results summary
        results = data.get('results', [])
        if results:
            print(f"\n📋 First 3 Results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  Review {i}:")
                print(f"    Name: {result.get('reviewer_name', 'N/A')}")
                print(f"    Date: {result.get('review_date', 'N/A')}")
                print(f"    Rating: {result.get('rating', 'N/A')}")
                print(f"    Text: {result.get('review_text', 'N/A')[:100]}...")
        
        # Save to file (optional)
        output_file = f"webhook_data_{data.get('job_id')}.json"
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
