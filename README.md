# Scholar Citation Tracker Web Application

A comprehensive web application for tracking and visualizing Google Scholar citation metrics with beautiful dashboards and analytics.

## Features

### 📊 **Dashboard Overview**
- **Real-time Statistics**: Total citations, daily/weekly changes, paper count
- **Interactive Charts**: Citation trends over time with smooth animations
- **Top Papers**: Quick view of most cited publications
- **Daily Changes**: Bar chart showing daily citation increases
- **Live Data Updates**: One-click update from Google Scholar with real-time status

### 📈 **Advanced Analytics**
- **Growth Metrics**: Total growth, average daily growth, best/worst days
- **Paper Statistics**: Most/least cited papers, average citations per paper
- **Recent Activity**: 30-day growth tracking
- **Trend Analysis**: Individual paper citation trends

### 📋 **Paper Management**
- **Comprehensive Table**: All papers with current citations and recent changes
- **Sorting Options**: By citations, recent change, or title
- **Individual Details**: Click any paper for detailed trend analysis
- **Mini Trend Charts**: Visual trend indicators in the table

### 📤 **Data Export**
- **CSV Export**: Download complete citation data
- **Papers Export**: Export individual paper trends
- **Analytics Export**: Advanced metrics and statistics

### 🔄 **Integrated Data Management**
- **Google Scholar Integration**: Direct scraping and data collection
- **Automatic Updates**: One-click refresh from Google Scholar
- **Real-time Status**: Live update indicators and notifications
- **Data Synchronization**: Automatic comparison with previous data
- **Change Detection**: Only saves when citations actually change

### 🎨 **Visualization Features**
- **Interactive Charts**: Built with Chart.js for smooth interactions
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern UI**: Bootstrap 5 with custom styling
- **Real-time Updates**: Auto-refresh every 5 minutes

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Dashboard**:
   Open your browser and go to `http://localhost:8080`

## Data Structure

The application reads data from two directories:
- `history/`: Contains timestamped pickle files with complete citation snapshots
- `difference/`: Contains CSV files with daily citation changes

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/summary` - Summary statistics
- `GET /api/trends` - Citation trend data
- `GET /api/papers` - All papers data
- `GET /api/paper/<title>` - Individual paper details
- `GET /api/export/csv` - Export citation data as CSV
- `GET /api/export/papers` - Export papers data as CSV
- `GET /api/analytics` - Advanced analytics
- `POST /api/update` - Update data from Google Scholar
- `GET /api/status` - Get current data status

## Cool Visualization Methods

### 1. **Smooth Line Charts**
- Citation trends with tension curves for natural flow
- Interactive tooltips showing exact values
- Color-coded positive/negative changes

### 2. **Mini Trend Charts**
- Inline trend visualization in the papers table
- Quick visual assessment of paper performance
- Responsive design that scales with screen size

### 3. **Animated Number Changes**
- Numbers animate when values change
- Visual feedback for data updates
- Smooth transitions for better UX

### 4. **Color-Coded Metrics**
- Green for positive changes
- Red for negative changes
- Blue for neutral/stable values
- Consistent color scheme throughout

### 5. **Interactive Modals**
- Detailed paper analysis with full trend charts
- Advanced analytics with comprehensive metrics
- Smooth modal transitions and animations

### 6. **Responsive Cards**
- Hover effects with elevation changes
- Gradient headers for visual appeal
- Consistent spacing and typography

## Suggested Additional Functionalities

### 🔮 **Future Enhancements**

1. **Prediction Models**
   - Machine learning-based citation prediction
   - Trend forecasting with confidence intervals
   - Growth rate projections

2. **Comparative Analysis**
   - Compare with other researchers
   - Benchmark against field averages
   - Relative performance metrics

3. **Advanced Filtering**
   - Filter papers by research area
   - Date range selection
   - Citation threshold filters

4. **Social Features**
   - Share achievements on social media
   - Generate citation reports
   - Export to academic profiles

5. **Real-time Notifications**
   - Email alerts for significant changes
   - Webhook integrations
   - Mobile push notifications

6. **Data Visualization Enhancements**
   - Heat maps for citation patterns
   - Network graphs for co-authorship
   - Geographic citation maps

7. **Advanced Analytics**
   - H-index calculations
   - Impact factor analysis
   - Research area clustering

8. **Integration Features**
   - ORCID integration
   - Google Scholar API (when available)
   - ResearchGate synchronization

## Technical Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Charts**: Chart.js
- **UI Framework**: Bootstrap 5
- **Icons**: Font Awesome 6
- **Data Storage**: CSV files and Pickle files

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

This project is open source and available under the MIT License.