from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
import signal
import sys

# Global variable to store all results for signal handler
all_results = []
current_page = 1

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully by saving current progress"""
    print('\n🛑 Interrupted! Saving current progress...')
    if all_results:
        df = pd.DataFrame(all_results, columns=["URL"])
        df = df.drop_duplicates(subset="URL")
        filename = f"eetimes_semiconductors_interrupted_page_{current_page}.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(df)} articles to {filename} before exiting")
    sys.exit(0)

def setup_driver():
    """Setup optimized Chrome driver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")  # Don't load images (faster)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Performance optimizations
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Disable logging
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add some additional stability options
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Set timeouts
    driver.set_page_load_timeout(30)  # Increased timeout
    driver.implicitly_wait(10)  # Increased implicit wait
    
    return driver

def scrape_page_with_fallback(driver, url, page_num):
    """Scrape a page with multiple fallback strategies"""
    print(f"🔎 Scraping page {page_num}: {url}")
    results = []
    
    try:
        # Load the page
        driver.get(url)
        
        # Wait for content to load - try multiple strategies
        wait = WebDriverWait(driver, 15)  # Increased wait time
        
        try:
            # Strategy 1: Wait for article links within specific segments
            wait.until(EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".segment-one a.article-links")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".segment-main a.article-links"))
            ))
            print(f"   ✅ Page {page_num} loaded with article-links in segments")
        except TimeoutException:
            # Strategy 2: Wait for segment containers
            try:
                wait.until(EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".segment-one")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".segment-main"))
                ))
                print(f"   ⚠️  Page {page_num} loaded but no article-links found in segments")
            except TimeoutException:
                print(f"   ❌ Page {page_num} failed to load properly")
                return results
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Look for article-links within segment-one or segment-main
        selectors = [
            ".segment-one a.article-links",
            ".segment-main a.article-links"
        ]
        
        links_found = False
        for selector in selectors:
            links = soup.select(selector)
            if links:
                print(f"   ✅ Found {len(links)} links with selector: {selector}")
                
                for link in links:
                    href = link.get("href")
                    text = link.text.strip()
                    
                    # Clean and validate
                    if href and text and len(text) > 10:  # Reasonable title length
                        # Ensure absolute URL
                        if href.startswith('/'):
                            href = 'https://www.eetimes.com' + href
                        
                        # Only append the URL now
                        results.append(href)
                
                links_found = True
        
        if not links_found:
            print(f"   ⚠️  No article links found on page {page_num}")
        
    except TimeoutException:
        print(f"   ❌ Timeout loading page {page_num}")
    except WebDriverException as e:
        print(f"   ❌ WebDriver error on page {page_num}: {str(e)[:100]}")
    except Exception as e:
        print(f"   ❌ Unexpected error on page {page_num}: {str(e)[:100]}")
    
    return results

def save_progress(results, page_num, batch_num=None):
    """Save current progress to CSV"""
    if results:
        df = pd.DataFrame(results, columns=["URL"])
        df = df.drop_duplicates(subset="URL")
        
        if batch_num:
            filename = f"eetimes_semiconductors_batch_{batch_num}_pages_{page_num-49}-{page_num}.csv"
        else:
            filename = f"eetimes_semiconductors_final_page_{page_num}.csv"
            
        df.to_csv(filename, index=False)
        print(f"💾 Saved {len(df)} articles to {filename}")
        return filename
    return None

def main():
    """Main scraping function with driver restart every 50 pages"""
    global all_results, current_page
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    driver = None
    batch_results = []  # Results for current batch
    batch_num = 1
    js_enabled = False
    
    try:
        print("🚀 Starting EETimes scraper with auto-restart every 50 pages")
        
        # Scrape all pages from 1 to 1824
        for page in range(1, 1825):
            current_page = page
            
            # Start new driver every 50 pages or on first run
            if (page - 1) % 50 == 0:
                if driver:
                    print(f"🔄 Restarting driver after {page-1} pages...")
                    driver.quit()
                    time.sleep(2)  # Brief pause between driver sessions
                
                print(f"🚀 Starting driver for batch {batch_num} (pages {page}-{min(page+49, 1824)})")
                driver = setup_driver()
                
                # Test if we need JavaScript on first batch only
                if batch_num == 1 and not js_enabled:
                    print("🧪 Testing if JavaScript is required...")
                    test_results = scrape_page_with_fallback(driver, "https://www.eetimes.com/tag/semiconductors/page/1/", "test")
                    
                    if not test_results:
                        print("🔄 No results without JS, enabling JavaScript...")
                        driver.quit()
                        
                        # Retry with JavaScript enabled
                        options = Options()
                        options.add_argument("--headless")
                        options.add_argument("--no-sandbox")
                        options.add_argument("--disable-dev-shm-usage")
                        options.add_argument("--disable-gpu")
                        options.add_argument("--disable-extensions")
                        options.add_argument("--disable-images")
                        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                        # Note: JavaScript enabled this time
                        
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=options)
                        driver.set_page_load_timeout(30)
                        driver.implicitly_wait(10)
                        js_enabled = True
            
            # Scrape the page
            url = f"https://www.eetimes.com/tag/semiconductors/page/{page}/"
            page_results = scrape_page_with_fallback(driver, url, page)
            batch_results.extend(page_results)
            all_results.extend(page_results)
            
            # Save batch every 50 pages
            if page % 50 == 0:
                print(f"📊 Completed batch {batch_num}: pages {page-49}-{page}")
                save_progress(batch_results, page, batch_num)
                print(f"📈 Total progress: {page}/1824 pages completed ({len(all_results)} articles found so far)")
                
                # Reset batch results and increment batch number
                batch_results = []
                batch_num += 1
            
            # Small delay between pages
            time.sleep(1)
        
        # Save any remaining results (if total pages not divisible by 50)
        if batch_results:
            save_progress(batch_results, current_page, batch_num)
        
        print(f"\n✅ Scraping complete! Found {len(all_results)} total articles across all batches.")
        
        # Save final combined results
        if all_results:
            df_final = pd.DataFrame(all_results, columns=["URL"])
            df_final = df_final.drop_duplicates(subset="URL")
            final_filename = "eetimes_semiconductors_COMPLETE_all_pages.csv"
            df_final.to_csv(final_filename, index=False)
            print(f"📁 Final combined data saved to {final_filename} ({len(df_final)} unique articles)")
        else:
            print("⚠️  No results found!")
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        # Try to save whatever we have
        if all_results:
            save_progress(all_results, current_page)
    
    finally:
        if driver:
            driver.quit()
            print("🔚 Driver closed")

if __name__ == "__main__":
    main()