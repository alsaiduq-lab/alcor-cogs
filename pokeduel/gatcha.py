import json
import random
import os
import logging
import re
import uuid
from discord import ButtonStyle, SelectOption, Interaction, Embed
from discord.ui import Select, View, Button
from .data.database import DatabaseManager


def find_strongest_attack(pokemon_data):
    max_effective_damage = 0
    strongest_attack = None
    for attack in pokemon_data["Base Wheel Size"]:
        try:
            damage = 0
            if attack["Move Type"] in ["White", "Blue"]:
                damage = int(attack["Damage"])
            elif attack["Move Type"] == "Purple":
                damage = 70
            elif attack["Move Type"] == "Gold":
                damage = int(attack["Damage"]) * 1.5

            if damage > max_effective_damage:
                max_effective_damage = damage
                strongest_attack = attack["Name"]
        except (ValueError, KeyError):
            continue

    return (strongest_attack, max_effective_damage) if strongest_attack else ("Unknown", 0)


def process_pokemon_data(pokemon_data):
    processed_data = []
    for name, details in pokemon_data.items():
        strongest_attack = find_strongest_attack(details)

        if strongest_attack and isinstance(strongest_attack, dict):
            processed_data.append({
                "name": name,
                "rarity": details["Rarity"],
                "strongest_attack": strongest_attack.get("Name", "Unknown"),
                "attack_damage": strongest_attack.get("Damage", "0")
            })
        else:
            processed_data.append({
                "name": name,
                "rarity": details["Rarity"],
                "strongest_attack": "Unknown",
                "attack_damage": "0"
            })

    return processed_data


def process_plates_data(plates_data):
    print("Type of plates_data:", type(plates_data))
    print("Content of plates_data:", plates_data)

    processed_data = []

    for plate in plates_data:
        cost = int(plate["Cost"]) if plate["Cost"].isdigit() else 0

        plate_info = {
            "id": plate["ID"],
            "name": plate["Name"],
            "cost": cost,
            "rarity": plate["Rarity"].strip(),
            "color": plate["Color"],
            "effect": plate["Effect"]
        }
        processed_data.append(plate_info)
        print("Processed plate info:", plate_info)

    return processed_data


def create_shop_data_template(pokemon_data, plates_data, num_pokemon=5, num_plates=3):
    if isinstance(pokemon_data, dict):
        pokemon_list = [{'name': name, **details} for name, details in pokemon_data.items()]
    else:
        pokemon_list = pokemon_data

    if 'plates' in plates_data:
        plates_list = [{'plate_id': re.search(r'\d+', plate['ID']).group(), **plate} for plate in plates_data['plates']]
    else:
        plates_list = plates_data

    num_pokemon = min(num_pokemon, len(pokemon_list))
    num_plates = min(num_plates, len(plates_list))

    selected_pokemon = random.sample(pokemon_list, num_pokemon) if num_pokemon > 0 else []
    selected_plates = random.sample(plates_list, num_plates) if num_plates > 0 else []

    pokemon_items = [process_pokemon(p) for p in selected_pokemon]
    plate_items = [process_plate(p) for p in selected_plates]

    return {"pokemon": pokemon_items, "plates": plate_items}


def process_pokemon(pokemon):
    attack_result = find_strongest_attack(pokemon)
    if attack_result:
        strongest_attack, attack_damage = attack_result
        return {
            "name": pokemon['name'],
            "rarity": pokemon['Rarity'],
            "strongest_attack": strongest_attack,
            "attack_damage": attack_damage
        }
    return {
        "name": pokemon['name'],
        "rarity": pokemon['Rarity'],
        "strongest_attack": "Unknown",
        "attack_damage": 0
    }


def process_plate(plate):
    return {
        "id": plate["plate_id"],
        "color": plate["Color"],
        "name": plate["Name"],
        "rarity": plate["Rarity"].strip(),
        "cost": int(plate["Cost"]) if plate["Cost"].isdigit() else 0,
        "effect": plate["Effect"]
    }


dir_path = os.path.dirname(os.path.abspath(__file__))
pokemon_data_path = os.path.join(dir_path, 'data', 'pokemon.json')
plates_path = os.path.join(dir_path, 'data', 'plates.json')

