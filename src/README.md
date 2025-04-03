# README Main script

## Project Overview
This project extracts and analyzes team transition data from a football (soccer) database. The goal is to track ball possession losses and subsequent defensive actions within a specified timeframe. The extracted data is stored in CSV format for further analysis.

## Prerequisites
Ensure the following Python libraries are installed before running the script:

```bash
pip install pandas numpy matplotlib seaborn tabulate
```

Additionally, ensure you have a working `util` module that provides a `DatabaseConnection` class for database interaction.

## Directory Setup
The script automatically creates an output directory:
- `features/` (used for storing feature-related files, but does not modify the database)

## How to Run the Script
1. Ensure the database connection is correctly configured in `util.DatabaseConnection()`.
2. Run the script using:

   ```bash
   python Main.py
   ```
3. The script will process data for all teams and output results.

## Database Queries and Logic
The script follows these steps:
1. Fetch all team IDs from the `teams` table.
2. Identify ball possession losses and subsequent team actions.
3. Categorize movements and defensive actions.
4. Store all processed data into a structured CSV file.

## Output
- **CSV File:** `all_teams_transition_data.csv` (contains transition-related actions for all teams)
- **Console Output:** Displays summary statistics and formatted tables for quick review.

## Sample Output
For each team, the script prints:
```
Processing team: Club Brugge
Found 10417 actions for Club Brugge
```
This confirms the number of actions retrieved per team.

