import numpy as np
import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
from util import DatabaseConnection

def calculate_team_compactness(player_positions):
    positions = np.array([[p['x'], p['y']] for p in player_positions])
    if len(positions) < 3:
        return 0

    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(positions)
        return hull.volume
    except:
        x_range = np.max(positions[:, 0]) - np.min(positions[:, 0])
        y_range = np.max(positions[:, 1]) - np.min(positions[:, 1])
        return x_range * y_range


def get_player_positions(db_connection, game_id, team_id, timestamp):
    query = f"""
    SELECT pt.player_id, p.player_name, pt.x, pt.y 
    FROM player_tracking pt
    JOIN players p ON pt.player_id = p.player_id
    WHERE pt.game_id = '{game_id}'
    AND p.team_id = '{team_id}'
    AND pt.timestamp = '{timestamp}'
    """

    result_df = db_connection.execute_query(query)

    if result_df is None or result_df.empty:
        print(f"No data found for game_id={game_id}, team_id={team_id}, timestamp={timestamp}")
        return []

    player_positions = []
    for _, row in result_df.iterrows():
        player_positions.append({
            'player_id': row['player_id'],
            'player_name': row['player_name'],
            'x': row['x'],
            'y': row['y']
        })

    return player_positions


def visualize_team_compactness(player_positions, compactness_value):

    positions = np.array([[p['x'], p['y']] for p in player_positions])

    plt.figure(figsize=(10, 8))

    plt.scatter(positions[:, 0], positions[:, 1], color='blue', s=100, label='Players')

    for p in player_positions:
        plt.annotate(p['player_name'], (p['x'], p['y']), xytext=(5, 5),
                     textcoords='offset points')

    if len(positions) >= 3:
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(positions)
            for simplex in hull.simplices:
                plt.plot(positions[simplex, 0], positions[simplex, 1], 'r-')

            hull_points = positions[hull.vertices]
            plt.fill(hull_points[:, 0], hull_points[:, 1], alpha=0.3, color='red')
        except:
            min_x, min_y = np.min(positions, axis=0)
            max_x, max_y = np.max(positions, axis=0)
            plt.plot([min_x, max_x, max_x, min_x, min_x],
                     [min_y, min_y, max_y, max_y, min_y], 'r-')
            plt.fill([min_x, max_x, max_x, min_x],
                     [min_y, min_y, max_y, max_y], alpha=0.3, color='red')

    plt.title(f'Team Formation - Compactness: {compactness_value:.2f} square units')
    plt.xlabel('X Position')
    plt.ylabel('Y Position')
    plt.grid(True)
    plt.axis('equal')
    plt.legend()
    plt.tight_layout()

    return plt


def calculate_compactness_over_time(db_connection, game_id, team_id, start_time, end_time, interval):
    query = f"""
    SELECT DISTINCT pt.timestamp
    FROM player_tracking pt
    JOIN players p ON pt.player_id = p.player_id
    WHERE pt.game_id = '{game_id}'
    AND p.team_id = '{team_id}'
    AND pt.timestamp BETWEEN '{start_time}' AND '{end_time}'
    ORDER BY pt.timestamp
    """

    timestamps_df = db_connection.execute_query(query)

    if timestamps_df is None or timestamps_df.empty:
        print(f"No timestamps found for the specified range")
        return {}

    compactness_over_time = {}

    for _, row in timestamps_df.iterrows():
        timestamp = row['timestamp']
        player_positions = get_player_positions(db_connection, game_id, team_id, timestamp)

        if player_positions:
            compactness = calculate_team_compactness(player_positions)
            compactness_over_time[timestamp] = compactness
            print(f"Timestamp: {timestamp}, Compactness: {compactness:.2f}")

    return compactness_over_time


def main():
    db = DatabaseConnection()

    game_id = '5oc8drrbruovbuiriyhdyiyok'
    team_id = '1oyb7oym5nwzny8vxf03szd2h'
    timestamp = '0 days 00:00:00'

    player_positions = get_player_positions(db, game_id, team_id, timestamp)

    if player_positions:
        compactness = calculate_team_compactness(player_positions)
        print(f"Team compactness at timestamp {timestamp}: {compactness:.2f} square units")

        # Visualize the results
        plt_figure = visualize_team_compactness(player_positions, compactness)
        plt_figure.savefig('team_compactness.png')
        plt.show()

    db.close()


if __name__ == "__main__":
    main()