try:
    with open(pokemon_data_path, 'r') as data_file:
        raw_pokemon_data = json.load(data_file)
    processed_pokemon_data = process_pokemon_data(raw_pokemon_data)

    with open(plates_path, 'r') as data_file:
        raw_plates_data = json.load(data_file)
    processed_plates_data = process_plates_data(raw_plates_data["plates"])
except FileNotFoundError as e:
    logging.error(f"File not found: {e.filename}")


def roll(self):
    rarity_weights = {
        'EX': 0.075,
        'UX': 0.075,
        'R': 0.15,
        'UC': 0.30,
        'C': 0.40
    }
    pokemon_list = [(name, data['Rarity']) for name, data in self.pokemon_shop_data.items()]
    cumulative_weights = [rarity_weights[pokemon[1]] for pokemon in pokemon_list]
    chosen_pokemon = random.choices(pokemon_list, weights=cumulative_weights, k=1)[0]

    return chosen_pokemon[0], chosen_pokemon[1]



class ShopView(View):
    def __init__(self, db_path, init_pokemon_data, init_plates_data):
        super().__init__()
        self.db = DatabaseManager(db_path)
        processed_pokemon_data_for_shop, processed_plates_data_for_shop = self.prepare_shop_data(init_pokemon_data, init_plates_data)
        self.pokemon_shop_data = processed_pokemon_data_for_shop
        self.plates_shop_data = processed_plates_data_for_shop
        self.initialize_buttons()

        unique_suffix = str(uuid.uuid4())[:8]

        self.view_inventory_button = Button(label='View Inventory', style=ButtonStyle.secondary, custom_id=f'view_inventory_{unique_suffix}')
        self.view_inventory_button.callback = lambda interaction: self.view_inventory_callback(interaction)
        self.add_item(self.view_inventory_button)

        self.check_balance_button = Button(label='Check Balance', style=ButtonStyle.secondary,
                                           custom_id='check_balance')
        self.check_balance_button.callback = self.check_balance_callback
        self.add_item(self.check_balance_button)

        self.single_roll_button = Button(label='Roll', style=ButtonStyle.secondary, custom_id='roll')
        self.single_roll_button.callback = self.single_roll_callback
        self.add_item(self.single_roll_button)

        self.multi_roll_button = Button(label='Multi Roll', style=ButtonStyle.secondary,
                                        custom_id=f'multi_roll_{unique_suffix}')
        self.multi_roll_button.callback = lambda interaction: self.multi_roll_callback(interaction)
        self.add_item(self.multi_roll_button)

        self.flash_sale_button = None
        self.flash_sale_pokemon = []

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

    def prepare_shop_data(self, pokemon_data, plates_data):
        self.pokemon_shop_data = process_pokemon_data(pokemon_data)
        self.plates_shop_data = process_plates_data(plates_data)
        return process_pokemon_data(pokemon_data), process_plates_data(plates_data)

    def initialize_buttons(self):
        unique_suffix = str(uuid.uuid4())[:8]

        self.view_inventory_button = Button(label='View Inventory', style=ButtonStyle.secondary,
                                            custom_id=f'view_inventory_{unique_suffix}')
        self.view_inventory_button.callback = lambda interaction: self.view_inventory_callback(interaction)
        self.add_item(self.view_inventory_button)

        self.check_balance_button = Button(label='Check Balance', style=ButtonStyle.secondary,
                                           custom_id=f'check_balance_{unique_suffix}')
        self.check_balance_button.callback = lambda interaction: self.check_balance_callback(interaction)
        self.add_item(self.check_balance_button)

        self.single_roll_button = Button(label='Roll', style=ButtonStyle.secondary,
                                         custom_id=f'roll_{unique_suffix}')
        self.single_roll_button.callback = lambda interaction: self.single_roll_callback(interaction)
        self.add_item(self.single_roll_button)

        self.multi_roll_button = Button(label='Multi Roll', style=ButtonStyle.secondary,
                                        custom_id=f'multi_roll_{unique_suffix}')
        self.multi_roll_button.callback = lambda interaction: self.multi_roll_callback(interaction)
        self.add_item(self.multi_roll_button)

    @staticmethod
    def process_shop_data(pokemon_data, plates_data):
        process_for_shop_pokemon_data = process_pokemon_data(pokemon_data)
        process_for_shop_plates_data = process_plates_data(plates_data)
        return process_for_shop_pokemon_data, process_for_shop_plates_data

    @staticmethod
    def create_button(label, custom_id, callback_method, style=ButtonStyle.secondary, roll_count=1):
        button = Button(label=label, style=style, custom_id=custom_id)
        button.callback = lambda interaction: callback_method(interaction, roll_count)
        return button

    async def single_roll(self, interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)
        if current_crystals < 50:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return

        self.db.update_crystals(user_id, current_crystals - 50)
        pokemon, rarity = self.roll()
        self.add_to_inventory(user_id, pokemon, rarity)
        await interaction.response.send_message(f"You've got a {pokemon} of rarity {rarity}!", ephemeral=True)

    async def multi_roll(self, interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)
        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return

        self.db.update_crystals(user_id, current_crystals - 500)
        rolls = [self.roll() for _ in range(10)]
        for pokemon, rarity in rolls:
            self.add_to_inventory(user_id, pokemon, rarity)

        roll_messages = [f"{pokemon} ({rarity})" for pokemon, rarity in rolls]
        await interaction.response.send_message(f"You've got the following Pokémon: {', '.join(roll_messages)}", ephemeral=True)

    async def flash_sale(self, interaction):
        self.generate_flash_sale_pokemon()
        flash_sale_msg = "Flash sale is live! The following Pokémon are available at half-off dust prices:\n"
        flash_sale_msg += "\n".join([f"{pokemon['name']} ({pokemon['rarity']})" for pokemon in self.flash_sale_pokemon])
        await interaction.response.send_message(flash_sale_msg, ephemeral=True)

    def handle_roll(self, user_id, roll_count, crystal_cost):
        if not self.update_crystals(user_id, -crystal_cost):
            return False, "Not enough crystals."
        rolls = [self.roll() for _ in range(roll_count)]
        self.add_to_inventory(user_id, rolls)
        roll_results = ', '.join([f"{rarity} {pokemon}" for pokemon, rarity in rolls if pokemon])
        return True, f"Roll Results: {roll_results}"

    async def view_inventory_callback(self, interaction: Interaction):
        # Logic to display the user's inventory
        pass

    async def single_roll_callback(self, interaction, roll_count):
        user_id = interaction.user.id
        crystal_cost = 50 if roll_count == 1 else 500
        success, message = self.handle_roll(user_id, roll_count, crystal_cost)
        await interaction.response.send_message(message, ephemeral=True)

    async def multi_roll_callback(self, interaction: Interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)

        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals for a multi roll.", ephemeral=True)
            return

        self.db.update_crystals(user_id, current_crystals - 500)
        rolls = []
        for _ in range(10):
            rolled_pokemon = self.roll()
            if rolled_pokemon:
                pokemon_name, rarity = rolled_pokemon
                self.add_to_inventory(user_id, pokemon_name, rarity)
                rolls.append(f"{rarity} {pokemon_name}")

        if rolls:
            await interaction.response.send_message(f"Multi roll results: {', '.join(rolls)}", ephemeral=True)
        else:
            await interaction.response.send_message("No Pokémon found to roll.", ephemeral=True)

    def update_crystals(self, user_id, amount):
        current_crystals = self.db.get_crystals(user_id)
        if current_crystals + amount < 0:
            return False
        self.db.update_crystals(user_id, current_crystals + amount)
        return True

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

    async def check_balance_callback(self, interaction: Interaction):
        user_id = interaction.user.id
        current_dust = self.db.get_dust(user_id)
        current_crystals = self.db.get_crystals(user_id)
        embed = Embed(title="Your Balances", color=0x00ff00)
        embed.add_field(name="Dust", value=f"{current_dust} 💨", inline=True)
        embed.add_field(name="Crystals", value=f"{current_crystals} 💎", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

        pokemon_details = next(item for item in self.pokemon_shop_data if item["name"] == selected_pokemon)
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
