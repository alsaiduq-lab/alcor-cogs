import json

class PlateManager:
    def __init__(self, plates_file):
        self.plates = self.load_plates(plates_file)

    def load_plates(self, plates_file):
        try:
            with open(plates_file, 'r') as file:
                return json.load(file)['plates']
        except FileNotFoundError:
            raise Exception(f"The file {plates_file} does not exist.")
        except json.JSONDecodeError:
            raise Exception(f"The file {plates_file} is not valid JSON.")

    def use_plate(self, plate_id, game_data):
        plate = next((p for p in self.plates if p['ID'] == plate_id), None)
        if not plate:
            raise ValueError(f"Plate with ID {plate_id} not found.")
        effect_method = self.get_plate_effect_method(plate['Name'])
        if effect_method:
            return effect_method(plate, game_data)
        else:
            raise NotImplementedError(f"No method for applying the plate {plate['Name']}.")

    def get_plate_effect_method(self, plate_name):
        return getattr(self, plate_name.lower().replace(' ', '_').replace('.', ''), None)

    # Plate effect methods
    def long_throw(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_from_bench(game_data)
        self.place_pokemon_near_entry_point(chosen_pokemon, game_data)
        game_data['turn_ends'] = True
        return "Long Throw plate used."

    def bright_powder(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['can_respin'] = True
        return "Bright Powder plate used."
    def recycle(self, plate, game_data):
        # Make all used plates available again except for Recycle itself
        for p in game_data['used_plates']:
            if p != plate['ID']:
                game_data['available_plates'].append(p)
        game_data['used_plates'].remove(plate['ID'])
        game_data['turn_ends'] = True
        return f"Recycle plate used. All plates are now available."

    def x_sp_atk(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['stars'] += 2
        return f"X Sp. Atk plate used. {chosen_pokemon['name']} gains +2 stars for this turn."

    def max_revive(self, plate, game_data):
        # Move a Pokemon from P.C. to bench
        pc_pokemon = self.choose_pokemon_from_pc(game_data)
        game_data['bench'].append(pc_pokemon)
        game_data['pc'].remove(pc_pokemon)
        return f"Max Revive plate used. {pc_pokemon['name']} moved to bench."

    def desperate_times(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['desperate_buff'] = 50
        return f"Desperate Times plate used. {chosen_pokemon['name']} may deal extra damage."

    def dna_splicers(self, plate, game_data):
        # Change form of Kyurem and remove Zekrom or Reshiram from the duel
        kyurem = game_data['pokemon'].get('kyurem')
        zekrom_reshiram = game_data['pokemon'].get('zekrom') or game_data['pokemon'].get('reshiram')
        if kyurem and zekrom_reshiram:
            self.change_form_to_black_or_white_kyurem(kyurem)
            self.exclude_pokemon_from_duel(zekrom_reshiram, game_data)
            return "Kyurem's form has changed and Zekrom or Reshiram has been excluded from the duel."
        else:
            return "Conditions for DNA Splicers not met."

    def miracle_seed(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_on_field_of_type(game_data, 'Grass')
        chosen_pokemon['Damage'] += 20
        return f"Miracle Seed plate used. {chosen_pokemon['Name']} got a 20 damage boost."

    def never_melt_ice(self, plate, game_data):
        chosen_pokemon = self.choose_pokemon_on_field_of_type(game_data, 'Ice')
        chosen_pokemon['Damage'] += 20
        return f"Never-Melt Ice plate used. {chosen_pokemon['Name']} got a 20 damage boost."

    def microwave_oven(self, plate, game_data):
        rotom = self.choose_specific_pokemon_on_field(game_data, ['Rotom', 'Wash Rotom',
                                                                  'Frost Rotom', 'Fan Rotom', 'Mow Rotom'])
        rotom['Form'] = 'Heat Rotom'
        self.clear_burned_condition(game_data)
        game_data['weather'] = 'Sunny'
        return f"Microwave Oven used: {rotom['Name']} changed to Heat Rotom, burned status cleared, and sunny weather set for 9 turns."

    def washing_machine(self, plate, game_data):
        rotom = self.choose_specific_pokemon_on_field(game_data, ['Rotom', 'Heat Rotom',
                                                                  'Frost Rotom', 'Fan Rotom', 'Mow Rotom'])
        rotom['Form'] = 'Wash Rotom'
        self.clear_poisoned_condition(game_data)
        game_data['weather'] = 'Rain'
        return f"Washing Machine used: {rotom['Name']} changed to Wash Rotom, poisoned status cleared, and rain weather set for 9 turns."

    def silk_sphere(self, plate, game_data):
        for opponent_pokemon in game_data['opponent_field']:
            if 'MP-reducing marker' in opponent_pokemon['Status Effects']:
                opponent_pokemon['Ability'] = None
        return f"Silk Sphere plate used, nullifying abilities of all opposing Pokémon with MP-reducing markers."

    def double_chance(self, plate, game_data):
        # Allows a player to respin once for the selected Pokémon.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['double_chance'] = True
        return f"Double Chance plate used. {chosen_pokemon['Name']} can respin once."

    def clear_wait(self, plate, game_data):
        # The selected Pokémon cannot have Wait.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['status_effects'].discard('Wait')
        return f"Clear Wait plate used. {chosen_pokemon['Name']} cannot have Wait."

    def focus_band(self, plate, game_data):
        # The selected Pokémon cannot be knocked out by attacks this turn.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['focus_band'] = True
        return f"Focus Band plate used. {chosen_pokemon['Name']} is protected this turn."

    def full_heal(self, plate, game_data):
        # Remove all special conditions from the selected Pokémon.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['status_effects'].clear()
        return f"Full Heal plate used. All conditions removed from {chosen_pokemon['Name']}."

    def scoop_up(self, plate, game_data):
        # Return the selected Pokémon to the bench.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        game_data['field'].remove(chosen_pokemon)
        game_data['bench'].append(chosen_pokemon)
        return f"Scoop Up plate used. {chosen_pokemon['Name']} returned to bench."

    def x_attack(self, plate, game_data):
        # The selected Pokémon deals +30 damage this turn.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['temporary_damage_boost'] = 30
        return f"X Attack plate used. {chosen_pokemon['Name']} deals +30 damage this turn."

    def pokemon_switch(self, plate, game_data):
        # Switch two Pokémon on the field or one with another on the bench.
        # Implementation logic goes here
        pass

    def swap_spot(self, plate, game_data):
        # Switch the positions of two of your Pokémon on the field.
        # Implementation logic goes here
        pass

    def x_defend(self, plate, game_data):
        # The selected Pokémon will not be knocked out by damage within the specified range.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['x_defend'] = True
        return f"X Defend plate used. {chosen_pokemon['Name']} has damage protection this turn."

    def no_guard(self, plate, game_data):
        # The selected Pokémon can spin again once if it spins a Blue Attack.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        chosen_pokemon['no_guard'] = True
        return f"No Guard plate used. {chosen_pokemon['Name']} can spin again if a Blue Attack is spun."

    def quick_care(self, plate, game_data):
        # Move the selected Pokémon to the P.C. if there's space. Your turn ends.
        chosen_pokemon = self.choose_pokemon_on_field(game_data)
        game_data['field'].remove(chosen_pokemon)
        # Assuming there is logic to put the Pokémon in P.C.
        self.admit_pokemon_to_pc(chosen_pokemon, game_data)
        game_data['turn_ends'] = True
        return f"Quick Care plate used. {chosen_pokemon['Name']} moved to P.C."

    def priority_recovery(self, plate, game_data):
        # Switch the order of Pokémon in the P.C.
        if len(game_data['pc']) >= 2:
            game_data['pc'].insert(0, game_data['pc'].pop())  # Move the last Pokémon to front
            game_data['turn_ends'] = True
            return "Priority Recovery plate used. The order in the P.C. has been changed."
        else:
            return "Priority Recovery plate could not be used. Not enough Pokémon in the P.C."

# Continue adding new methods here as new plates are needed

    def choose_pokemon_from_bench(self, game_data):
        # Logic to choose a Pokémon from the bench
        pass

    def place_pokemon_near_entry_point(self, chosen_pokemon, game_data):
        # Logic to place a chosen Pokémon near an entry point
        pass

    def choose_pokemon_on_field(self, game_data):
        # Logic to choose a Pokémon on the field
        pass

    def change_form_to_black_or_white_kyurem(self, kyurem):
        # Logically change Kyurem's form; for instance, modify its model or attack set
        kyurem['form'] = 'Black Kyurem'  # or 'White Kyurem' based on some condition or choice

    def exclude_pokemon_from_duel(self, pokemon, game_data):
        # Remove a Pokemon from the game logically; e.g., alter its status or remove from available Pokemon
        # Also assume there's some sort of 'excluded' status or list in game_data
        game_data['excluded_pokemon'].append(pokemon)

    def choose_pokemon_on_field_of_type(self, game_data, type):
        # Logic to choose a Pokémon of specific type on the field
        return next((p for p in game_data['field'] if p['Type'] == type), None)

    def choose_specific_pokemon_on_field(self, game_data, possible_names):
        # Logic to choose specific Pokémon on field given a list of possible names
        return next((p for p in game_data['field'] if p['Name'] in possible_names), None)

    def clear_burned_condition(self, game_data):
        # Logic to clear burned condition from all Pokémon
        for pokemon in game_data['all_pokemon']:
            pokemon['Status Effects'].discard('Burned')

    def clear_poisoned_condition(self, game_data):
        # Logic to clear poisoned condition from all Pokémon
        for pokemon in game_data['all_pokemon']:
            pokemon['Status Effects'].discard('Poisoned')

    def admit_pokemon_to_pc(self, pokemon, game_data):
        # Logic to place Pokémon in P.C.
        pass