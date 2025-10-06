from flask import Flask, render_template, jsonify, request
import os
import csv
import pickle
from datetime import datetime, timedelta
import glob
import json
from collections import defaultdict, Counter
import statistics
import requests
from bs4 import BeautifulSoup
import time
from config import GOOGLE_SCHOLAR_URL, REQUEST_HEADERS, HOST, PORT, DEBUG

app = Flask(__name__)

def get_data_paths():
    """Get paths to data directories"""
    root_path = os.path.dirname(os.path.abspath(__file__))
    return {
        'history': os.path.join(root_path, 'history'),
        'difference': os.path.join(root_path, 'difference')
    }

def crawl_google_scholar():
    """Crawl Google Scholar page and extract citation information"""
    url = GOOGLE_SCHOLAR_URL
    headers = REQUEST_HEADERS

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

def write_to_csv(results, csv_file):
    """Write the results to a CSV file"""
    with open(csv_file, "w", encoding='utf-8') as file:
        for key in results.keys():
            file.write("%s, %s\n" % (key, results[key]))

def write_to_pkl(results, pkl_file):
    """Write the results to a pkl file"""
    with open(pkl_file, "wb") as file:
        pickle.dump(results, file)

def get_last_added_file(folder_path):
    """Get the most recently added file in a folder"""
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

