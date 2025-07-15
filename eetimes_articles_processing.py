import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def extract_article_info(url):
    """Extract article info from EETimes article"""
    
    try:
        print(f"Processing: {url}")
        
        # Get the webpage with timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.encoding = 'utf-8'  # Ensure UTF-8 encoding
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('h1')
        if title:
            title = title.get_text().strip()
        else:
            title = soup.find('title').get_text().strip()
        
        # Extract author from articleHeader-author class
        author_container = soup.find(class_='articleHeader-author')
        if author_container:
            # Look for author link within the container
            author_element = author_container.find('a', class_='author url fn')
            if author_element:
                author = author_element.get_text().strip()
            else:
                # Fallback to any text in the author container
                author = author_container.get_text().strip()
        else:
            author = "Unknown Author"
        
        # Extract publication date
        date_element = soup.find('span', class_='articleHeader-date')
        if date_element:
            publication_date = date_element.get_text().strip()
        else:
            publication_date = "Unknown Date"
        
        # Extract full content from articleBody class
        full_content = ""
        article_body = soup.find(class_='articleBody')
        if article_body:
            # Get all <p> tags within articleBody
            paragraphs = article_body.find_all('p')
            content_parts = []
            for p in paragraphs:
                text = p.get_text().strip()
                if text:  # Only add non-empty paragraphs
                    content_parts.append(text)
            
            if content_parts:
                full_content = ' '.join(content_parts)
        
        # Clean up content
        if full_content:
            full_content = ' '.join(full_content.split())  # Normalize whitespace
        else:
            full_content = "No content found in articleBody"
        
        result = {
            'title': title,
            'full_content': full_content,
            'publication_date': publication_date,
            'author': author,
            'url': url,
            'status': 'success'
        }
        
        # Print extracted info to terminal
        print(f"✓ Successfully extracted article:")
        print(f"  Title: {title}")
        print(f"  Author: {author}")
        print(f"  Publication Date: {publication_date}")
        print(f"  Content Length: {len(full_content)} characters")
        print(f"  Content Preview: {full_content[:150]}...")
        
        return result
        
    except Exception as e:
        error_message = 'Error extracting content: ' + str(e)
        error_result = {
            'title': 'ERROR',
            'full_content': error_message,
            'publication_date': 'ERROR',
            'author': 'ERROR',
            'url': url,
            'status': 'error'
        }
        
        # Print error info to terminal
        print("✗ Error processing article:")
        print("  URL:", url)
        print("  Error:", str(e))
        
        return error_result

def process_urls_from_csv(csv_file, url_column='url', delay=1):
    """
    Process URLs from a CSV file
    
    Args:
        csv_file (str): Path to CSV file containing URLs
        url_column (str): Name of column containing URLs (default: 'url')
        delay (int): Delay in seconds between requests (default: 1)
    """
    
    # Read the CSV file
    print(f"Reading URLs from: {csv_file}")
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"Found {len(df)} rows in CSV")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Check if URL column exists
    if url_column not in df.columns:
        print(f"Error: Column '{url_column}' not found in CSV.")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Extract URLs
    urls = df[url_column].dropna().tolist()
    print(f"Found {len(urls)} URLs to process")
    
    # Set up output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'article_extracts_{timestamp}.csv'
    column_order = ['title', 'full_content', 'publication_date', 'author', 'url', 'status']
    
    # Create empty CSV with headers
    pd.DataFrame(columns=column_order).to_csv(output_file, index=False, encoding='utf-8')
    print(f"Progress will be saved to: {output_file}")
    
    # Process each URL with periodic saving
    results = []
    try:
        for i, url in enumerate(urls, 1):
            print(f"\nProcessing {i}/{len(urls)}")
            
            result = extract_article_info(url)
            results.append(result)
            
            # Save progress every 50 URLs or at the end
            if i % 50 == 0 or i == len(urls):
                results_df = pd.DataFrame(results)
                results_df = results_df[column_order]
                results_df.to_csv(output_file, index=False, encoding='utf-8')
                print(f"  Progress saved ({i}/{len(urls)} completed)")
            
            # Add delay between requests to be respectful
            if i < len(urls):
                print(f"Waiting {delay} seconds...")
                time.sleep(delay)
                
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print("INTERRUPTED BY USER (Ctrl+C)")
        print(f"{'='*60}")
        print(f"Processed {len(results)} out of {len(urls)} URLs")
        print(f"Partial results saved to: {output_file}")
        return pd.DataFrame(results)
    
    # Print final summary
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total URLs processed: {len(results)}")
    print(f"Successful extractions: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Failed extractions: {len([r for r in results if r['status'] == 'error'])}")
    print(f"Results saved to: {output_file}")
    
    return pd.DataFrame(results)

def main():
    """
    Main function - you can either process a single URL or a CSV file
    """
    
    # Option 1: Process a CSV file of URLs
    csv_file = input("Enter path to CSV file (or press Enter to process single URL): ").strip()
    
    if csv_file:
        # Process CSV file
        url_column = input("Enter URL column name (default: 'url'): ").strip() or 'url'
        delay = input("Enter delay between requests in seconds (default: 1): ").strip()
        delay = int(delay) if delay.isdigit() else 1
        
        process_urls_from_csv(csv_file, url_column, delay)
        
    else:
        # Process single URL (original functionality)
        url = "https://www.eetimes.com/indian-risc-v-startup-slashes-design-time-to-minutes/"
        
        print(f"Extracting info from: {url}")
        result = extract_article_info(url)
        
        # Print results
        print("\n" + "="*50)
        print("EXTRACTED ARTICLE INFO:")
        print("="*50)
        print(f"Title: {result['title']}")
        print(f"Author: {result['author']}")
        print(f"Publication Date: {result['publication_date']}")
        print(f"Content Preview: {result['full_content'][:200]}...")
        print(f"Status: {result['status']}")
        
        # Save to CSV
        df = pd.DataFrame([result])
        output_file = f'single_article_extract_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nSaved to: {output_file}")

if __name__ == "__main__":
    main()