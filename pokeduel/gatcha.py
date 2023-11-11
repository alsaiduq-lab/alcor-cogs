import json
import random
import os
import logging

from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button
from discord.ext import commands
from pokeduel.data.database import DatabaseManager


dir_path = os.path.dirname(os.path.abspath(__file__))
plates_path = os.path.join(dir_path, 'data', 'plates.json')

logging.debug(f"Attempting to open file at: {plates_path}")

try:
    with open(plates_path, 'r') as f:
        plates_data = json.load(f)
except FileNotFoundError as e:
    logging.error(f"File not found: {plates_path}")
    raise e


class ShopView(View):
    def __init__(self, user_id, db_path, shop_data, plates_data):
        super().__init__()
        self.user_id = user_id
        self.db = DatabaseManager(db_path)
        self.shop_data = shop_data
        self.plates_data = plates_data
        self.add_item(self.create_pokemon_select_menu())
        self.add_item(self.create_plate_select_menu())

        self.pokemon_options = [SelectOption(label=pokemon['name'], value=pokemon['name']) for pokemon in shop_data]
        self.plate_options = [SelectOption(label=plate['name'], value=plate['name']) for plate in plates_data]

        self.current_crystals = self.db.get_crystals(user_id)
        self.current_dust = self.db.get_dust(user_id)

        self.add_item(self.create_select_menu('Select a Pokémon to buy with dust', 'pokemon'))
        self.add_item(self.create_select_menu('Select a Plate to buy with dust', 'plate'))

        self.add_roll_buttons()
        self.single_roll_button = Button(label='Single Roll (50 Crystals)', style=ButtonStyle.primary, custom_id='single_roll', emoji='🎲')
        self.single_roll_button.callback = self.single_roll
        self.add_item(self.single_roll_button)

        self.multi_roll_button = Button(label='Multi Roll (10x for 500 Crystals)', style=ButtonStyle.primary, custom_id='multi_roll', emoji='🎰')
        self.multi_roll_button.callback = self.multi_roll
        self.add_item(self.multi_roll_button)

        self.flash_sale_button = Button(label='Flash Sale!', style=ButtonStyle.danger, custom_id='flash_sale', emoji='⚡')
        self.flash_sale_button.callback = self.flash_sale
        self.add_item(self.flash_sale_button)

    async def single_roll(self, interaction):
        self.current_crystals = self.db.get_crystals(self.user_id)
        if self.current_crystals < 50:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = self.current_crystals - 50
        self.db.update_crystals(self.user_id, new_crystal_count)

        pokemon, rarity = self.roll()
        self.add_to_inventory(pokemon, rarity)
        await interaction.response.send_message(f"You've got a {pokemon} of rarity {rarity}!", ephemeral=True)

    async def multi_roll(self, interaction):
        current_crystals = self.db.get_crystals(self.user_id)
        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = current_crystals - 500
        self.db.update_crystals(self.user_id, new_crystal_count)

        rolls = []
        for _ in range(10):
            pokemon, rarity = self.roll()
            self.add_to_inventory(pokemon, rarity)
            rolls.append(f"{pokemon} ({rarity})")

        await interaction.response.send_message(f"You've got the following Pokémon: {', '.join(rolls)}", ephemeral=True)

    async def flash_sale(self, interaction):
        self.generate_flash_sale_pokemon()
        flash_sale_msg = "Flash sale is live! The following Pokémon are available at half-off dust prices:\n"
        flash_sale_msg += "\n".join([f"{pokemon['name']} ({pokemon['rarity']})" for pokemon in self.flash_sale_pokemon])
        await interaction.response.send_message(flash_sale_msg, ephemeral=True)

    @staticmethod
    def load_pokemon_data():
        pokemon_data_path = os.path.join(dir_path, 'data', 'pokemon.json')
        try:
            with open(pokemon_data_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"File not found: {pokemon_data_path}")
            return []



    def roll(self):
        rolled_pokemon = random.choice(self.shop_data)
        return rolled_pokemon['name'], rolled_pokemon['rarity']

    def add_to_inventory(self, item, rarity):
        self.db.add_to_inventory(self.user_id, item, rarity)

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
            options=self.plate_options,
            custom_id='plate_select'
        )
        plate_select.callback = self.select_plate_callback
        return plate_select

    def generate_flash_sale_pokemon(self):
        self.shop_data = self.load_pokemon_data()
        ex_ux_pokemon = [pokemon for pokemon in self.shop_data if pokemon['rarity'] in ['EX', 'UX']]
        other_pokemon = [pokemon for pokemon in self.shop_data if pokemon['rarity'] not in ['EX', 'UX']]

        self.flash_sale_pokemon = random.sample(ex_ux_pokemon, 1) + random.sample(other_pokemon, 1)

    def calculate_dust_cost(self, rarity):
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
        selected_pokemon = select.values[0]
        pokemon_details = next(item for item in self.shop_data if item["name"] == selected_pokemon)
        dust_cost = self.calculate_dust_cost(pokemon_details['rarity'])

        self.current_dust = self.db.get_dust(self.user_id)
        if self.current_dust < dust_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.add_to_inventory(self.user_id, selected_pokemon, pokemon_details['rarity'])
        self.db.update_dust(self.user_id, self.current_dust - dust_cost)
        await interaction.response.send_message(f"You've bought a {selected_pokemon}!", ephemeral=True)



    async def select_plate_callback(self, select, interaction):
        selected_plate = select.values[0]
        plate_details = next(item for item in self.plates_data if item["name"] == selected_plate)
        plate_cost = plate_details['cost']

        self.current_dust = self.db.get_dust(self.user_id)
        if self.current_dust < plate_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.db.add_plate_to_inventory(self.user_id, selected_plate)
        self.db.update_dust(self.user_id, self.current_dust - plate_cost)
        await interaction.response.send_message(f"You've bought a {selected_plate} for {plate_cost} dust!",
                                                ephemeral=True)