def update_citation_data():
    """Update citation data by crawling Google Scholar and comparing with previous data"""
    try:
        # Get current citation data from Google Scholar
        current_results = crawl_google_scholar()
        
        if not current_results:
            return {"success": False, "message": "No data retrieved from Google Scholar"}
        
        paths = get_data_paths()
        
        # Ensure directories exist
        os.makedirs(paths['history'], exist_ok=True)
        os.makedirs(paths['difference'], exist_ok=True)
        
        # Read previous data
        previous_file = get_last_added_file(paths['history'])
        previous_counts = {}
        
        if previous_file is not None:
            previous_file_path = os.path.join(paths['history'], previous_file)
            previous_counts = load_pickle_data(previous_file_path)
        
        # Calculate changes
        current_counts = {}
        today_sum = 0
        changes_detected = False
        
        for title in current_results:
            previous_citations = previous_counts.get(title, 0)
            current_citations = int(current_results[title])
            today_sum += current_citations
            
            # Check if there is an increase in the citation count
            if current_citations != previous_citations:
                changes_detected = True
                # Store the current citation count change
                current_counts[title] = current_citations - previous_citations
        
        # Save changes if any were detected
        if changes_detected and len(current_counts) > 0:
            today = time.strftime("%Y%m%d%H%M.csv")
            write_to_csv(current_counts, os.path.join(paths['difference'], today))
        
        # Always save the current total citation data
        today_total = time.strftime("%Y%m%d%H%M.pkl")
        write_to_pkl(current_results, os.path.join(paths['history'], today_total))
        
        return {
            "success": True, 
            "message": f"Data updated successfully. Total citations: {today_sum}",
            "total_citations": today_sum,
            "changes_detected": changes_detected,
            "papers_count": len(current_results)
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error updating data: {str(e)}"}

def load_pickle_data(file_path):
    """Load data from pickle file"""
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except:
        return {}

def load_csv_data(file_path):
    """Load data from CSV file"""
    data = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    title = row[0].strip()
                    count = int(row[1].strip()) if row[1].strip().isdigit() else 0
                    data[title] = count
    except:
        pass
    return data

def get_file_timestamp(filename):
    """Extract timestamp from filename"""
    try:
        return datetime.strptime(filename.split('.')[0], '%Y%m%d%H%M')
    except:
        return datetime.min

def get_all_historical_data():
    """Get all historical citation data"""
    paths = get_data_paths()
    history_files = glob.glob(os.path.join(paths['history'], '*.pkl'))
    
    historical_data = []
    for file_path in sorted(history_files):
        timestamp = get_file_timestamp(os.path.basename(file_path))
        data = load_pickle_data(file_path)
        if data:
            historical_data.append({
                'timestamp': timestamp,
                'data': data,
                'total_citations': sum(data.values())
            })
    
    return historical_data

def get_daily_changes():
    """Get daily citation changes"""
    paths = get_data_paths()
    diff_files = glob.glob(os.path.join(paths['difference'], '*.csv'))
    
    daily_changes = []
    for file_path in sorted(diff_files):
        timestamp = get_file_timestamp(os.path.basename(file_path))
        data = load_csv_data(file_path)
        if data:
            daily_changes.append({
                'timestamp': timestamp,
                'changes': data,
                'total_change': sum(data.values())
            })
    
    return daily_changes

def calculate_monthly_stats(historical_data):
    """Calculate monthly statistics"""
    monthly_stats = defaultdict(lambda: {'total': 0, 'papers': set(), 'count': 0})
    
    for entry in historical_data:
        month_key = entry['timestamp'].strftime('%Y-%m')
        monthly_stats[month_key]['total'] = entry['total_citations']
        monthly_stats[month_key]['papers'].update(entry['data'].keys())
        monthly_stats[month_key]['count'] += 1
    
    # Convert sets to counts
    for month in monthly_stats:
        monthly_stats[month]['paper_count'] = len(monthly_stats[month]['papers'])
        del monthly_stats[month]['papers']
    
    return dict(monthly_stats)

def get_top_papers(historical_data, limit=10):
    """Get top papers by current citation count"""
    if not historical_data:
        return []
    
    latest_data = historical_data[-1]['data']
    sorted_papers = sorted(latest_data.items(), key=lambda x: x[1], reverse=True)
    return sorted_papers[:limit]

def get_paper_trends(historical_data, paper_title):
    """Get citation trend for a specific paper"""
    trends = []
    for entry in historical_data:
        citations = entry['data'].get(paper_title, 0)
        trends.append({
            'timestamp': entry['timestamp'].strftime('%Y-%m-%d'),
            'citations': citations
        })
    return trends

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/summary')
def api_summary():
    """API endpoint for summary statistics"""
    historical_data = get_all_historical_data()
    daily_changes = get_daily_changes()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Current stats
    current_total = historical_data[-1]['total_citations']
    previous_total = historical_data[-2]['total_citations'] if len(historical_data) > 1 else current_total
    daily_change = current_total - previous_total
    
    # Recent changes (last 7 days)
    recent_changes = [change for change in daily_changes 
                     if change['timestamp'] >= datetime.now() - timedelta(days=7)]
    weekly_change = sum(change['total_change'] for change in recent_changes)
    
    # Monthly stats
    monthly_stats = calculate_monthly_stats(historical_data)
    
    # Top papers
    top_papers = get_top_papers(historical_data, 5)
    
    return jsonify({
        'current_total': current_total,
        'daily_change': daily_change,
        'weekly_change': weekly_change,
        'monthly_stats': monthly_stats,
        'top_papers': top_papers,
        'total_papers': len(historical_data[-1]['data']),
        'last_updated': historical_data[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')
    })

@app.route('/api/trends')
def api_trends():
    """API endpoint for citation trends"""
    historical_data = get_all_historical_data()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Overall trend
    overall_trend = []
    for entry in historical_data:
        overall_trend.append({
            'timestamp': entry['timestamp'].strftime('%Y-%m-%d'),
            'total_citations': entry['total_citations']
        })
    
    # Daily changes trend
    daily_changes = get_daily_changes()
    daily_trend = []
    for change in daily_changes:
        daily_trend.append({
            'timestamp': change['timestamp'].strftime('%Y-%m-%d'),
            'change': change['total_change']
        })
    
    return jsonify({
        'overall_trend': overall_trend,
        'daily_trend': daily_trend
    })

@app.route('/api/papers')
def api_papers():
    """API endpoint for paper data"""
    historical_data = get_all_historical_data()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    papers = []
    latest_data = historical_data[-1]['data']
    
    for title, citations in latest_data.items():
        # Get trend for this paper
        trend = get_paper_trends(historical_data, title)
        
        # Calculate recent change
        recent_change = 0
        if len(trend) > 1:
            recent_change = trend[-1]['citations'] - trend[-2]['citations']
        
        papers.append({
            'title': title,
            'current_citations': citations,
            'recent_change': recent_change,
            'trend': trend
        })
    
    # Sort by current citations
    papers.sort(key=lambda x: x['current_citations'], reverse=True)
    
    return jsonify({'papers': papers})

@app.route('/api/paper/<paper_title>')
def api_paper_detail(paper_title):
    """API endpoint for specific paper details"""
    historical_data = get_all_historical_data()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Find the paper
    latest_data = historical_data[-1]['data']
    if paper_title not in latest_data:
        return jsonify({'error': 'Paper not found'})
    
    # Get trend data
    trend = get_paper_trends(historical_data, paper_title)
    
    # Calculate statistics
    citations = [point['citations'] for point in trend]
    if len(citations) > 1:
        total_growth = citations[-1] - citations[0]
        avg_daily_growth = total_growth / len(citations) if len(citations) > 0 else 0
    else:
        total_growth = 0
        avg_daily_growth = 0
    
    return jsonify({
        'title': paper_title,
        'current_citations': latest_data[paper_title],
        'trend': trend,
        'total_growth': total_growth,
        'avg_daily_growth': round(avg_daily_growth, 2)
    })

@app.route('/api/export/csv')
def api_export_csv():
    """Export all data as CSV"""
    historical_data = get_all_historical_data()
    daily_changes = get_daily_changes()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Create CSV data
    csv_data = []
    
    # Add header
    csv_data.append(['Date', 'Total Citations', 'Daily Change', 'Paper Count'])
    
    # Add data rows
    for entry in historical_data:
        date_str = entry['timestamp'].strftime('%Y-%m-%d')
        total_citations = entry['total_citations']
        paper_count = len(entry['data'])
        
        # Find daily change for this date
        daily_change = 0
        for change in daily_changes:
            if change['timestamp'].date() == entry['timestamp'].date():
                daily_change = change['total_change']
                break
        
        csv_data.append([date_str, total_citations, daily_change, paper_count])
    
    # Convert to CSV string
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_data)
    csv_string = output.getvalue()
    output.close()
    
    return csv_string, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=citation_data.csv'
    }

