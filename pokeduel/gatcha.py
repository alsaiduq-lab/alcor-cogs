import json
import random
import os
import logging
from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button
from .data.database import DatabaseManager


def find_strongest_attack(pokemon_data):
    max_effective_damage = 0
    strongest_attack = None
    for attack in pokemon_data["Base Wheel Size"]:
        try:
            if attack["Move Type"] == "White" or attack["Move Type"] == "Blue":
                damage = int(attack["Damage"])
            elif attack["Move Type"] == "Purple":
                damage = 70
            elif attack["Move Type"] == "Gold":
                damage = int(attack["Damage"]) * 1.5
            else:
                damage = 0

            if damage > max_effective_damage:
                max_effective_damage = damage
                strongest_attack = attack
        except ValueError:
            continue
    return strongest_attack


def process_pokemon_data(pokemon_data):
    processed_data = []
    for name, details in pokemon_data.items():
        strongest_attack = find_strongest_attack(details)
        if strongest_attack:
            processed_data.append({
                "name": name,
                "rarity": details["Rarity"],
                "strongest_attack": strongest_attack["Name"],
                "attack_damage": strongest_attack["Damage"]
            })
    return processed_data



def process_plates_data(plates_data):
    processed_data = []
    for plate in plates_data:
        plate_info = {
            "name": plate["Name"],
            "cost": int(plate["Cost"]),
            "rarity": plate["Rarity"].strip(),
            "color": plate["Color"],
            "effect": plate["Effect"]
        }
        processed_data.append(plate_info)
    return processed_data


def create_shop_data_template(pokemon_data, plates_data, num_pokemon=5, num_plates=3):
    selected_pokemon = random.sample(pokemon_data, num_pokemon)
    selected_plates = random.sample(plates_data, num_plates)

    pokemon_items = []
    for pokemon in selected_pokemon:
        strongest_attack, attack_damage = find_strongest_attack(pokemon)
        pokemon_items.append({
            "name": pokemon['name'],
            "rarity": pokemon['rarity'],
            "strongest_attack": strongest_attack,
            "attack_damage": attack_damage
        })
    plate_items = []
    for plate in selected_plates:
        plate_items.append({
            "id": plate["ID"],
            "color": plate["Color"],
            "name": plate["Name"],
            "rarity": plate["Rarity"].strip(),
            "cost": int(plate["Cost"]),
            "effect": plate["Effect"]
        })

    return {"pokemon": pokemon_items, "plates": plate_items}


dir_path = os.path.dirname(os.path.abspath(__file__))
pokemon_data_path = os.path.join(dir_path, 'data', 'pokemon.json')
plates_path = os.path.join(dir_path, 'data', 'plates.json')

try:
    with open(pokemon_data_path, 'r') as data_file:
        raw_pokemon_data = json.load(data_file)
    processed_pokemon_data = process_pokemon_data(raw_pokemon_data)

    with open(plates_path, 'r') as data_file:
        raw_plates_data = json.load(data_file)
    processed_plates_data = process_plates_data(raw_plates_data)

except FileNotFoundError as e:
    logging.error(f"File not found: {e.filename}")


