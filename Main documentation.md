# MAIN QUERY COLUMN DOCUMENTATION'

## Overview

This SQL query analyzes defensive transitions in soccer matches by tracking events that occur in the 10 seconds after a team loses possession. The query identifies possession loss moments and provides detailed information about player actions, field positions, movement directions, and defensive success during the transition phase.

## Column Descriptions

### Possession Loss Information

| Column | Data Type | Description |
|--------|-----------|-------------|
| `loss_event_id` | integer | Unique identifier of the action where possession was lost |
| `game_id` | text | Unique identifier for the match |
| `period_id` | integer | Period of the match (1 = first half, 2 = second half, 3 = first extra time, 4 = second extra time) |
| `loss_time` | float | Time in seconds when possession was lost |
| `team_losing_ball` | text | Team ID of the team that lost possession |
| `team_gaining_ball` | text | Team ID of the team that gained possession |
| `loss_x` | float | X-coordinate on the pitch where possession was lost (0-105m) |
| `loss_y` | float | Y-coordinate on the pitch where possession was lost (0-68m) |

### Action Information

| Column | Data Type | Description |
|--------|-----------|-------------|
| `action_id` | integer | Unique identifier for the action |
| `seconds_after_loss` | float | Time in seconds between the possession loss and this action |
| `team_id` | text | Team ID of the team performing this action |
| `team_name` | text | Name of the team performing this action |
| `player_id` | text | Unique identifier of the player performing the action |
| `player_name` | text | Name of the player performing the action |
| `action_type` | text | Type of action performed (e.g., '9' = tackle, '10' = interception, '18' = clearance) |
| `result` | text | Result of the action ('1' = success, '0' = fail) |
| `start_x` | float | Starting X-coordinate of the action (0-105m) |
| `start_y` | float | Starting Y-coordinate of the action (0-68m) |
| `end_x` | float | Ending X-coordinate of the action (0-105m) |
| `end_y` | float | Ending Y-coordinate of the action (0-68m) |

### Spatial Analysis Columns

| Column | Data Type | Description |
|--------|-----------|-------------|
| `movement_direction` | text | Direction of player movement during the action: <br>• 'FORWARD' = Moving toward opponent's goal<br>• 'BACKWARD' = Moving toward own goal<br>• 'NEUTRAL' = No significant movement in attacking/defending direction |
| `x_sector` | text | Field sector based on the X-coordinate:<br>• 'DEFENSIVE_THIRD' = 0-35m (own goal side)<br>• 'MIDDLE_THIRD' = 35-70m (middle of pitch)<br>• 'ATTACKING_THIRD' = 70-105m (opponent's goal side) |
| `y_sector` | text | Field sector based on the Y-coordinate:<br>• 'LEFT_WING' = 0-22.67m (left side of pitch)<br>• 'CENTER' = 22.67-45.33m (center of pitch)<br>• 'RIGHT_WING' = 45.33-68m (right side of pitch) |
| `game_direction` | text | Overall game play direction:<br>• 'LEFT_TO_RIGHT' = First team attacks from left to right in period 1<br>• 'RIGHT_TO_LEFT' = First team attacks from right to left in period 1 |

### Defensive Success Metrics

| Column | Data Type | Description |
|--------|-----------|-------------|
| `successful_defensive_action` | boolean | Whether this specific action is a successful defensive action:<br>• TRUE = This action is a successful tackle, interception, or clearance<br>• FALSE = This action is not a successful defensive action |
| `defensive_success` | boolean | Whether any successful defensive action occurred after this possession loss:<br>• TRUE = At least one successful defensive action occurred in the 10-second window<br>• FALSE = No successful defensive actions occurred in the 10-second window |
| `time_to_defensive_action` | float | Time in seconds between possession loss and the first successful defensive action (NULL if no successful defensive action occurred) |

## Understanding the Query Logic

### 1. Identifying Possession Changes

The query identifies possession changes by analyzing consecutive actions in chronological order. A possession change occurs when the team ID of one action differs from the team ID of the next action.

### 2. Determining Game Direction

Soccer teams switch sides at halftime. The query determines the initial game direction based on the first action of the match and then accounts for the side-switching in periods 2 and 4.

### 3. Movement Direction Calculation

The `movement_direction` column considers:
- Which period it is (teams play in opposite directions in periods 1/3 vs. 2/4)
- The original game direction (which team starts playing from left to right)
- Which team the player belongs to (attacking team or defending team)
- The change in x-coordinates (start_x vs. end_x)

### 4. Defensive Actions

The query considers three types of defensive actions:
- Tackles (action_type = '9')
- Interceptions (action_type = '10')
- Clearances (action_type = '18')

An action is a successful defensive action if it's one of these types AND has a result of '1' (success).

### 5. Two Levels of Analysis

The query provides both:
- **Row-level information**: Each action is analyzed individually
- **Transition-level aggregations**: Success metrics are calculated for the entire 10-second window

## Important Notes for Analysis

1. **Movement Direction**: The movement direction is relative to the attacking direction of the team. A defender moving "FORWARD" means they are moving toward the opponent's goal, which is the direction of attack.

2. **Defensive Success vs. Successful Defensive Action**:
   - `successful_defensive_action` identifies specific actions that are successful defensive actions
   - `defensive_success` indicates whether any successful defensive action occurred during the transition
   - It's possible to have `successful_defensive_action = FALSE` but `defensive_success = TRUE` if the action isn't a defensive action itself but the transition includes a successful defensive action elsewhere

3. **X and Y Sector Definitions**:
   - The sectors are defined based on absolute pitch coordinates
   - They do not change based on which direction a team is playing

4. **Period ID Values**:
   - Period 1: First half
   - Period 2: Second half
   - Period 3: First half of extra time
   - Period 4: Second half of extra time

## Example Usage Scenarios

1. **Analyzing Defensive Pressing Effectiveness**:
   ```sql
   SELECT 
       team_name,
       COUNT(*) AS total_transitions,
       SUM(CASE WHEN defensive_success THEN 1 ELSE 0 END) AS successful_transitions,
       ROUND(100.0 * SUM(CASE WHEN defensive_success THEN 1 ELSE 0 END) / COUNT(*), 2) AS success_percentage,
       AVG(CASE WHEN defensive_success THEN time_to_defensive_action ELSE NULL END) AS avg_recovery_time
   FROM your_query_result
   GROUP BY team_name
   ORDER BY success_percentage DESC;
   ```

2. **Field Zones Where Possession is Recovered**:
   ```sql
   SELECT 
       x_sector, 
       y_sector, 
       COUNT(*) AS recovery_count
   FROM your_query_result
   WHERE successful_defensive_action
   GROUP BY x_sector, y_sector
   ORDER BY recovery_count DESC;
   ```

3. **Analyzing Movement Patterns After Possession Loss**:
   ```sql
   SELECT 
       team_name,
       movement_direction,
       COUNT(*) AS action_count
   FROM your_query_result
   WHERE team_id = team_losing_ball
   GROUP BY team_name, movement_direction
   ORDER BY team_name, action_count DESC;
   ```
