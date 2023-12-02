import json
import random
import os
import logging
import re
import uuid
import discord
from discord import ButtonStyle, SelectOption, Interaction, Embed
from discord.ui import Select, View, Button
from .data.database import DatabaseManager
from .data import sprites
from .utils.constants import POKEMON_DATA_PATH, PLATES_PATH

logging.basicConfig(level=logging.INFO)


try:
    with open(POKEMON_DATA_PATH, 'r') as data_file:
        raw_pokemon_data = json.load(data_file)
    processed_pokemon_data = process_pokemon_data(raw_pokemon_data)

    with open(plates_path, 'r') as data_file:
        raw_plates_data = json.load(data_file)
    processed_plates_data = process_plates_data(raw_plates_data["plates"])
except FileNotFoundError as e:
    logging.error(f"File not found: {e.filename}")


class ShopView(View):
    def __init__(self, db_path, init_pokemon_data, init_plates_data):
        super().__init__()
        self.multi_roll_button = None
        self.single_roll_button = None
        self.check_balance_button = None
        self.view_inventory_button = None
        self.db = DatabaseManager(db_path)
        processed_pokemon_data_for_shop, processed_plates_data_for_shop = self.prepare_shop_data(init_pokemon_data,
                                                                                                 init_plates_data)
        self.pokemon_shop_data = processed_pokemon_data_for_shop
        self.plates_shop_data = processed_plates_data_for_shop
        self.initialize_buttons()
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
        self.clear_items()
        unique_suffix = str(uuid.uuid4())[:8]

        self.view_inventory_button = Button(label='View Inventory', style=ButtonStyle.secondary,
                                            custom_id='view_inventory')
        self.view_inventory_button.callback = self.view_inventory_callback
        self.add_item(self.view_inventory_button)

        self.check_balance_button = Button(label='Check Balance', style=ButtonStyle.secondary,
                                           custom_id=f'check_balance_{unique_suffix}')
        self.check_balance_button.callback = lambda interaction: self.check_balance_callback(interaction)
        self.add_item(self.check_balance_button)

        self.single_roll_button = Button(
            label='Roll',
            style=ButtonStyle.secondary,
            custom_id=f'roll_{unique_suffix}'
        )
        self.single_roll_button.callback = self.single_roll_callback
        self.add_item(self.single_roll_button)

        self.multi_roll_button = Button(
            label='Multi Roll',
            style=ButtonStyle.secondary,
            custom_id=f'multi_roll_{unique_suffix}'
        )
        self.multi_roll_button.callback = self.multi_roll_callback
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

        pokemon, rarity = self.roll()
        if pokemon:
            self.add_to_inventory(user_id, pokemon, rarity)
            self.db.update_crystals(user_id, current_crystals - 50)
            await interaction.response.send_message(f"You've got a {pokemon} of rarity {rarity}!", ephemeral=True)
        else:
            await interaction.response.send_message("No Pokémon were rolled. Your crystals have been refunded.",
                                                    ephemeral=True)

    async def multi_roll(self, interaction):
        user_id = interaction.user.id
        current_crystals = self.db.get_crystals(user_id)

        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return

        roll_results = self.roll(roll_count=10)
        if any(roll_results):
            for pokemon, rarity in roll_results:
                self.add_to_inventory(user_id, pokemon, rarity)
            self.db.update_crystals(user_id, current_crystals - 500)
            roll_results_message = f"You've got the following Pokémon: {', '.join([f'{pokemon} ({rarity})' for pokemon, rarity in roll_results])}"
            await interaction.response.send_message(roll_results_message, ephemeral=True)
        else:
            await interaction.response.send_message("No Pokémon were rolled. Your crystals have been refunded.",
                                                    ephemeral=True)

    async def flash_sale(self, interaction):
        self.generate_flash_sale_pokemon()
        flash_sale_msg = "Flash sale is live! The following Pokémon are available at half-off dust prices:\n"
        flash_sale_msg += "\n".join([f"{pokemon['name']} ({pokemon['rarity']})" for pokemon in self.flash_sale_pokemon])
        await interaction.response.send_message(flash_sale_msg, ephemeral=True)

    def roll(self, roll_count=1):
        """
        Performs roll(s) and returns a list of tuples (pokemon, rarity).
        """
        rarity_weights = {
            'EX': 0.075, 'UX': 0.075, 'R': 0.15, 'UC': 0.30, 'C': 0.40
        }
        pokemon_list = [(pokemon['name'], pokemon['rarity']) for pokemon in self.pokemon_shop_data]
        cumulative_weights = [rarity_weights[pokemon[1]] for pokemon in pokemon_list]

        return [random.choices(pokemon_list, weights=cumulative_weights, k=1)[0] for _ in range(roll_count)]

    async def handle_roll(self, user_id, roll_count, crystal_cost, interaction):
        logging.info(
            f"Initiating roll for user_id {user_id} with roll_count {roll_count} and crystal_cost {crystal_cost}")

        if not self.update_crystals(user_id, -crystal_cost):
            logging.warning(f"User {user_id} does not have enough crystals.")
            return False, "Not enough crystals."

        rolls = self.roll(roll_count)
        ex_ux_count = sum(1 for _, rarity in rolls if rarity in ["EX", "UX"])
        last_pokemon = next((pokemon for pokemon, rarity in rolls if rarity in ["EX", "UX"]), None)
        for pokemon, rarity in rolls:
            self.add_to_inventory(user_id, pokemon, rarity)

        user_mention = interaction.user.mention
        special_message = self.generate_special_message(ex_ux_count, roll_count, last_pokemon, rolls, user_mention)

        roll_results = ', '.join([f"{rarity} {pokemon}" for pokemon, rarity in rolls if pokemon])

        logging.info(f"Final message for user {user_id}: Roll Results: {roll_results} {special_message}")

        if interaction.channel.type == discord.ChannelType.private:
            return True, f"Roll Results: {roll_results}"

        if special_message:
            await interaction.followup.send(special_message)
        return True, f"Roll Results: {roll_results}"

    @staticmethod
    def generate_special_message(ex_ux_count, roll_count, last_pokemon, rolls, user_mention):
        special_message = ""
        if ex_ux_count >= 4 and roll_count > 1:
            ex_ux_pokemon_list = ', '.join(pokemon for pokemon, rarity in rolls if rarity in ["EX", "UX"])
            special_message = (f"🌟🎉 {user_mention} pulled over 4 EX/UX Pokémon: {ex_ux_pokemon_list}! "
                               f"🎊 Congratulations on this epic moment! 🌟")
        elif ex_ux_count > 0 and roll_count == 1 and last_pokemon:
            special_message = (f"🌟✨ {user_mention} pulled a rare {last_pokemon}! "
                               f"💫 Celebrate this amazing find! ✨🌟")
        return special_message

    async def view_inventory_callback(self, interaction: Interaction):
        user_id = interaction.user.id
        logging.debug(f"Starting inventory check for user_id: {user_id}")
        try:
            inventory = self.db.get_inventory(user_id)
            logging.debug(f"Inventory for user_id {user_id}: {inventory}")
            if not inventory:
                await interaction.response.send_message("Your inventory is empty.", ephemeral=True)
            else:
                inventory_view = InventoryView(user_id=user_id, db=self.db)
                await interaction.response.send_message(content=inventory_view.content, view=inventory_view,
                                                        ephemeral=True)
        except Exception as ex:
            logging.error(f"Error during inventory check for user {user_id}: {ex}", exc_info=True)
            await interaction.response.send_message("An error occurred while accessing your inventory.", ephemeral=True)
        logging.debug(f"Inventory check completed for user_id: {user_id}")

    async def single_roll_callback(self, interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        crystal_cost = 50
        success, message = await self.handle_roll(user_id, 1, crystal_cost, interaction)
        await interaction.followup.send(message, ephemeral=True)

    async def multi_roll_callback(self, interaction):
        user_id = interaction.user.id
        crystal_cost = 500
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        success, message = await self.handle_roll(user_id, 10, crystal_cost, interaction)
        await interaction.followup.send(message, ephemeral=True)

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
        logging.debug(f"Starting balance check for user_id: {user_id}")
        try:
            current_dust = self.db.get_dust(user_id)
            current_crystals = self.db.get_crystals(user_id)
            logging.debug(f"Dust: {current_dust}, Crystals: {current_crystals} for user_id: {user_id}")
            embed = Embed(title="Your Balances", color=0x00ff00)
            embed.add_field(name="Dust", value=f"{current_dust} 💨", inline=True)
            embed.add_field(name="Crystals", value=f"{current_crystals} 💎", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as ex:
            logging.error(f"Error during balance check for user {user_id}: {ex}", exc_info=True)
            await interaction.response.send_message("An error occurred while checking your balance.", ephemeral=True)
        logging.debug(f"Balance check completed for user_id: {user_id}")

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