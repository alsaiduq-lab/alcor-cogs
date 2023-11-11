import json
import random
from discord import ButtonStyle, SelectOption
from discord.ext import commands
from pokeduel.data.database import DatabaseManager

with open('plates.json', 'r') as f:
    plates_data = json.load(f)

class ShopView(commands.View):
    def __init__(self, user_id, db_path, shop_data, plates_data):
        super().__init__()
        self.user_id = user_id
        self.db = DatabaseManager(db_path)
        self.shop_data = shop_data
        self.plates_data = plates_data

        self.current_crystals = self.db.get_crystals(user_id)
        self.current_dust = self.db.get_dust(user_id)

        self.add_item(self.create_select_menu('Select a Pokémon to buy with dust', shop_data, 'pokemon'))
        self.add_item(self.create_select_menu('Select a Plate to buy with dust', plates_data, 'plate'))

        self.add_roll_buttons()

    def create_select_menu(self, placeholder, data, custom_id):
        options = [SelectOption(label=item['name'], value=item['name']) for item in data]
        return Select(placeholder=placeholder, options=options, custom_id=custom_id)

    def add_roll_buttons(self):
        self.add_item(Button(label='Single Roll (50 Crystals)', style=ButtonStyle.primary, custom_id='single_roll', emoji='🎲'))
        self.add_item(Button(label='Multi Roll (10x for 500 Crystals)', style=ButtonStyle.primary, custom_id='multi_roll', emoji='🎰'))
        self.add_item(Button(label='Flash Sale!', style=ButtonStyle.danger, custom_id='flash_sale', emoji='⚡'))

    def roll(self):
        rolled_pokemon = random.choice(self.shop_data)
        return rolled_pokemon['name'], rolled_pokemon['rarity']

    def add_to_inventory(self, item, rarity):
        self.db.add_to_inventory(self.user_id, item, rarity)

    def generate_flash_sale_pokemon(self):
        self.shop_data = self.load_pokemon_data()
        ex_ux_pokemon = [pokemon for pokemon in self.shop_data if pokemon['rarity'] in ['EX', 'UX']]
        other_pokemon = [pokemon for pokemon in self.shop_data if pokemon['rarity'] not in ['EX', 'UX']]

        self.flash_sale_pokemon = random.sample(ex_ux_pokemon, 1) + random.sample(other_pokemon, 1)

    @Select(placeholder='Select a Pokémon to buy with dust', options=self.pokemon_options)
    async def select_pokemon(self, select, interaction):
        selected_pokemon = select.values[0]
        selected_rarity = next(item for item in self.shop_data if item["name"] == selected_pokemon)["rarity"]

        dust_cost = 0
        if selected_rarity == 'UX' or selected_rarity == 'EX':
            dust_cost = 5000
        elif selected_rarity == 'R':
            dust_cost = 2000
        elif selected_rarity == 'UC':
            dust_cost = 1000
        elif selected_rarity == 'C':
            dust_cost = 500

        self.current_dust = self.db.get_dust(self.user_id)
        if self.current_dust < dust_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.add_to_inventory(self.user_id, selected_pokemon, selected_rarity)

        self.db.update_dust(self.user_id, self.current_dust - dust_cost)

        await interaction.response.send_message(f"You've bought a {selected_pokemon}!", ephemeral=True)

    @Select(placeholder='Select a Plate to buy with dust', options=self.plate_options)
    async def select_plate(self, select, interaction):
        selected_plate = select.values[0]
        plate_cost = next(item for item in self.plates_data if item["name"] == selected_plate)["cost"]

        self.current_dust = self.db.get_dust(self.user_id)
        if self.current_dust < plate_cost:
            await interaction.response.send_message("Not enough dust.", ephemeral=True)
            return

        self.db.add_plate_to_inventory(self.user_id, selected_plate)
        self.db.update_dust(self.user_id, self.current_dust - plate_cost)

        await interaction.response.send_message(f"You've bought a {selected_plate} for {plate_cost} dust!",
                                                ephemeral=True)

    @Button(label='Single Roll (50 Crystals)', style=ButtonStyle.primary, custom_id='single_roll', emoji='🎲')
    async def single_roll(self, button, interaction):
        self.current_crystals = self.db.get_crystals(self.user_id)
        if self.current_crystals < 50:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = self.current_crystals - 50

        self.db.update_crystals(self.user_id, new_crystal_count)

        pokemon, rarity = self.roll(self.user_id)
        self.add_to_inventory(self.user_id, pokemon, rarity)

        await interaction.response.send_message(f"You've got a {pokemon} of rarity {rarity}!", ephemeral=True)

    @Button(label='Multi Roll (10x for 500 Crystals)', style=ButtonStyle.primary, custom_id='multi_roll', emoji='🎰')
    async def multi_roll(self, button, interaction):
        current_crystals = self.db.get_crystals(self.user_id)
        if current_crystals < 500:
            await interaction.response.send_message("Not enough crystals.", ephemeral=True)
            return
        new_crystal_count = current_crystals - 500
        self.db.update_crystals(self.user_id, new_crystal_count)

        rolls = []
        for _ in range(10):
            pokemon, rarity = self.roll(self.user_id)
            self.add_to_inventory(self.user_id, pokemon, rarity)
            rolls.append(f"{pokemon} ({rarity})")

        await interaction.response.send_message(f"You've got the following Pokémon: {', '.join(rolls)}", ephemeral=True)

    @Button(label='Flash Sale!', style=ButtonStyle.danger, custom_id='flash_sale', emoji='⚡')
    async def flash_sale(self, button, interaction):
        self.generate_flash_sale_pokemon()
        flash_sale_msg = "Flash sale is live! The following Pokémon are available at half-off dust prices:\n"
        flash_sale_msg += "\n".join([f"{pokemon['name']} ({pokemon['rarity']})" for pokemon in self.flash_sale_pokemon])
        await interaction.response.send_message(flash_sale_msg, ephemeral=True)