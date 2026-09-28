
import json
import sys
import os

# Add the path to fpl_data and fpl_utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'skills/fpl/scripts'))

from fpl_data import FPLData
from fpl_utils import FPLUtils

fpl_utils = FPLUtils()
fpl_data_api = FPLData(fpl_utils)

# Load data (this will fetch from the API if not already cached)
fpl_data_api._load_data()

# Your team's player IDs (this list should be dynamically updated or passed as an argument in a more advanced tool)
# For now, keeping it static as per previous successful run.
player_ids = [220, 447, 473, 5, 237, 82, 47, 390, 450, 430, 661, 470, 691, 694, 508]

injured_players = []
doubtful_players = []

# Get all players data to map IDs to full details
all_players = fpl_data_api.get_players()
player_map = {player['id']: player for player in all_players}

for player_id in player_ids:
    player = player_map.get(player_id)
    if player:
        if player.get('status') == 'i':
            injured_players.append(player)
        elif player.get('status') == 'd':
            doubtful_players.append(player)

message_parts = []
if injured_players:
    message_parts.append('**Injured Players:**\n')
    for p in injured_players:
        message_parts.append(f'- {p["full_name"]} ({p["team_name"]})\n')

if doubtful_players:
    message_parts.append('\n**Doubtful Players:**\n')
    for p in doubtful_players:
        message_parts.append(f'- {p["full_name"]} ({p["team_name"]})\n')

if not injured_players and not doubtful_players:
    message_parts.append('Great news! None of your players are currently reported as injured or doubtful.')

final_message = ''.join(message_parts)
print(json.dumps({'status': 'success', 'message': final_message}))
