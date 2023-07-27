import requests
from bs4 import BeautifulSoup
import csv
from datetime import date
import os
import pickle
import time
from datetime import datetime



# Function to crawl Google Scholar page and extract citation information
def crawl_google_scholar():
    # Replace the URL with your own Google Scholar page
    url = "https://scholar.google.com/citations?user=RkspD6IAAAAJ"

    # Set the headers to mimic a legitimate user request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Create a dict to store the results
    results = {}
    
    # Initialize the page number
    page = 0
    stop = False
    
    while True:
        # Send a GET request to the URL with headers and page number
        response = requests.get(url + f"&cstart={page}", headers=headers)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all the papers listed on the page
        papers = soup.find_all("tr", {"class": "gsc_a_tr"})
        
        # Check if there are no more papers on the page
        if stop:
            break
        
        # Loop through each paper and extract the citation information
        for paper in papers:
            title = paper.find("a", {"class": "gsc_a_at"})
            if title is not None:
                title = title.text
                citations = paper.find("a", {"class": "gsc_a_ac"}).text
                if len(citations) == 0:
                    citations = 0
                else:
                    citations = int(citations)
                
                # Append the paper information to the results list
                results[title] = citations
            else:
                stop = True
        
        # Increment the page number
        page += 20
    
    return results

# Function to write the results to a CSV file
def write_to_csv(results, csv_file):
    with open(csv_file, "w") as file:
        for key in results.keys():
            file.write("%s, %s\n" % (key, results[key]))

# Function to write the results to a pkl file
def write_to_pkl(results, csv_file):
    with open(csv_file, "wb") as file:
        pickle.dump(results, file)

# Function to read the previous citation counts from a CSV file
def read_previous_counts(previous_counts_file):
    # Check if the previous counts file exists
    if os.path.isfile(previous_counts_file):
        with open(previous_counts_file, 'rb') as file:
            return pickle.load(file)
    else:
        # If the previous counts file does not exist, return an empty dictionary
        return {}

def get_last_added_file(folder_path):
    # Get a list of files in the folder
    files = os.listdir(folder_path)

    # Sort the files based on their modification time in descending order
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)

    if sorted_files:
        # Return the name of the most recently modified file
        return sorted_files[0]
    else:
        # If the folder is empty, return None or handle the case as needed
        return None


# Call the crawl_google_scholar function to retrieve the citation information
current_results = crawl_google_scholar()

# Read the previous citation counts
history_folder = "/Users/dongwookim/Workspace/scholar/history/"
diff_folder = "/Users/dongwookim/Workspace/scholar/difference/"
previous_file = get_last_added_file(history_folder)
previous_counts = read_previous_counts(history_folder+previous_file)

now = datetime.now()

current_time = now.strftime("%H:%M:%S")

print("[", current_time, "] read previous file from", previous_file)

# Create a dictionary to store the current citation counts
current_counts = {}
today_sum = 0

# Compare the previous and current results to check for changes
for title in current_results:
    previous_citations = previous_counts.get(title, 0)
    current_citations = int(current_results[title])
    today_sum += current_citations
    
    # Check if there is an increase in the citation count
    if current_citations != previous_citations:
        print(f"Paper: {title}")
        print(f"Previous Citations: {previous_citations}")
        print(f"Current Citations: {current_citations}")
        print("-----------------------------")
    
        # Store the current citation count
        current_counts[title] = current_citations - previous_citations

# Write the increasement to a file
if len(current_counts) > 0:
    today = time.strftime("%Y%m%d.csv")
    print("save difference at", today)
    write_to_csv(current_counts, diff_folder + today)

print("[", current_time, "] Today's total citation: ", today_sum)

# Write the total citation to the pkl file
today_total = time.strftime("%Y%m%d.pkl")
write_to_pkl(current_results, history_folder + today_total)

