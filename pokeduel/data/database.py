import sqlite3
import json
from discord.ext import commands
from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button


class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    crystals INTEGER,
                    dust INTEGER,
                    inventory TEXT,
                    party TEXT 
                );
            ''')

    def initialize_new_user(self, user_id, crystals=0, dust=0, inventory=None, party=None):
        if inventory is None:
            inventory = json.dumps([])
        if party is None:
            party = json.dumps([])
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO users (id, crystals, dust, inventory, party) VALUES (?, ?, ?, ?, ?)",
                              (user_id, crystals, dust, inventory, party))

    def get_crystals(self, user_id):
        with self.conn:
            cur = self.conn.execute("SELECT crystals FROM users WHERE id = ?", (user_id,))
            return cur.fetchone()[0]

    def update_crystals(self, user_id, new_crystal_count):
        with self.conn:
            self.conn.execute("UPDATE users SET crystals = ? WHERE id = ?", (new_crystal_count, user_id))

    def get_dust(self, user_id):
        with self.conn:
            cur = self.conn.execute("SELECT dust FROM users WHERE id = ?", (user_id,))
            return cur.fetchone()[0]

    def update_dust(self, user_id, new_dust_amount):
        with self.conn:
            self.conn.execute("UPDATE users SET dust = ? WHERE id = ?", (new_dust_amount, user_id))

    def get_inventory(self, user_id):
        with self.conn:
            cur = self.conn.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
            inventory_str = cur.fetchone()[0]
            return json.loads(inventory_str)

    def update_inventory(self, user_id, new_inventory):
        with self.conn:
            inventory_str = json.dumps(new_inventory)
            self.conn.execute("UPDATE users SET inventory = ? WHERE id = ?", (inventory_str, user_id))

    def get_user_party(self, user_id):
        with self.conn:
            cur = self.conn.execute("SELECT party FROM users WHERE id = ?", (user_id,))
            party_str = cur.fetchone()[0]
            return json.loads(party_str)

    def update_user_party(self, user_id, new_party):
        with self.conn:
            party_str = json.dumps(new_party)
            self.conn.execute("UPDATE users SET party = ? WHERE id = ?", (party_str, user_id))


class PokemonSelect(Select):
    def __init__(self, db, user_id, placeholder, callback_method):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.db = db
        self.user_id = user_id
        self.callback_method = callback_method
        self.populate_options()

    def populate_options(self):
        available_items = self.db.get_inventory(self.user_id)
        self.options = [SelectOption(label=item, value=item) for item in available_items]

    async def callback(self, interaction):
        selected_item = self.values[0]
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
        for i, item in enumerate(party):
            self.add_item(Button(style=ButtonStyle.primary, label=item, custom_id=f"remove_{i}"))

        self.add_item(PokemonSelect(self.db, self.user_id, 'Add to Party', self.add_to_party))

    async def add_to_party(self, select, item, interaction):
        party = self.db.get_user_party(self.user_id)
        party.append(item)
        self.db.update_user_party(self.user_id, party)
        self.refresh_view()
        await interaction.response.send_message(f"{item} added to your party!", ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, interaction):
        custom_id = interaction.data['custom_id']
        action, index = custom_id.split("_")
        if action == "remove":
            self.db.remove_item_from_party(self.user_id, int(index))
            self.refresh_view()
            await interaction.response.send_message("Item removed from your party.", ephemeral=True)


class PartyManager(commands.Cog):
    def __init__(self, bot, db_path):
        self.bot = bot
        self.db_manager = DatabaseManager(db_path)


    @commands.command()
    async def party(self, ctx):
        view = PartyButtonView(self.db, ctx.author.id)
        await ctx.send("Your party:", view=view)