class ShopView(View):
    def __init__(self, db_path, init_pokemon_data, init_plates_data):
        super().__init__()
        self.db = DatabaseManager(db_path)

        self.single_roll_button = None
        self.multi_roll_button = None
        self.flash_sale_button = None
        self.flash_sale_pokemon = []

        shop_data = create_shop_data_template(init_pokemon_data, init_plates_data)

        self.pokemon_shop_data = shop_data['pokemon']
        self.plates_shop_data = shop_data['plates']
        self.shop_data = self.pokemon_shop_data
        self.plate_options = [
            SelectOption(
                label=f"{plate['name']} - Cost: {plate['cost']}, Rarity: {plate['rarity']}, Color: {plate['color']}",
                value=plate['name'],
                description=plate['effect']
            )
            for plate in self.plates_shop_data
        ]
        self.pokemon_options = [
            SelectOption(label=pokemon['name'] + " - " + pokemon['strongest_attack'], value=pokemon['name'])
            for pokemon in self.pokemon_shop_data
        ]
        self.initialize_roll_buttons()

    def initialize_roll_buttons(self):
        self.single_roll_button = Button(label='Single Roll (50 Crystals)', style=ButtonStyle.primary,
                                         custom_id='single_roll', emoji='🎲')
        self.single_roll_button.callback = self.single_roll
        self.add_item(self.single_roll_button)

        self.multi_roll_button = Button(label='Multi Roll (10x for 500 Crystals)', style=ButtonStyle.primary,
                                        custom_id='multi_roll', emoji='🎰')
        self.multi_roll_button.callback = self.multi_roll
        self.add_item(self.multi_roll_button)

        self.flash_sale_button = Button(label='Flash Sale!', style=ButtonStyle.danger, custom_id='flash_sale',
                                        emoji='⚡')
        self.flash_sale_button.callback = self.flash_sale
        self.add_item(self.flash_sale_button)

    async def single_roll(self, interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)
        if current_crystals < 50:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = current_crystals - 50
        self.db.update_crystals(user_id, new_crystal_count)

        pokemon, rarity = self.roll()
        self.add_to_inventory(user_id, pokemon, rarity)
        await interaction.response.send_message(f"You've got a {pokemon} of rarity {rarity}!", ephemeral=True)

    async def multi_roll(self, interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)
        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = current_crystals - 500
        self.db.update_crystals(user_id, new_crystal_count)

        rolls = []
        for _ in range(10):
            pokemon, rarity = self.roll()
            self.add_to_inventory(user_id, pokemon, rarity)
            rolls.append(f"{pokemon} ({rarity})")

        await interaction.response.send_message(f"You've got the following Pokémon: {', '.join(rolls)}", ephemeral=True)

    async def flash_sale(self, interaction):
        self.generate_flash_sale_pokemon()
        flash_sale_msg = "Flash sale is live! The following Pokémon are available at half-off dust prices:\n"
        flash_sale_msg += "\n".join([f"{pokemon['name']} ({pokemon['rarity']})" for pokemon in self.flash_sale_pokemon])
        await interaction.response.send_message(flash_sale_msg, ephemeral=True)

    def roll(self):
        if self.shop_data:
            rolled_pokemon = random.choice(self.shop_data)
            return rolled_pokemon['name'], rolled_pokemon['rarity']
        else:
            return None, None

    def add_to_inventory(self, user_id, item, rarity):
        self.db.add_to_inventory(user_id, item, rarity)

    def create_pokemon_select_menu(self):
        pokemon_select = Select(
            placeholder='Select a Pokémon to buy with dust',
            options=self.pokemon_options,
            custom_id='pokemon_select'
        )
        pokemon_select.callback = self.select_pokemon_callback
        return pokemon_select

    def create_plate_select_menu(self):
        plate_select = Select(
            placeholder='Select a Plate to buy with dust',
            options=[
                SelectOption(
                    label=f"{plate['name']} (Cost: {plate['cost']}, Rarity: {plate['rarity']}, Color: {plate['color']})",
                    value=plate['name'],
                    description=f"Effect: {plate['effect'][:100]}..."
                )
                for plate in self.plates_shop_data
            ],
            custom_id='plate_select'
        )
        plate_select.callback = self.select_plate_callback
        return plate_select

    def generate_flash_sale_pokemon(self):
        ex_ux_pokemon = [pokemon for pokemon in self.pokemon_shop_data if pokemon['rarity'] in ['EX', 'UX']]
        other_pokemon = [pokemon for pokemon in self.pokemon_shop_data if pokemon['rarity'] not in ['EX', 'UX']]

        if len(ex_ux_pokemon) > 0 and len(other_pokemon) > 0:
            self.flash_sale_pokemon = random.sample(ex_ux_pokemon, 1) + random.sample(other_pokemon, 1)
        else:
            self.flash_sale_pokemon = []

    @staticmethod
    def calculate_dust_cost(rarity):
        if rarity == 'UX' or rarity == 'EX':
            return 5000
        elif rarity == 'R':
            return 2000
        elif rarity == 'UC':
            return 1000
        elif rarity == 'C':
            return 500
        else:
            return 0

    async def select_pokemon_callback(self, select, interaction):
        user_id = interaction.user.id
        selected_pokemon = select.values[0]
        pokemon_details = next(item for item in self.shop_data if item["name"] == selected_pokemon)
        dust_cost = self.calculate_dust_cost(pokemon_details['rarity'])

        current_dust = self.db.get_dust(user_id)
        if current_dust < dust_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.add_to_inventory(user_id, selected_pokemon, pokemon_details['rarity'])
        self.db.update_dust(user_id, current_dust - dust_cost)
        await interaction.response.send_message(f"You've bought a {selected_pokemon}!", ephemeral=True)

    async def select_plate_callback(self, select, interaction):
        user_id = interaction.user.id
        selected_plate = select.values[0]
        plate_details = next(item for item in self.plates_shop_data if item["name"] == selected_plate)
        plate_cost = plate_details['cost']

        current_dust = self.db.get_dust(user_id)
        if current_dust < plate_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.db.add_plate_to_inventory(user_id, selected_plate)
        self.db.update_dust(user_id, current_dust - plate_cost)
        await interaction.response.send_message(f"You've bought a {selected_plate} for {plate_cost} dust!",
                                                ephemeral=True)
