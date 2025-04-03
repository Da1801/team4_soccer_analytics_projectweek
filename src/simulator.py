import matplotlib.pyplot as plt
from mplsoccer import Pitch
import pandas as pd
import numpy as np
from matplotlib.animation import FuncAnimation
from util import DatabaseConnection
import matplotlib as mpl
mpl.use('TkAgg')

'''
Uses DatabaseConnection class from util.py

If you have a different database connection class. Make sure it has the following methods:
- connect() 
- execute_query(query)
- close()
'''

class MatchSimulator:
    def __init__(self, match_id, frames_per_second=15):
        self.match_id = match_id
        self.frames_per_second = frames_per_second  # Target FPS for animation
        self.db = DatabaseConnection()
        self.tracking_data = None
        self.events_data = None
        self.teams_data = None
        self.current_frame = 0
        self.max_frame = 0
        self.fig = None
        self.ax = None
        self.scatter_objects = {}
        self.text_objects = {}
        self.team_colors = {}
        self.period = 1
        self.timestamp = ""
        self.match_info = {}
        self.time_text = None
        self.event_text = None
        self.ball_trajectory = []
        self.trajectory_line = None
        self.max_trajectory_points = 30
        self.all_frames = []
        print(f"Initialized match simulator with target {frames_per_second} FPS")

    def load_data(self):
        print(f"Loading data for match {self.match_id}...")

        query = f"""
        SELECT m.*, ht.team_name as home_team_name, at.team_name as away_team_name 
        FROM matches m 
        JOIN teams ht ON m.home_team_id = ht.team_id
        JOIN teams at ON m.away_team_id = at.team_id
        WHERE m.match_id = '{self.match_id}'
        """

        match_df = self.db.execute_query(query)
        if match_df is not None and not match_df.empty:
            self.match_info = match_df.iloc[0].to_dict()
            print(f"Match: {self.match_info['home_team_name']} vs {self.match_info['away_team_name']}")
        else:
            print(f"No match found with ID: {self.match_id}")
            return False


        query = f"""
        SELECT pt.*, p.player_name, p.jersey_number, t.team_name, t.team_id
        FROM player_tracking pt
        LEFT JOIN players p ON pt.player_id = p.player_id
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE pt.game_id = '{self.match_id}'
        ORDER BY pt.frame_id, pt.player_id
        """
        self.tracking_data = self.db.execute_query(query)

        ball_query = f"""
        SELECT 
            frame_id, 
            timestamp, 
            period_id, 
            'Ball' as player_name, 
            x, 
            y,
            'Ball' as team_name,
            'Ball' as team_id,
            0 as jersey_number,
            'ball' as player_id
        FROM player_tracking 
        WHERE game_id = '{self.match_id}' AND player_id = 'ball'
        ORDER BY frame_id
        """
        ball_data = self.db.execute_query(ball_query)

        if ball_data is not None and not ball_data.empty:
            self.tracking_data = pd.concat([self.tracking_data, ball_data], ignore_index=True)

        if self.tracking_data is not None and not self.tracking_data.empty:
            frame_ids = self.tracking_data['frame_id'].unique()
            self.max_frame = max(frame_ids)
            print(f"Loaded {len(frame_ids)} frames of tracking data")
        else:
            print("No tracking data found")
            return False

        query = f"""
        SELECT me.*, et.name as event_name, t.team_name, p.player_name
        FROM matchevents me
        JOIN eventtypes et ON me.eventtype_id = et.eventtype_id
        LEFT JOIN teams t ON me.team_id = t.team_id
        LEFT JOIN players p ON me.player_id = p.player_id
        WHERE me.match_id = '{self.match_id}'
        ORDER BY me.timestamp
        """
        self.events_data = self.db.execute_query(query)

        if self.events_data is not None and not self.events_data.empty:
            print(f"Loaded {len(self.events_data)} match events")
        else:
            print("No events data found")

        home_team_id = self.match_info['home_team_id']
        away_team_id = self.match_info['away_team_id']
        self.team_colors = {
            home_team_id: 'blue',
            away_team_id: 'orange',
            'Ball': 'yellow'
        }

        return True

    def get_frame_data(self, frame_id):
        return self.tracking_data[self.tracking_data['frame_id'] == frame_id]

    def get_events_at_timestamp(self, timestamp):
        if self.events_data is None:
            return pd.DataFrame()
        return self.events_data[self.events_data['timestamp'] == timestamp]

    def initialize_pitch(self):
        pitch = Pitch(pitch_color='grass', line_color='white', pitch_type='opta',
                      pitch_length=105, pitch_width=68)
        self.fig, self.ax = pitch.draw(figsize=(14, 10))

        home_team = self.match_info.get('home_team_name', 'Home Team')
        away_team = self.match_info.get('away_team_name', 'Away Team')
        match_title = f"{home_team} vs {away_team}"
        self.fig.suptitle(match_title, fontsize=16)

        self.time_text = self.ax.text(0, -5, "", fontsize=12, ha='center')
        self.event_text = self.ax.text(0, 73, "", fontsize=12, ha='center')

        home_team_id = self.match_info['home_team_id']
        away_team_id = self.match_info['away_team_id']

        self.scatter_objects[home_team_id] = self.ax.scatter([], [], s=100,
                                                             color=self.team_colors[home_team_id],
                                                             label=home_team)
        self.scatter_objects[away_team_id] = self.ax.scatter([], [], s=100,
                                                             color=self.team_colors[away_team_id],
                                                             label=away_team)
        self.scatter_objects['Ball'] = self.ax.scatter([], [], s=150,
                                                       color=self.team_colors['Ball'],
                                                       label='Ball')

        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=3)

        self.ball_trajectory = []
        if self.trajectory_line and self.trajectory_line in self.ax.lines:
            self.trajectory_line.remove()
        self.trajectory_line = None

        self.text_objects = {
            home_team_id: [],
            away_team_id: [],
            'Ball': []
        }

        return self.fig

    def update_ball_trajectory(self, ball_x, ball_y):
        try:
            self.ball_trajectory.append((ball_x, ball_y))

            if len(self.ball_trajectory) > self.max_trajectory_points:
                self.ball_trajectory = self.ball_trajectory[-self.max_trajectory_points:]

            if len(self.ball_trajectory) > 1:
                trajectory_x, trajectory_y = zip(*self.ball_trajectory)

                if self.trajectory_line and self.trajectory_line in self.ax.lines:
                    self.trajectory_line.set_data(trajectory_x, trajectory_y)
                else:
                    self.trajectory_line = self.ax.plot(
                        trajectory_x, trajectory_y,
                        color='gold',
                        linewidth=3,
                        alpha=0.8,
                        zorder=1
                    )[0]
        except Exception as e:
            pass

    def interpolate_positions(self, start_frame_id, end_frame_id, num_interpolated_frames):
        interpolated_frames = []

        start_frame_data = self.get_frame_data(start_frame_id)
        end_frame_data = self.get_frame_data(end_frame_id)

        if start_frame_data.empty or end_frame_data.empty:
            print(f"Warning: Missing data for frames {start_frame_id} or {end_frame_id}")
            return []

        timestamp_start = start_frame_data['timestamp'].iloc[0]
        period_id = start_frame_data['period_id'].iloc[0]

        start_players = {}
        for _, row in start_frame_data.iterrows():
            player_id = row['player_id']
            start_players[player_id] = row

        end_players = {}
        for _, row in end_frame_data.iterrows():
            player_id = row['player_id']
            end_players[player_id] = row

        common_players = set(start_players.keys()).intersection(set(end_players.keys()))

        for i in range(1, num_interpolated_frames + 1):
            t = i / (num_interpolated_frames + 1)

            frame_data = []

            for player_id in common_players:
                try:
                    start_player = start_players[player_id]
                    end_player = end_players[player_id]

                    x = float(start_player['x']) * (1.0 - t) + float(end_player['x']) * t
                    y = float(start_player['y']) * (1.0 - t) + float(end_player['y']) * t

                    is_ball = (player_id == 'ball' or
                               start_player.get('player_name', '') == 'Ball' or
                               start_player.get('team_id', '') == 'Ball')

                    team_id = 'Ball' if is_ball else start_player['team_id']
                    team_name = 'Ball' if is_ball else start_player['team_name']

                    player_row = {
                        'player_id': player_id,
                        'x': x,
                        'y': y,
                        'player_name': start_player['player_name'],
                        'jersey_number': start_player['jersey_number'],
                        'team_id': team_id,
                        'team_name': team_name
                    }

                    frame_data.append(player_row)
                except Exception as e:
                    print(f"Error interpolating player {player_id}: {e}")
                    continue

            interp_frame_id = start_frame_id + (end_frame_id - start_frame_id) * t
            interp_timestamp = timestamp_start

            interpolated_frame = {
                'frame_id': interp_frame_id,
                'is_real': False,
                'data': frame_data,  # List of player dictionaries
                'timestamp': interp_timestamp,
                'period_id': period_id
            }

            interpolated_frames.append(interpolated_frame)

        return interpolated_frames

    def prepare_all_frames(self, start_frame_id=None, end_frame_id=None, max_frames=500):
        real_frame_ids = sorted(self.tracking_data['frame_id'].unique())

        if start_frame_id is not None:
            real_frame_ids = [f for f in real_frame_ids if f >= start_frame_id]
        if end_frame_id is not None:
            real_frame_ids = [f for f in real_frame_ids if f <= end_frame_id]

        # Limit number of frames if needed
        if len(real_frame_ids) > max_frames:
            print(f"Limiting to {max_frames} real frames for performance")
            real_frame_ids = real_frame_ids[:max_frames]

        if len(real_frame_ids) < 2:
            print("Not enough frames to animate")
            return 0

        print(f"Processing {len(real_frame_ids)} real frames")

        self.all_frames = []

        first_frame_data = self.get_frame_data(real_frame_ids[0])
        if not first_frame_data.empty:
            first_frame = {
                'frame_id': real_frame_ids[0],
                'is_real': True,
                'data': first_frame_data,
                'timestamp': first_frame_data['timestamp'].iloc[0],
                'period_id': first_frame_data['period_id'].iloc[0]
            }
            self.all_frames.append(first_frame)

        total_interpolated = 0
        for i in range(len(real_frame_ids) - 1):
            current_frame_id = real_frame_ids[i]
            next_frame_id = real_frame_ids[i + 1]

            frames_to_interpolate = self.frames_per_second - 1  # -1 because we already have the real frame

            interpolated_frames = self.interpolate_positions(
                current_frame_id, next_frame_id, frames_to_interpolate
            )

            if interpolated_frames:
                self.all_frames.extend(interpolated_frames)
                total_interpolated += len(interpolated_frames)

            if i < len(real_frame_ids) - 2:
                next_frame_data = self.get_frame_data(next_frame_id)
                if not next_frame_data.empty:
                    next_frame = {
                        'frame_id': next_frame_id,
                        'is_real': True,
                        'data': next_frame_data,
                        'timestamp': next_frame_data['timestamp'].iloc[0],
                        'period_id': next_frame_data['period_id'].iloc[0]
                    }
                    self.all_frames.append(next_frame)

        last_frame_data = self.get_frame_data(real_frame_ids[-1])
        if not last_frame_data.empty:
            last_frame = {
                'frame_id': real_frame_ids[-1],
                'is_real': True,
                'data': last_frame_data,
                'timestamp': last_frame_data['timestamp'].iloc[0],
                'period_id': last_frame_data['period_id'].iloc[0]
            }
            self.all_frames.append(last_frame)

        self.all_frames.sort(key=lambda f: f['frame_id'])

        total_frames = len(self.all_frames)
        print(f"Created {total_frames} total frames: "
              f"{len(real_frame_ids)} real + {total_interpolated} interpolated")

        return total_frames

    def update_animation(self, frame_idx):
        try:
            if frame_idx >= len(self.all_frames):
                existing_artists = list(self.scatter_objects.values())
                if self.time_text:
                    existing_artists.append(self.time_text)
                if self.event_text:
                    existing_artists.append(self.event_text)
                if self.trajectory_line:
                    existing_artists.append(self.trajectory_line)
                for team_texts in self.text_objects.values():
                    existing_artists.extend(team_texts)
                return existing_artists

            frame = self.all_frames[frame_idx]

            self.timestamp = frame['timestamp']
            self.period = frame['period_id']
            self.time_text.set_text(f"Period: {self.period} | Time: {self.timestamp}")

            if frame['is_real']:
                events = self.get_events_at_timestamp(self.timestamp)
                if not events.empty:
                    event_str = f"EVENT: {events.iloc[0]['event_name']} by {events.iloc[0]['player_name']} ({events.iloc[0]['team_name']})"
                    self.event_text.set_text(event_str)
                else:
                    self.event_text.set_text("")

            for team_id in self.text_objects:
                for text_obj in self.text_objects.get(team_id, []):
                    if text_obj in self.ax.texts:
                        text_obj.remove()
            self.text_objects = {team_id: [] for team_id in self.team_colors.keys()}

            home_team_id = self.match_info['home_team_id']
            away_team_id = self.match_info['away_team_id']
            all_team_ids = [home_team_id, away_team_id, 'Ball']

            if frame['is_real']:
                frame_data = frame['data']

                team_data = {}
                for team_id in all_team_ids:
                    if team_id == 'Ball':
                        ball_data = frame_data[(frame_data['team_id'] == 'Ball') |
                                               (frame_data['player_id'] == 'ball') |
                                               (frame_data['player_name'] == 'Ball')]
                        team_data[team_id] = ball_data

                        if not ball_data.empty and len(ball_data) > 0:
                            ball_x = ball_data['x'].values[0]
                            ball_y = ball_data['y'].values[0]
                            self.update_ball_trajectory(ball_x, ball_y)
                    else:
                        team_data[team_id] = frame_data[frame_data['team_id'] == team_id]
            else:
                players_data = frame['data']

                team_data = {team_id: [] for team_id in all_team_ids}
                for player in players_data:
                    team_id = player['team_id']
                    if team_id not in team_data:
                        continue

                    team_data[team_id].append(player)

                    if team_id == 'Ball' or player['player_id'] == 'ball':
                        self.update_ball_trajectory(player['x'], player['y'])

                for team_id in team_data:
                    if team_data[team_id]:
                        team_data[team_id] = pd.DataFrame(team_data[team_id])
                    else:
                        team_data[team_id] = pd.DataFrame()

            for team_id in all_team_ids:
                team_df = team_data.get(team_id, pd.DataFrame())

                if not team_df.empty:
                    x = team_df['x'].values
                    y = team_df['y'].values

                    if team_id in self.scatter_objects:
                        self.scatter_objects[team_id].set_offsets(np.column_stack([x, y]))

                    max_labels = 11 if team_id != 'Ball' else 1
                    for idx, player_row in enumerate(team_df.iterrows()):
                        if idx >= max_labels:
                            break

                        _, player = player_row

                        if team_id != 'Ball':
                            jersey_num = player['jersey_number'] if pd.notna(player['jersey_number']) else "?"
                            text = self.ax.text(player['x'] + 1, player['y'] + 1,
                                                f"{jersey_num}", fontsize=9)
                            self.text_objects[team_id].append(text)
                        else:
                            text = self.ax.text(player['x'] + 1, player['y'] + 1, "⚽", fontsize=10)
                            self.text_objects[team_id].append(text)
                else:
                    if team_id in self.scatter_objects:
                        self.scatter_objects[team_id].set_offsets(np.zeros((0, 2)))

            artists = list(self.scatter_objects.values()) + [self.time_text, self.event_text]
            if self.trajectory_line:
                artists.append(self.trajectory_line)
            artists.extend(sum(list(self.text_objects.values()), []))

            return artists

        except Exception as e:
            print(f"Error updating animation frame {frame_idx}: {e}")
            return []

    def animate_match(self, start_frame=None, end_frame=None, max_frames=300):
        if self.tracking_data is None:
            print("No tracking data loaded. Run load_data() first.")
            return

        total_frames = self.prepare_all_frames(start_frame, end_frame, max_frames)

        if total_frames < 2:
            print("Not enough frames to animate.")
            return

        self.initialize_pitch()

        frame_interval = 1000.0 / self.frames_per_second
        print(f"Animating at {self.frames_per_second} FPS ({frame_interval:.1f}ms per frame)")

        animation = FuncAnimation(
            self.fig,
            self.update_animation,
            frames=range(total_frames),
            interval=frame_interval,
            blit=True,
            repeat=False,
            cache_frame_data=False
        )

        # Show animation
        plt.tight_layout()
        plt.show(block=True)

        return animation

    def close(self):
        self.db.close()


if __name__ == "__main__":
    simulator = MatchSimulator("6fal3n71n68p9j1pypcdabggk", frames_per_second=30)

    if simulator.load_data():
        try:
            frame_ids = sorted(simulator.tracking_data['frame_id'].unique())
            if len(frame_ids) > 0:
                start_frame = frame_ids[0]

                end_frame = frame_ids[min(300, len(frame_ids) - 1)]
                print(f"Using frame range: {start_frame} to {end_frame}")

                simulator.animate_match(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    max_frames=300
                )
            else:
                print("No frames available to animate")
        finally:
            simulator.close()
