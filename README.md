# polis-scanner
Python project that shows swedish crime events data using swedish police public API
## Overview  
polis-scanner is a both GUI and CLI based event scanner that fetches and stores  
public police event data from an external API.  

The application supports searching, filtering, ranking, and browsing  
stored events through an interactive terminal UI.

Features include
- Background event fetching and local caching
- Interactive GUI or CLI with log-buffered output
- Direct command mode support using command arguments from terminal  
  (this also makes the project scriptable)
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
2. Create and activate virtual environment:  
 - Windows (PowerShell):  
```
python3 -m venv .venv
.venv\Scripts\Activate.ps1
```
- Linux (Terminal):  
```
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

## Configuration

(Optional) Create a file called `.env` in the project root if you want custom settings.

Example (check src.core.config for more):

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

Execute following from project root:  
### GUI mode (default)
    python3 main.py

### CLI mode
    python3 main.py --gui

### Direct CLI mode
    python3 main.py <command> [args]

### Commands
```
Category Data:
    find <text>
        Quick search using strict filtering (default behavior).
        Only events matching all words are returned.
        Example:
            find brand stockholm

    load
        Display events stored in local storage.

    more <id>
        Show full details for a specific event by its ID.

    rank --group <field> [options]
        Group events by a field and display statistics.
        Options:
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
                Available fields: count, avg_score, group
                Multiple fields can be provided in priority order.
            --limit <n>
                Limit number of groups returned.
            --strict <true|false>
                true  (default)  → hard filtering only
                false            → enable relevance scoring and ranking
        Example:
           rank --group location.name --filters type brand

    refresh
        Fetch the latest events from the API.

    search [options]
        Advanced search with filtering, sorting and limit.
        Options:
            --text <text>
                Match all words in the specified fields.
            --fields <field1 field2 ...>
                Fields used for text matching.
                (Default all): name, summary, type, location.name.
            --filters <field1 value1 field2 value2 ...>
                Exact field-value filtering.
            --sort <field1 field2 ...>
                Sort events by specified event fields.
                Examples: score, datetime, name, type, location.name
                Multiple fields can be provided in priority order.
            --limit <n>
                Limit the number of returned results.
            --strict <true|false>
                true  (default)  → hard filtering only
                false            → enable relevance scoring and ranking
        Example:
           search --text polis --filters type brand location.name stockholm --limit 3

Category Tasks:
    kill <name>
        Stop a running task.

    poll [interval]
        Repeatedly refresh events at a fixed interval.
        Interval format: <int>[s|m|h|d]
        (seconds, minutes, hours, days).
        Example interval values: 30s, 5m, 1h, 2d.

    tasks
        List running background tasks.  

Category Other:
    clear
        Clear the output screen.

    exit / quit [now]
        Quit the program.
        Options:
            now            → Do not wait for background tasks, quit immediately
            (no arguments) → Program will make a clean exit and properly close tasks

    help [prefix1 prefix2 prefix3 ...]
        Display help for all commands or a filtered subset.
        If one or more command prefixes are provided, only commands
        starting with those prefixes are shown.
        If no arguments are given, all commands are listed.
        Examples:
            help po tas find    → shows: poll, tasks, find
            help refresh        → shows: refresh
            help                → shows all commands

```
#### Examples
   `refresh`  
   `more 123456`  
   `search --text polis --filters type brand location.name stockholm --limit 3`  
   `find brand stockholm`  
   `rank --group location.name --filters type brand`  
   `poll 5m`  
   `tasks`  
   `kill poll`  

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
    Modular separation between API, services, GUI/CLI, and utilities

## License

    Free to use for personal purposes. 
    The software is provided without warranty 
    and comes with no guarantees of support or reliability.  

    Use at your own risk.
