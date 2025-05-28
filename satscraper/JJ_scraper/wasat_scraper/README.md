# WASAT Case Scraper

A comprehensive tool for scraping, downloading, and parsing cases from the Western Australia State Administrative Tribunal (WASAT). This project enables legal researchers and practitioners to efficiently access and analyze WASAT case data.

## Features

- Scrapes case metadata from the WASAT website
- Downloads full HTML case documents
- Checks for corrupted or incomplete case files
- Parses HTML into structured JSON format
- Extracts metadata, citations, and decision content
- Prepares data for vector database integration
- Monitors RSS feeds for case updates

## Directory Structure

```
wasat_scraper/
├── data/
│   ├── raw/
│   │   ├── wasat_cases.csv         # Primary case metadata
│   │   ├── db_stats.csv            # Database statistics
│   │   ├── available_years.csv     # Available years list
│   │   └── rss_feeds/              # RSS feed data
│   │       ├── latest.xml          # Most recent RSS feed
│   │       └── YYYYMMDD.xml        # Historical RSS feeds
│   ├── html/
│   │   └── by_year/                # Organized by year
│   │       ├── YYYY/
│   │       │   ├── 1.html          # Named by case number
│   │       │   ├── 2.html      
│   │       │   └── ...
│   │       └── ...
│   └── parsed/                     # Parsed data output
│       └── json/                   # Initial structured data
│           └── YYYY/               # Organized by year
│               ├── 1.json          # Named by case number
│               ├── 2.json
│               └── ...
├── neo4j_aura_api/                 # Neo4j Aura API package
│   ├── neo4j_aura_api.py           # Main API implementation
│   ├── import_to_neo4j_aura.py     # Import data to Neo4j
│   ├── query_neo4j_aura.py         # Query utility for Neo4j
│   ├── static/                     # Static files for web UI
│   ├── templates/                  # HTML templates
│   └── README.md                   # Package documentation
├── scripts/
│   ├── setup.py                    # Initial project setup
│   ├── wasat_case_manager.py       # Case metadata manager
│   ├── html_downloader.py          # HTML content downloader
│   ├── check_empty_html.py         # Quality checker
│   ├── parser.py                   # HTML parser
│   └── rss_monitor.py              # RSS update monitor
├── logs/
│   ├── setup_logs.txt              # Setup logs
│   ├── scrape_logs.txt             # Scraper logs
│   ├── download_logs.txt           # Downloader logs
│   ├── parser_logs.txt             # Parser logs
│   ├── check_html_logs.txt         # HTML checker logs
│   ├── problematic_html_files.txt  # List of problem files
│   └── error_logs.txt              # Error logs
├── config.py                       # Configuration settings
├── requirements.txt                # Dependencies
└── README.md                       # Project documentation
```

## Neo4j Aura API Server

The project includes a Neo4j Aura API Server that provides a REST API for accessing the WASAT case database stored in Neo4j Aura.

### Installation and Usage

#### Option 1: Using the Run Script (Simplest)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server using the provided script
./run_api_server.sh
```

#### Option 2: Manual Execution

```bash
# Go to the neo4j_aura_api directory
cd neo4j_aura_api

# Install dependencies
pip install -r requirements.txt

# Run the API server directly
python app.py --uri neo4j+s://3d34e9d7.databases.neo4j.io --user neo4j --password wXydxCfCnWMZINiNbm0jhAzzWwbW5yjQkvjGdGd7DWw --port 5000
```

You can then access:
- API endpoints at http://localhost:5000/api/
- Web visualizer at http://localhost:5000/visualizer

For more details, see the [Neo4j Aura API README](neo4j_aura_api/README.md).

## Usage

1. **Initial Setup:**
   ```bash
   python setup.py
   ```
   This creates the necessary directory structure and configuration files for the project.

2. **Manage Case Metadata:**
   ```bash
   python scripts/wasat_case_manager.py
   ```
   Scrapes the WASAT website to collect case metadata and saves it to CSV.
   
   For RSS updates only:
   ```bash
   python scripts/wasat_case_manager.py rss
   ```

3. **Download HTML Content:**
   ```bash
   python scripts/html_downloader.py [--limit N] [--workers N] [--new-only]
   ```
   Downloads HTML content for cases listed in the metadata CSV.
   - `--limit N`: Limit downloads to first N cases (useful for testing)
   - `--workers N`: Set number of concurrent downloads (default: 5)
   - `--new-only`: Only download cases that haven't been downloaded yet (useful after RSS updates)

4. **Check HTML Quality:**
   ```bash
   python scripts/check_empty_html.py [--sample N] [--fix]
   ```
   Checks for empty or corrupted HTML files and identifies problematic cases.
   - `--sample N`: Number of files to check content for (default: 10)
   - `--fix`: Attempt to re-download problematic files

5. **Parse HTML Content:**
   ```bash
   python scripts/parser.py [--year YYYY] [--case NUMBER] [--limit N] [--debug]
   ```
   Parses HTML files into structured JSON data.
   - `--year YYYY`: Process files from a specific year only
   - `--case NUMBER`: Process a specific case number only
   - `--limit N`: Limit processing to N files
   - `--debug`: Enable detailed debug logging

6. **Process Parsed JSON:**
   ```bash
   python scripts/parser_json.py [--config CONFIG_FILE] [--year YYYY] [--case NUMBER]
   ```
   Processes parsed JSON files to standardize metadata and prepare for vector database use.
   - `--config CONFIG_FILE`: Use a custom configuration file
   - `--year YYYY`: Process files from a specific year
   - `--case NUMBER`: Process a specific case number

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wasat_scraper.git
   cd wasat_scraper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the setup script:
   ```bash
   python setup.py
   ```

## Requirements

- Python 3.7+
- Dependencies:
  - beautifulsoup4>=4.11.0
  - requests>=2.28.0
  - pandas>=1.4.0
  - lxml>=4.8.0

## Data Structure

### Case Metadata
The primary case metadata is stored in `data/raw/wasat_cases.csv` with the following fields:
- `case_number`: Unique identifier for the case
- `citation`: Official citation (e.g., "[2023] WASAT 42")
- `title`: Case title or name
- `decision_date`: Date of the decision (YYYY-MM-DD)
- `url`: URL to the original case on AustLII

### Parsed JSON
Each parsed case JSON file contains:
- `case_number`: Case identifier
- `year`: Year of the decision
- `metadata`: Extracted metadata including citation, parties, legislation, etc.
- `decisions`: Array of decision sections with titles and content

### Processed Data
The processed data includes:
- Standardized metadata with consistent field names
- Extracted decision content organized by sections
- Vector-ready documents chunked for embedding

## Workflow Examples

### Initial Data Collection

```bash
# Set up the project
python scripts/setup.py

# Collect metadata from all available years
python scripts/wasat_case_manager.py

# Download all HTML content
python scripts/html_downloader.py

# Parse HTML into structured data
python scripts/parser.py
```

### Regular Updates

```bash
# Get latest RSS updates for new cases
python scripts/wasat_case_manager.py rss

# Download only the new cases
python scripts/html_downloader.py --new-only

# Parse the new HTML files
python scripts/parser.py
```

### Daily Maintenance (for automated jobs)

```bash
# Add to your crontab for daily updates
# Example cron entry (runs at 2 AM daily):
# 0 2 * * * cd /path/to/wasat_scraper && python scripts/wasat_case_manager.py rss && python scripts/html_downloader.py --new-only
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [AustLII](https://www.austlii.edu.au/) for providing access to legal information
- Western Australia State Administrative Tribunal (WASAT) for publishing decisions