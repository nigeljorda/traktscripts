import requests
from bs4 import BeautifulSoup
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Define the header for the output CSV
csv_file = "watched_movies_tmdb.csv"
csv_header = ["Letterboxd URL", "TMDB ID", "Type"]

# Function to extract movie URLs from the main list page
def extract_movie_urls(page_url):
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    movie_data = []
    
    # Get all movie containers (list items)
    movie_items = soup.find_all('li', class_='poster-container')
    
    for li in movie_items:
        # Find the movie URL from the 'data-target-link' attribute
        lazy_load_div = li.find('div', class_='really-lazy-load')
        
        if lazy_load_div and lazy_load_div.get('data-target-link'):
            movie_url = "https://letterboxd.com" + lazy_load_div['data-target-link']
            movie_data.append(movie_url)
    
    return movie_data

# Function to extract TMDb info from the detailed movie page
def extract_tmdb_info(movie_url):
    response = requests.get(movie_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the TMDb button by class and text content
    tmdb_button = soup.find('a', class_='micro-button track-event', string='TMDb')
    
    if tmdb_button:
        tmdb_link = tmdb_button.get('href')
        
        # Extract TMDB ID and type (movie or tv)
        if "/movie/" in tmdb_link:
            tmdb_id = tmdb_link.split("/movie/")[1].strip("/")
            media_type = "movie"
        elif "/tv/" in tmdb_link:
            tmdb_id = tmdb_link.split("/tv/")[1].strip("/")
            media_type = "show"
        else:
            tmdb_id = None
            media_type = None
        
        return movie_url, tmdb_id, media_type
    else:
        return movie_url, None, None

# Function to find the last page number by parsing pagination
def get_last_page(base_url):
    first_page_url = base_url + "/page/1/"
    response = requests.get(first_page_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find pagination container
    pagination = soup.find('div', class_='paginate-pages')
    
    if pagination:
        # Find the last page number by looking for the last link in the pagination
        last_page_link = pagination.find_all('a')[-1].get('href')
        last_page_number = int(last_page_link.split('/page/')[-1].strip('/'))
    else:
        # If no pagination is found, we assume there's only one page
        last_page_number = 1

    return last_page_number

# Function to crawl multiple pages using ThreadPoolExecutor
def crawl_watched_movies(last_page, base_url):
    all_movie_urls = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for page in range(1, last_page + 1):
            page_url = base_url + f"/page/{page}/"
            futures.append(executor.submit(extract_movie_urls, page_url))
        
        # Progress feedback
        print("- Extracting movies from pages")
        
        # Collect the results as they are completed
        for future in as_completed(futures):
            all_movie_urls.extend(future.result())
    
    return all_movie_urls

# Function to crawl detailed movie pages for TMDb links
def crawl_detailed_movie_pages(movie_urls):
    all_movie_data = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for movie_url in movie_urls:
            futures.append(executor.submit(extract_tmdb_info, movie_url))
        
        # Progress feedback
        print("- Gathering TMDB Ids")
        
        # Collect the results as they are completed
        for future in as_completed(futures):
            all_movie_data.append(future.result())
    
    return all_movie_data

# Function to save the extracted data to a CSV file
def save_to_csv(movie_data):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(csv_header)
        writer.writerows(movie_data)
    
    # Feedback after saving
    print(f"- Movies/shows saved to {csv_file}")

# Function to get the Letterboxd username and validate the input URL
def get_letterboxd_url():
    while True:
        username = input("Enter your Letterboxd username: ").strip()
        base_url = f"https://letterboxd.com/{username}/films"
        
        # Validate the URL by trying to access the first page
        try:
            response = requests.get(base_url)
            if response.status_code == 200:
                return base_url
            else:
                print(f"Invalid username or the page doesn't exist. Please try again.")
        except requests.RequestException:
            print("Error accessing the page. Please check your internet connection and try again.")

# Main function to run the script
if __name__ == "__main__":
    # Get the user's Letterboxd URL
    base_url = get_letterboxd_url()
    
    # Find the last page number
    last_page = get_last_page(base_url)
    
    # Crawl all pages to collect movie URLs
    movie_urls = crawl_watched_movies(last_page, base_url)
    
    # Crawl detailed movie pages to extract TMDb links
    movie_data = crawl_detailed_movie_pages(movie_urls)
    
    # Save the data to CSV
    save_to_csv(movie_data)

    print("Script finished.")
