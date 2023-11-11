
import random

class CombatManager:
    active_damage_boosts = {}
    active_ability_negations = {}
    mega_evolutions = {}
    active_plates = {}
    active_evolutions = {}
    mega_evolution_data = {'Player 1': {'active': False, 'turns_left': 0},
                           'Player 2': {'active': False, 'turns_left': 0}}

    @staticmethod
    def calculate_probabilities(base_wheel):
        total_size = sum(segment['Size'] for segment in base_wheel)
        probabilities = {}
        for segment in base_wheel:
            probabilities[segment['Name']] = segment['Size'] / total_size
        return probabilities

    @staticmethod
    def spin_wheel(pokemon):
        wheel = []
        for move in pokemon['Base Wheel Size']:
            wheel.extend([move['Name']] * move['Size'])
        return random.choice(wheel)

    @staticmethod
    def determine_outcome(move1, move2):
        type1, type2 = move1['Move Type'], move2['Move Type']

        # handle Blue moves
        if type1 == 'Blue':
            return 'Player 1 Wins', 'Blue move used'
        if type2 == 'Blue':
            return 'Player 2 Wins', 'Blue move used'

        # handle Red moves
        if type1 == 'Red':
            return 'Player 2 Wins', 'Player 1 missed'
        if type2 == 'Red':
            return 'Player 1 Wins', 'Player 2 missed'

        # handle Gold vs Purple moves
        if type1 == 'Gold' and type2 == 'Purple':
            return 'Player 1 Wins', move1['Name']
        if type2 == 'Gold' and type1 == 'Purple':
            return 'Player 2 Wins', move2['Name']

        # handle Purple vs Purple moves
        if type1 == 'Purple' and type2 == 'Purple':
            stars1 = move1.get('Stars', 0)
            stars2 = move2.get('Stars', 0)
            if stars1 > stars2:
                return 'Player 1 Wins', move1['Name']
            elif stars2 > stars1:
                return 'Player 2 Wins', move2['Name']
            else:
                return 'Draw', 'Same number of stars'

        # handle White vs White moves
        if type1 == 'White' and type2 == 'White':
            damage1 = move1.get('Damage', 0)
            damage2 = move2.get('Damage', 0)
            if damage1 > damage2:
                return 'Player 1 Wins', move1['Name']
            elif damage2 > damage1:
                return 'Player 2 Wins', move2['Name']
            else:
                return 'Draw', 'Same damage value'

        # handle White vs Gold moves
        if (type1 == 'White' and type2 == 'Gold') or (type1 == 'Gold' and type2 == 'White'):
            damage1 = move1.get('Damage', 0)
            damage2 = move2.get('Damage', 0)
            if damage1 > damage2:
                return 'Player 1 Wins', move1['Name']
            elif damage2 > damage1:
                return 'Player 2 Wins', move2['Name']
            else:
                return 'Draw', 'Same damage value'

        return 'No applicable rule'

    def apply_effects(self, outcome, move1, move2):
        if outcome == "Player 1 Wins" and move1.get('Additional Notes'):
            return f"Player 1's Pokemon applies {move1['Additional Notes']}"
        elif outcome == "Player 2 Wins" and move2.get('Additional Notes'):
            return f"Player 2's Pokemon applies {move2['Additional Notes']}"
        else:
            return "No additional effects applied"

    @staticmethod
    def use_support_cards(player, plate):
        plate_id = plate["ID"]
        plate_effect = plate["Effect"]
        plate_name = plate["Name"]

        if plate_id in CombatManager.active_plates:
            return f"{plate_name} is already active."

        CombatManager.active_plates[plate_id] = {
            'player': player,
            'effect': plate_effect
        }

        if "deals +20 damage" in plate_effect:
            CombatManager.apply_damage_boost(player, plate)
        elif "Abilities of opposing Pokémon" in plate_effect:
            CombatManager.apply_ability_negation(player, plate)
        # TODO: more conditions

        return f"{player}'s plate {plate_name} is activated."

    @staticmethod
    def apply_damage_boost(player, plate):
        pokemon_type = plate["Effect"].split("of your ")[1].split("-type")[0]

        if player not in CombatManager.active_damage_boosts:
            CombatManager.active_damage_boosts[player] = {}


        CombatManager.active_damage_boosts[player][pokemon_type] = 20  # Assuming a flat +20 boost

        return f"{player}'s {pokemon_type}-type Pokemon now deals +20 damage."

    @staticmethod
    def apply_ability_negation(player, plate):
        pokemon_type = plate["Effect"].split("of your ")[1].split("-type")[0]
        if player not in CombatManager.active_ability_negations:
            CombatManager.active_ability_negations[player] = {}
        CombatManager.active_ability_negations[player][pokemon_type] = True

        return f"The abilities of {player}'s opponent's {pokemon_type}-type Pokemon with MP-reducing markers are now nullified."

    @staticmethod
    def check_plate_effects(player, opponent, move):
        player_boosts = CombatManager.active_damage_boosts.get(player, {})
        opponent_negations = CombatManager.active_ability_negations.get(opponent, {})
        if move.get('Type') in player_boosts:
            move['Damage'] += player_boosts[move.get('Type')]
        if move.get('Type') in opponent_negations:
            move['Ability'] = None

        return move

    @staticmethod
    def apply_status_effects(pokemon, move):
        status = pokemon.get('Status Condition', None)

        if status == 'Confusion':
            move = CombatManager.get_next_wheel_move(move, pokemon)

        elif status == 'Poison':
            move['Damage'] -= 20

        elif status == 'Noxious':
            move['Damage'] -= 40

        elif status == 'Paralysis':
            move = CombatManager.convert_smallest_move_to_miss(move, pokemon)

        elif status == 'Sleep' or status == 'Frozen':
            return {'Move Type': 'Miss', 'Name': 'N/A'}

        elif status == 'Burn':
            move = CombatManager.convert_smallest_move_to_miss(move, pokemon)
            move['Damage'] -= 10

        elif status == 'Wait':
            return None  # No move can be performed

        elif status == 'Curse':
            return move

    @staticmethod
    def get_next_wheel_move(move, pokemon):
        # Find the index of the current move
        current_index = pokemon['Moves'].index(move)
        # Move to the next index to simulate the confusion effect
        next_index = (current_index + 1) % len(pokemon['Moves'])
        # Return the 'next' move
        return pokemon['Moves'][next_index]

    @staticmethod
    def convert_smallest_move_to_miss(move, pokemon):
        # Find the smallest move segment for Paralysis and Burn
        if not pokemon['Moves']:
            return move  # No move to convert if list is empty
        smallest_move = min(pokemon['Moves'], key=lambda m: m.get('Size', float('inf')))

        if smallest_move['Size'] == move['Size']:
            # If the move to be converted is the one that was spun
            smallest_move['Name'] = 'Miss'
            smallest_move['Move Type'] = 'Red'
            smallest_move['Damage'] = 0
            smallest_move['Stars'] = 0

        return move if move['Name'] != smallest_move['Name'] else smallest_move

    @staticmethod
    def combat_calculation(pokemon1, pokemon2, plate1=None, plate2=None):

        pokemon1 = CombatManager.active_evolutions.get('Player 1', pokemon1)
        pokemon2 = CombatManager.active_evolutions.get('Player 2', pokemon2)

        move1 = CombatManager.spin_wheel(pokemon1)
        move2 = CombatManager.spin_wheel(pokemon2)

        if plate1:
            move1 = CombatManager.check_plate_effects('Player 1', 'Player 2', move1)
        if plate2:
            move2 = CombatManager.check_plate_effects('Player 2', 'Player 1', move2)

        outcome, reason = CombatManager.determine_outcome(move1, move2)

        additional_effects = CombatManager.apply_effects(outcome, move1, move2)

        if outcome == 'Player 1 Wins':
            CombatManager.evolve_pokemon('Player 1', pokemon1)
        elif outcome == 'Player 2 Wins':
            CombatManager.evolve_pokemon('Player 2', pokemon2)

        return outcome, reason, additional_effects

    @staticmethod
    def mega_evolve(player, pokemon):
        if CombatManager.mega_evolution_data[player]['active']:
            return f"{player} has already used Mega Evolution."
        CombatManager.mega_evolution_data[player]['active'] = True
        CombatManager.mega_evolution_data[player]['turns_left'] = 7

        return f"{player}'s {pokemon['Name']} has Mega Evolved!"

    @staticmethod
    def evolve_pokemon(player, pokemon):

        if not pokemon.get('Evolution'):
            return f"{pokemon['Name']} cannot evolve."

        for move in pokemon['Evolution']['Base Wheel Size']:
            move['Damage'] = move.get('Damage', 0) + 10
            move['Stars'] = move.get('Stars', 0) + 1

        pokemon = pokemon['Evolution']

        CombatManager.active_evolutions[player] = pokemon

        return f"{player}'s {pokemon['Name']} has evolved!"

    @staticmethod
    def multiple_spin_wheel(pokemon, num_spins=1):
        outcomes = []
        outcome_counts = {}
        for _ in range(num_spins):
            outcome = CombatManager.spin_wheel(pokemon)
            outcomes.append(outcome)
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        most_common = max(outcome_counts, key=outcome_counts.get)
        return most_common

    @staticmethod
    def apply_curse_effect(defeated_pokemon, player_board):
        if defeated_pokemon.get('Status Condition') == 'Curse':
            # Attempt to remove the Pokémon from the board
            try:
                player_board.remove(defeated_pokemon)  # This assumes player_board is a list
                return f"{defeated_pokemon['Name']} was cursed and is removed from play."
            except ValueError:
                return f"Error: {defeated_pokemon['Name']} could not be found on the player's board."
        # Return an empty string if no curse effect was applied
        return ""

    @staticmethod
    def use_support_cards(player, plate, all_pokemon):
        plate_id = plate["ID"]
        plate_effect = plate.get("Effect")
        plate_name = plate["Name"]

        # Check if the plate is already active
        if plate_id in CombatManager.active_plates:
            return f"{plate_name} is already active."

        # Activate the plate
        CombatManager.active_plates[plate_id] = {'player': player, 'effect': plate_effect}

        # Handle new plate effects
        if "heals all status conditions" in plate_effect:
            # Heal all status conditions for the player's Pokémon
            for pokemon in all_pokemon:
                pokemon.pop('Status Condition', None)
            return f"{plate_name} used by {player} healed all status conditions."

        elif "increase movement" in plate_effect:
            # Increase movement points for the player's Pokémon
            boost_amount = int(plate_effect.split('+')[1].split(' ')[0])  # Assuming format "increase movement +1"
            for pokemon in all_pokemon:
                pokemon['Movement'] += boost_amount
            return f"{plate_name} used by {player} increased the movement of Pokémon by {boost_amount}."

        # Add more special effects as needed

        return f"{player}'s plate {plate_name} is activated."