@app.route('/api/export/papers')
def api_export_papers():
    """Export papers data as CSV"""
    historical_data = get_all_historical_data()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Get all unique papers
    all_papers = set()
    for entry in historical_data:
        all_papers.update(entry['data'].keys())
    
    # Create CSV data
    csv_data = []
    
    # Add header
    header = ['Paper Title', 'Current Citations']
    for entry in historical_data:
        header.append(entry['timestamp'].strftime('%Y-%m-%d'))
    csv_data.append(header)
    
    # Add data rows
    for paper in sorted(all_papers):
        row = [paper]
        
        # Get current citations
        current_citations = historical_data[-1]['data'].get(paper, 0)
        row.append(current_citations)
        
        # Get historical citations
        for entry in historical_data:
            citations = entry['data'].get(paper, 0)
            row.append(citations)
        
        csv_data.append(row)
    
    # Convert to CSV string
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_data)
    csv_string = output.getvalue()
    output.close()
    
    return csv_string, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=papers_data.csv'
    }

@app.route('/api/analytics')
def api_analytics():
    """Advanced analytics endpoint"""
    historical_data = get_all_historical_data()
    daily_changes = get_daily_changes()
    
    if not historical_data:
        return jsonify({'error': 'No data available'})
    
    # Calculate various metrics
    total_citations = [entry['total_citations'] for entry in historical_data]
    daily_changes_list = [change['total_change'] for change in daily_changes]
    
    # Growth metrics
    total_growth = total_citations[-1] - total_citations[0] if len(total_citations) > 1 else 0
    avg_daily_growth = total_growth / len(total_citations) if len(total_citations) > 1 else 0
    
    # Best and worst days
    if daily_changes_list:
        best_day = max(daily_changes_list)
        worst_day = min(daily_changes_list)
        avg_daily_change = statistics.mean(daily_changes_list)
    else:
        best_day = worst_day = avg_daily_change = 0
    
    # Paper statistics
    latest_papers = historical_data[-1]['data']
    paper_citations = list(latest_papers.values())
    
    if paper_citations:
        most_cited = max(latest_papers.items(), key=lambda x: x[1])
        least_cited = min(latest_papers.items(), key=lambda x: x[1])
        avg_citations_per_paper = statistics.mean(paper_citations)
        median_citations = statistics.median(paper_citations)
    else:
        most_cited = least_cited = ("", 0)
        avg_citations_per_paper = median_citations = 0
    
    # Recent activity (last 30 days)
    recent_cutoff = datetime.now() - timedelta(days=30)
    recent_changes = [change for change in daily_changes 
                     if change['timestamp'] >= recent_cutoff]
    recent_growth = sum(change['total_change'] for change in recent_changes)
    
    return jsonify({
        'total_growth': total_growth,
        'avg_daily_growth': round(avg_daily_growth, 2),
        'best_day': best_day,
        'worst_day': worst_day,
        'avg_daily_change': round(avg_daily_change, 2),
        'most_cited_paper': {
            'title': most_cited[0],
            'citations': most_cited[1]
        },
        'least_cited_paper': {
            'title': least_cited[0],
            'citations': least_cited[1]
        },
        'avg_citations_per_paper': round(avg_citations_per_paper, 2),
        'median_citations': round(median_citations, 2),
        'recent_growth_30_days': recent_growth,
        'total_papers': len(latest_papers),
        'data_points': len(historical_data)
    })

@app.route('/api/update', methods=['POST'])
def api_update_data():
    """Update citation data from Google Scholar"""
    try:
        result = update_citation_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating data: {str(e)}"})

@app.route('/api/status')
def api_status():
    """Get current data status and last update time"""
    historical_data = get_all_historical_data()
    
    if not historical_data:
        return jsonify({
            'has_data': False,
            'last_update': None,
            'total_citations': 0,
            'papers_count': 0
        })
    
    latest_entry = historical_data[-1]
    return jsonify({
        'has_data': True,
        'last_update': latest_entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
        'total_citations': latest_entry['total_citations'],
        'papers_count': len(latest_entry['data'])
    })

if __name__ == '__main__':
    app.run(debug=DEBUG, host=HOST, port=PORT)