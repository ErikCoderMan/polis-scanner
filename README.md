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
    POLIS_SCANNER_POLL_INTERVAL=120s
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

    poll [start <interval> | stop]
        Repeatedly runs the refresh command at a fixed interval.

        Interval format: <int>[s|m|h|d]
        (seconds, minutes, hours, days).
        Examples: 30s, 5m, 1h, 2d.

        Recommended minimum interval: 60s.
        Minimum allowed interval: 10s.
        Use with care to avoid rate limiting.

    load
        Display events stored in local storage.

    more <id>
        Show full details for a specific event by its ID.

    find <text>
        Quick search using strict filtering (default behavior).
        Only events matching all words are returned.

    search [options]
        Advanced search with filtering, sorting, ranking and limits.

        Default mode: strict filtering (no relevance scoring).
        Only exact matches are returned unless --strict false is used.

        To enable relevance ranking:
            --strict false

    rank --group <field> [options]
        Group events by a field and display statistics.

        Filters (--text, --fields, --filters) are applied before grouping.

        Default sorting:
            If --text is used → avg_score, count, group
            Otherwise        → count, group

Search options:
    --text <text>
        Match all words in the specified fields.

    --fields <field1 field2 ...>
        Fields used for text matching.
        Default: name, summary, type, location.name.

    --filters <field1 value1 field2 value2 ...>
        Exact field-value filtering.

    --sort <field1 field2 ...>
        Sort events by specified event fields.
        Examples:
            score
            datetime
            name
            type
            location.name

        Multiple fields can be provided in priority order.

    --limit <n>
        Limit the number of returned results.

    --strict <true|false>
        true  (default)  → hard filtering only
        false            → enable relevance scoring and ranking

Rank options:
    --group <field>
        Field used for grouping.

    --text <text>
        Apply text filtering before grouping.

    --fields <field1 field2 ...>
        Fields used for text filtering.

    --filters <field1 value1 ...>
        Exact field-value filters before grouping.

    --sort <field1 field2 ...>
        Sort grouped results.
        Available fields:
            count
            avg_score
            group

        Multiple fields can be provided in priority order.

    --limit <n>
        Limit number of groups returned.
    
    --strict <true|false>
        true  (default)  → hard filtering only
        false            → enable relevance scoring and ranking
        
Other:
    help
        Display this help message.

    clear
        Clear the output screen.

    exit / quit
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
