#!/usr/bin/env python3
"""
Google Maps Scraper - Main Entry Point
Scrapes business information from Google Maps search results.
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from scraper import scrape_google_maps


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Google Maps Scraper - Extract business leads from Google Maps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --query "Real Estate Agencies in Cairo"
  python main.py --query "Restaurants in New York" --output data/results.csv --headless
  python main.py --query "Hotels in Paris" --no-headless
        """
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Search query (e.g., "Real Estate Agencies in Cairo")',
        required=False
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output CSV file path (default: results_TIMESTAMP.csv)',
        default=None
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (default: True)',
        default=True
    )

    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Run browser with GUI (for debugging)'
    )

    parser.add_argument(
        '--max-results', '-m',
        type=int,
        help='Maximum number of results to scrape (default: all available)',
        default=None
    )

    return parser.parse_args()


def get_search_query(args) -> str:
    """Get search query from arguments or environment variable."""
    # Priority: CLI argument > Environment variable
    query = args.query or os.getenv('SEARCH_QUERY')

    if not query:
        print("❌ Error: No search query provided!")
        print("   Use --query flag or set SEARCH_QUERY environment variable")
        sys.exit(1)

    return query


def generate_output_filename(custom_path: str = None) -> str:
    """Generate output filename with timestamp."""
    if custom_path:
        return custom_path

    # Create output directory if it doesn't exist
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return str(output_dir / f'results_{timestamp}.csv')


def save_to_csv(data: list, output_path: str):
    """Save scraped data to CSV file."""
    if not data:
        print("⚠️  No data to save!")
        return

    df = pd.DataFrame(data)

    # Reorder columns for better readability
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

    # Only include columns that exist
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]

    # Save to CSV
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 Data saved to: {output_path}")
    print(f"   Total records: {len(df)}")

    # Print summary statistics
    print("\n📈 Summary Statistics:")
    print(f"   Businesses with ratings: {df['rating'].notna().sum()}")
    print(f"   Businesses with reviews: {df['review_count'].notna().sum()}")
    
    # Star breakdown statistics
    if 'five_star' in df.columns:
        star_breakdown_count = df['five_star'].notna().sum()
        if star_breakdown_count > 0:
            print(f"   Businesses with star breakdown: {star_breakdown_count}")
    
    print(f"   Businesses with phone: {df['phone'].notna().sum()}")
    print(f"   Businesses with email: {df['email'].notna().sum()}")
    print(f"   Businesses with website: {df['website'].notna().sum()}")
    print(f"   Businesses with address: {df['address'].notna().sum()}")

    if not df['rating'].isna().all():
        print(f"   Average rating: {df['rating'].mean():.2f}")
    
    if 'review_count' in df.columns and not df['review_count'].isna().all():
        print(f"   Total reviews collected: {df['review_count'].sum():.0f}")
    
    # Show star distribution totals if available
    if 'five_star' in df.columns and not df['five_star'].isna().all():
        print(f"\n⭐ Star Distribution Totals:")
        if 'five_star' in df.columns:
            print(f"   5-star reviews: {df['five_star'].sum():.0f}")
        if 'four_star' in df.columns:
            print(f"   4-star reviews: {df['four_star'].sum():.0f}")
        if 'three_star' in df.columns:
            print(f"   3-star reviews: {df['three_star'].sum():.0f}")
        if 'two_star' in df.columns:
            print(f"   2-star reviews: {df['two_star'].sum():.0f}")
        if 'one_star' in df.columns:
            print(f"   1-star reviews: {df['one_star'].sum():.0f}")


async def main():
    """Main execution function."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_arguments()

    # Get search query
    search_query = get_search_query(args)

    # Generate output filename
    output_path = generate_output_filename(args.output)

    # Print configuration
    print("=" * 60)
    print("🗺️  GOOGLE MAPS SCRAPER")
    print("=" * 60)
    print(f"Query:       {search_query}")
    print(f"Output:      {output_path}")
    print(f"Headless:    {args.headless}")
    print(f"Max Results: {args.max_results if args.max_results else 'All available'}")
    print("=" * 60)
    print()

    try:
        # Run the scraper
        results = await scrape_google_maps(
            search_term=search_query,
            headless=args.headless,
            max_results=args.max_results
        )

        # Save results
        if results:
            save_to_csv(results, output_path)
            print("\n✅ Scraping completed successfully!")
        else:
            print("\n⚠️  No results found. Please check your query.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())
