# polis-scanner
Python project that shows swedish crime events data using swedish police public API
## Overview  
polis-scanner is a CLI-based event scanner that fetches and stores public police event data from an external API.
The application supports searching, filtering, ranking, and browsing stored events through an interactive terminal UI.

Features include
- Background event fetching and local caching
- Interactive CLI with log-buffered output
- Search engine with scoring-based ranking
- Group statistics mode
- Command history navigation
- Animated title bar in the terminal UI

## Installation
During installation replace `python3` with either `python`, `python3`, `py`  
depending on your system.  

1. Clone repository and navigate into project root directory  
using either Linux terminal or Windows PowerShell:
```
git clone https://github.com/ErikCoderMan/polis-scanner.git
cd polis-scanner
```
2. Create and activate virtual environment
   - Windows (PowerShell)  
     ```
     python3 -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - Linux (Terminal)  
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install dependencies
```
pip install -r requirements.txt
```

## Configuration

(Optional) Create a file called `.env` in the project root if you want custom settings.

Example

    POLIS_SCANNER_NAME=polis-scanner
    POLIS_SCANNER_VERSION=0.0.1
    POLIS_SCANNER_DATA_DIR=data
    POLIS_SCANNER_LOGS_DIR=data/logs
    POLIS_SCANNER_CACHE_DIR=data/cache
    POLIS_SCANNER_POLIS_EVENT_URL=https://polisen.se/api/events
    POLIS_SCANNER_POLL_INTERVALL_S=60
    POLIS_SCANNER_HTTP_TIMEOUT_S=10

## Running the application
Replace `python3` with either `python`, `python3`, `py`  
depending on your system.
### CLI mode (default)

    python3 main.py

### GUI mode (planned)

    python3 main.py --gui

    GUI is not yet implemented

### Commands
```
Commands:
    refresh
        Fetch the latest events from the API.
    load
        Display stored events from local storage.
    more <id>
        Show full details for a specific event by its ID.
    find <text>
        Quick search for events containing the given text.
        Results are displayed in reverse order; the best matches appear at the bottom.
    search [options]
        Advanced search with filters, sorting, and limits.
        Results are displayed in reverse order; top match appears last.
    rank --group <field> [options]
        Show grouped statistics (counts) for a specified field.
        Filters (--text, --fields, --filters) are applied before grouping.
        Ranked groups are displayed in reverse order; group with highest count appears at the bottom.

Search options:
    --text <text>
        Search for specific words in event fields (default behavior).
    --fields <field1 field2 ...>
        Specify which event fields to search in (default: name, summary, type, location.name).
    --filters <field1 value1 field2 value2 ...>
        Filter events by exact matches for specified fields.
    --sort <value>
        score      - sort by relevance score (default)
        -datetime  - sort by datetime, newest first
    --limit <n>
        Limit the number of results returned.

Rank options:
    --group <field>
        Specify the field to group by for statistics.
    --sort <value>
        -count     - sort groups by count (default)
        <field>    - sort groups alphabetically by field value
    --text <text>
        Filter events by text before grouping.
    --fields <field1 field2 ...>
        Specify which fields to search in for filtering before grouping.
    --filters <field1 value1 ...>
        Filter events by exact matches before grouping.
    --limit <n>
        Limit the number of ranked groups returned.

Other:
    help
        Display this help message.
    exit
        Quit the program.
```
#### Examples

   `search --text polis --filters type brand location.name stockholm --limit 3`  
   `find brand stockholm`  
   `rank --group location.name --filters type brand`  

### UI Controls

    Enter
        Execute command

    PageUp
        Scroll output up

    PageDown
        Scroll output down

    Ctrl+C
        Exit application

## Logging

    Logs are written both to
    - Terminal UI buffer
    - Rotating log files in the data directory

## Architecture Notes

    Async event fetching with retry backoff
    Thread-safe log buffer using locks
    Modular separation between API, services, CLI, and utilities

## License

    Free to use for personal purposes. The software is provided without warranty and comes with no guarantees of support or reliability.  
    Use at your own risk.
