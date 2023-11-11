from pokeduel.logic.combat import CombatManager
import json
import random

class CombatManagerPokemon(CombatManager):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.pokemon_data = next((data for data in pokemons_data if data["Name"] == name), None)
        if self.pokemon_data:
            self.base_wheel_size = self.pokemon_data["Base Wheel Size"]
            self.type_ = self.pokemon_data["Type"]
        else:
            self.base_wheel_size = []
            self.type_ = []

    # Method to be implemented by subclasses for special move effects
    def apply_special_effects(self, move, opponent_move, outcome):
        raise NotImplementedError

    # Combat calculation considering special effects based on the Pokémon's move
    def combat_calculation(self, pokemon1, pokemon2, plate1=None, plate2=None):
        outcome, reason, additional_effects = super().combat_calculation(pokemon1, pokemon2, plate1, plate2)
        pokemon1_move = pokemon1.get('Move')
        pokemon2_move = pokemon2.get('Move')

        if pokemon1.get('Name') == self.name:
            special_effects = self.apply_special_effects(pokemon1_move, pokemon2_move, outcome)
        elif pokemon2.get('Name') == self.name:
            special_effects = self.apply_special_effects(pokemon2_move, pokemon1_move, outcome)
        else:
            special_effects = ""

        return outcome, reason, additional_effects + special_effects


class Pikachu(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Pikachu")
        with open('./pokemon.json') as file:
            pokemons_data = json.load(file)
        self.pikachu_data = next(p for p in pokemons_data if p['Name'] == 'Pikachu')

    def spin_wheel(self):
        # If a Z-Move is available, it overrides the normal spin
        z_move_available = any(move for move in self.base_wheel_size if move["Move Type"] == "White Z-Move")
        if z_move_available:
            return next(move for move in self.base_wheel_size if move["Move Type"] == "White Z-Move")
        else:
            # Normal spin_wheel logic using random
            total_size = sum(move['Size'] for move in self.base_wheel_size)
            spin = random.randint(1, total_size)
            current_spin = 0
            for move in self.base_wheel_size:
                current_spin += move["Size"]
                if spin <= current_spin:
                    return move

    def apply_special_effects(self, pikachu_move, opponent_move, outcome):
        move_details = next(
            (move for move in self.pikachu_data['Base Wheel Size'] if move['Name'] == pikachu_move.get('Name')),
            None)

        if move_details and move_details.get('Move Type') == 'White Z-Move' and outcome == 'Player 1 Wins':
            return "Gigavolt Havoc effect is applied to the opponent, causing paralysis."
        return ""

    def combat_calculation(self, pokemon1, pokemon2, plate1=None, plate2=None):
        """Override combat calculation to include Pikachu's special rules.
        """
        # Call the parent class combat calculation
        outcome, reason, additional_effects = super().combat_calculation(pokemon1, pokemon2, plate1, plate2)

        # Check if Pikachu is involved and apply special rules
        if pokemon1.get('Name') == 'Pikachu':
            special_outcome = self.apply_special_effects(pokemon1, pokemon2, outcome)
            additional_effects += f" {special_outcome}"
        elif pokemon2.get('Name') == 'Pikachu':
            special_outcome = self.apply_special_effects(pokemon2, pokemon1, outcome)
            additional_effects += f" {special_outcome}"

        return outcome, reason, additional_effects


class Charmander(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Charmander")
        with open('./pokemon.json') as file:
            pokemons_data = json.load(file)
        self.charmander_data = next(p for p in pokemons_data if p['Name'] == 'Charmander')

    def apply_special_effects(self, charmander_move, opponent_move, outcome):
        if charmander_move.get('Name') == 'Smokescreen' and outcome == 'Player 1 Wins':
            return "Smokescreen effect is applied to the opponent."
        return ""


    def combat_calculation(self, pokemon1, pokemon2, plate1=None, plate2=None):
        """Override combat calculation to include Charmander's special rules.
        """
        # Call the parent class combat calculation
        outcome, reason, additional_effects = super().combat_calculation(pokemon1, pokemon2, plate1, plate2)

        # Check if Charmander is involved and apply special rules
        if pokemon1.get('Name') == 'Charmander':
            special_outcome = self.apply_special_effects(pokemon1, pokemon2, outcome)
            additional_effects += f" {special_outcome}"
        elif pokemon2.get('Name') == 'Charmander':
            special_outcome = self.apply_special_effects(pokemon2, pokemon1, outcome)
            additional_effects += f" {special_outcome}"

        return outcome, reason, additional_effects


class CombatManagerSquirtle(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Squirtle")

    # Placeholder for Squirtle's special effects
    def apply_special_effects(self, squirtle_move, opponent_move, outcome):
        return ""


# Specific Combat Manager for Bulbasaur
class CombatManagerBulbasaur(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Bulbasaur")

    def apply_special_effects(self, bulbasaur_move, opponent_move, outcome):
        return ""


# Specific Combat Manager for Charizard
class CombatManagerCharizard(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Charizard")

    def apply_special_effects(self, charizard_move, opponent_move, outcome):
        # Placeholder for Charizard's special effects logic
        # Implement Charizard's special effects when details are provided
        return ""


# Specific Combat Manager for Blastoise
class CombatManagerBlastoise(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Blastoise")

    def apply_special_effects(self, blastoise_move, opponent_move, outcome):
        # Placeholder for Blastoise's special effects logic
        # Implement Blastoise's special effects when details are provided
        return ""


# Specific Combat Manager for Venusaur
class CombatManagerVenusaur(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Venusaur")

    def apply_special_effects(self, venusaur_move, opponent_move, outcome):
        # Placeholder for Venusaur's special effects logic
        # Implement Venusaur's special effects when details are provided
        return ""
# For Machop
class CombatManagerMachop(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Machop")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Machop's special effects logic
        # Implement the special effects of "Focus Punch" and "All-Out Pummelling" Z-Move when details are provided
        return ""

# For Raticate
class CombatManagerRaticate(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Raticate")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Raticate's special effects logic
        # Implement the special effects of "Hyper Fang" and "Breakneck Blitz" Z-Move when details are provided
        return ""

# For Marill
class CombatManagerMarill(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Marill")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Marill's special effects logic
        # Implement the 'Huge Power' ability and special effects of moves like "Hydro Vortex" when details are provided
        return ""

# For Steelix
class CombatManagerSteelix(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Steelix")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Steelix's special effects logic
        # Implement the special effects of "Screech", "Explosion", "Tectonic Rage", and "Corkscrew Crash" when details are provided
        return ""

# For Bidoof
class CombatManagerBidoof(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Bidoof")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Bidoof's special effects logic
        # Implement the special effects of "Cut", "Rock Smash", and "Breakneck Blitz" Z-Move when details are provided
        return ""

# For Mudkip
class CombatManagerMudkip(CombatManagerPokemon):
    def __init__(self):
        super().__init__("Mudkip")

    def apply_special_effects(self, move, opponent_move, outcome):
        # Placeholder for Mudkip's special effects logic
        # Implement the special effects of "Hydro Vortex" Z-Move and other moves like "Water Gun" when details are provided
        return ""
