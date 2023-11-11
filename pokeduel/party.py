from discord.ext import commands
from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button


class PartyManager(commands.Cog):
    def __init__(self, bot, db_path):
        self.bot = bot
        self.db_manager = PartyDatabaseManager(db_path)

    @commands.command()
    async def party(self, ctx):
        view = PartyButtonView(self.db_manager, ctx.author.id)
        await ctx.send("Your party:", view=view)

class PokemonSelect(Select):
    def __init__(self, db, user_id, placeholder, callback_method, is_z_move_select=False):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.db = db
        self.user_id = user_id
        self.callback_method = callback_method
        self.is_z_move_select = is_z_move_select
        self.populate_options()

    def populate_options(self):
        if self.is_z_move_select:
            party = self.db.get_user_party(self.user_id)
            for pokemon_name in party:
                pokemon_data = self.db.get_pokemon_data(pokemon_name)
                z_moves = [move['Name'] for move in pokemon_data['Base Wheel Size'] if 'Z-Move' in move['Move Type']]
                for z_move in z_moves:
                    self.options.append(SelectOption(label=f"{pokemon_name}: {z_move}", value=f"{pokemon_name}:{z_move}"))
        else:
            # Standard implementation for adding Pokémon to party
            available_pokemon = self.db.get_inventory(self.user_id)
            self.options = [SelectOption(label=pokemon, value=pokemon) for pokemon in available_pokemon]

    async def callback(self, interaction):
        selected_item = self.values[0]
        if self.is_z_move_select:
            pokemon, z_move = selected_item.split(":")
            self.db.set_pokemon_z_move(self.user_id, pokemon, z_move)
            await interaction.response.send_message(f"Selected Z-Move {z_move} for {pokemon}.", ephemeral=True)
        else:
            await self.callback_method(self, selected_item, interaction)

class PartyButtonView(View):
    def __init__(self, db, user_id):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.refresh_view()

    def refresh_view(self):
        self.clear_items()
        party = self.db.get_user_party(self.user_id)
        for i, pokemon in enumerate(party):
            self.add_item(Button(style=ButtonStyle.primary, label=pokemon, custom_id=f"remove_{i}"))

        self.add_item(PokemonSelect(self.db, self.user_id, 'Add to Party', self.add_to_party))
        self.add_item(PokemonSelect(self.db, self.user_id, 'Select Z-Move', self.select_z_move, is_z_move_select=True))

    async def add_pokemon_to_party(self, select, pokemon, interaction):
        try:
            party = self.db.get_user_party(self.user_id)
            if len(party) < MAX_PARTY_SIZE:
                party.append(pokemon)
                self.db.update_user_party(self.user_id, party)
                await interaction.response.send_message(f"{pokemon} added to your party!", ephemeral=True)
            else:
                await interaction.response.send_message("Your party is full.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    async def add_plate_to_party(self, select, plate, interaction):
        try:
            party = self.db.get_user_party(self.user_id)
            if len(party) < MAX_PARTY_SIZE:  # Assuming a limit to the party size
                party.append(plate)
                self.db.update_user_party(self.user_id, party)
                await interaction.response.send_message(f"{plate} added to your party!", ephemeral=True)
            else:
                await interaction.response.send_message("Your party is full.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    def remove_item_from_party(self, user_id, index):
        party = self.get_user_party(user_id)
        if 0 <= index < len(party):
            del party[index]
            self.update_user_party(user_id, party)

    async def on_button_click(self, interaction):
        custom_id = interaction.data['custom_id']
        action, index = custom_id.split("_")
        if action == "remove":
            self.db.remove_item_from_party(self.user_id, int(index))
            self.refresh_view()
            await interaction.response.send_message("Item removed from your party.", ephemeral=True)

