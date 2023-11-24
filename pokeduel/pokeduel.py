import asyncio
import json
import os
from datetime import datetime, timedelta

import discord
from discord import Interaction, ui, ButtonStyle, Member, Embed
from discord.ui import View, Button
from redbot.core import commands, Config

from .data.database import DatabaseManager
from .gatcha import ShopView
from .ingame import GameManager
from .party import PartyManager, PartyButtonView
from .utils.board import BoardManager


# predicate saves
def has_started_save():
    async def predicate(ctx):
        return ctx.cog.db.has_started_save(ctx.author.id)

    return commands.check(predicate)


class PokeDuel(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._load_data()
        self.db = DatabaseManager(self.db_path)
        self._initialize_managers()
        self._register_default_user_config()
        self.matchmaking_queue = {}
        self.ongoing_duels = {}

    @staticmethod
    def load_json(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)

    def _load_data(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.db_path = os.path.join(dir_path, 'data', 'pokeduel_db.sqlite')
        self.plates_data = self.load_json(os.path.join(dir_path, 'data', 'plates.json'))["plates"]
        self.pokemon_data = self.load_json(os.path.join(dir_path, 'data', 'pokemon.json'))

    def _initialize_managers(self):
        self.party_manager = PartyManager(self.bot, self.db_path)
        self.board_manager = BoardManager(self.party_manager)
        self.game_manager = GameManager(self.bot, self.db_path, self.party_manager)
        self.gacha = ShopView(self.db_path, self.pokemon_data, self.plates_data)

    def _register_default_user_config(self):
        default_user = {'key1': 'default_value1', 'key2': 'default_value2'}
        self.config = Config.get_conf(self, identifier=10112123, force_registration=True)
        self.config.register_user(**default_user)

    @commands.group(name="pduel")
    async def pduel(self, ctx):
        """Commands for PokeDuel."""
        pass

    @pduel.command(name="start")
    async def pokeduel_start(self, ctx):
        user_id = ctx.author.id
        if self.is_new_player(user_id):
            self.initialize_new_player(user_id)

            embed = Embed(title="Welcome to PokeDuel!",
                          description="You've received 5000 crystals to start your journey. Let's visit the shop to gear up!",
                          color=0x00ff00)

            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_name = 'welcome.png'
            file_path = os.path.join(dir_path, file_name)

            view = View()
            shop_button = Button(style=ButtonStyle.primary, label="Visit Shop", custom_id="visit_shop")
            shop_button.callback = self.open_shop
            view.add_item(shop_button)

            if os.path.exists(file_path):
                await ctx.send(file=discord.File(file_path, filename=file_name), embed=embed, view=view)
            else:
                await ctx.send("Welcome to PokeDuel!", embed=embed, view=view)
        else:
            await ctx.send("Resuming your existing game.")

    def initialize_new_player(self, user_id):
        self.db.initialize_new_user(user_id, 5000)
        # Add additional initialization logic here if needed

    async def open_shop(self, interaction: discord.Interaction):
        try:
            shop_view = ShopView(self.db_path, self.pokemon_data, self.plates_data)
            embed = Embed(title="PokeDuel Shop", description="Explore the shop and gear up for your adventures!",
                          color=0x00ff00)

            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_name = 'shop.png'
            file_path = os.path.join(dir_path, 'data', file_name)

            if os.path.exists(file_path):
                await interaction.followup.send(file=discord.File(file_path, filename=file_name), embed=embed,
                                                view=shop_view)
            else:
                await interaction.followup.send(content="Welcome to the PokeDuel Shop!", embed=embed, view=shop_view)

        except Exception as e:
            print(f"Error in open_shop: {e}")

    @pduel.command(name="customize")
    @has_started_save()
    async def pokeduel_customize(self, ctx):
        user_id = ctx.author.id
        party = self.db.get_user_party(user_id)

        if party is None:
            await ctx.send("No party data found for your account. Set up your party first.", ephemeral=True)
        else:
            party_view = PartyButtonView(self.db, user_id)
            await ctx.send("Manage your party:", view=party_view)

    @pduel.command(name="shop")
    @has_started_save()
    async def pokeduel_shop(self, ctx):
        user_id = ctx.author.id
        if not self.db.has_started_save(user_id):
            await ctx.send("You need to start a game first using `pokeduel start`.")
            return

        try:
            shop_view = ShopView(self.db_path, self.pokemon_data, self.plates_data)
            embed = Embed(title="PokeDuel Shop", description="Explore the shop and gear up for your adventures!",
                          color=0x00ff00)

            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_name = 'shop.png'
            file_path = os.path.join(dir_path, 'data', file_name)

            if os.path.exists(file_path):
                await ctx.send(file=discord.File(file_path, filename=file_name), embed=embed, view=shop_view)
            else:
                await ctx.send("Welcome to the PokeDuel Shop!", embed=embed, view=shop_view)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @pduel.command(name="duel")
    @has_started_save()
    async def pokeduel_duel(self, ctx, opponent: Member):
        if self.is_duel_ineligible(ctx, opponent):
            return

        self.prepare_for_duel(ctx.author, opponent)
        await ctx.send(f"Duel between {ctx.author.mention} and {opponent.mention} has started!")

    async def is_duel_ineligible(self, ctx, opponent):
        player = ctx.author
        queue_status = self.matchmaking_queue.get(player.id) or self.matchmaking_queue.get(opponent.id)
        duel_status = self.ongoing_duels.get(player.id) or self.ongoing_duels.get(opponent.id)
        if queue_status:
            await ctx.send("One of the players is currently in matchmaking.")
            return True
        if duel_status:
            await ctx.send("One of the players is currently in a duel.")
            return True
        return False

    async def handle_new_game(self, ctx):
        user_id = ctx.author.id
        if self.is_new_player(user_id):
            self.initialize_new_player(user_id)
            await ctx.send(f"New game started with 5000 crystals!")
        else:
            await ctx.send("Resuming your existing game.")

    def is_new_player(self, user_id):
        return not self.db.has_started_save(user_id)

    def prepare_for_duel(self, player1, player2):
        self.setup_game(player1)
        self.setup_game(player2)
        self.game_manager.start_duel(player1, player2)

    async def start_duel(self, player1, player2):
        message = "Your duel is starting now!"
        await self.bot.send_ephemeral_message(player1, message)
        await self.bot.send_ephemeral_message(player2, message)

        current_player, other_player = player1, player2
        while not self.is_duel_finished():
            board = self.board_manager.get_board_for_player(current_player)
            await self.bot.send_message(current_player, f"Your turn! Here's the board:\n{board}")

            current_player, other_player = other_player, current_player

    async def send_duel_start_notifications(self, player1, player2):
        message = "Your duel is about to start in 15 seconds. Get ready!"
        await self.bot.send_ephemeral_message(player1, message)
        await self.bot.send_ephemeral_message(player2, message)

    def is_player_available_for_duel(self, player):
        return self.db.is_player_available(player.id)

    async def enter_matchmaking(self, player):
        self.matchmaking_queue[player.id] = datetime.now()
        await asyncio.sleep(30)  # Wait for 30 seconds
        await self.find_match(player)

    async def find_match(self, player):
        for opponent_id, time_joined in self.matchmaking_queue.items():
            if opponent_id != player.id and datetime.now() - time_joined < timedelta(minutes=5):
                self.prepare_for_duel(player, self.bot.get_user(opponent_id))
                self.leave_matchmaking(player)
                self.leave_matchmaking(self.bot.get_user(opponent_id))
                return True
        return False

    def leave_matchmaking(self, player):
        self.matchmaking_queue.pop(player.id, None)

    def setup_game(self, player):
        initial_resources = 1000
        self.db.initialize_player_game_state(player.id, initial_resources)

    def get_game_status(self, user):
        if user.id in self.bot.matchmaking_queue:
            return "In matchmaking queue"
        elif user.id in self.bot.ongoing_duels:
            return "Currently in a duel"
        else:
            return "Idle"

    @pduel.command(name="help")
    async def pokeduel_help(self, ctx):
        prefix = (await ctx.bot.get_prefix(ctx.message))[0]
        help_message = (f"Welcome to PokeDuel! Here are some commands you can use:\n"
                        f"- `{prefix}pduel start`: Start your journey in PokeDuel\n"
                        f"- `{prefix}pduel shop`: Visit the shop\n"
                        f"- `{prefix}pduel customize`: Customize your party\n"
                        f"- `{prefix}pduel duel <user>`: Challenge another player to a duel")
        await ctx.send(help_message)

    def is_duel_finished(self):
        if self.win_condition_met():
            return True
        elif self.draw_condition_met():
            return True
        return False

    @staticmethod
    def win_condition_met():
        return False  # Replace with actual condition

    @staticmethod
    def draw_condition_met():
        return False  # Replace with actual condition


class StartGameView(View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

        self.add_item(Button(label='New Game', style=ButtonStyle.green, custom_id='new_game'))
        self.add_item(Button(label='Resume Game', style=ButtonStyle.green, custom_id='resume_game'))

    async def interaction_check(self, interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await self.ctx.send("Game selection timed out.")

    async def on_error(self, interaction, error, item):
        await interaction.followup.send()(f"An error occurred. Please try again or ping the dev", ephemeral=True)


class PokeDuelButtons(ui.View):
    def __init__(self, bot, pokeduel_cog):
        super().__init__()
        self.bot = bot
        self.pokeduel_cog = pokeduel_cog

        self.add_item(ui.Button(label='Game Status', style=ButtonStyle.grey, custom_id='game_status'))
        self.add_item(ui.Button(label='Help', style=ButtonStyle.grey, custom_id='help'))
        self.add_item(ui.Button(label='Enter Matchmaking', style=ButtonStyle.primary, custom_id='matchmaking'))

    @ui.button(label='Game Status', style=ButtonStyle.grey)
    async def game_status(self, interaction: Interaction, button: ui.Button):
        status = self.pokeduel_cog.get_game_status(interaction.user)
        await interaction.message.edit(f"Your Game Status: {status}", ephemeral=True)

        button.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label='Help', style=ButtonStyle.grey)
    async def help(self, interaction: Interaction, button: ui.Button):
        help_message = self.pokeduel_cog.get_help_message()
        await interaction.message.edit(help_message, ephemeral=True)

        button.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label='Enter Matchmaking', style=ButtonStyle.primary)
    async def matchmaking(self, interaction: Interaction, button: ui.Button):
        self.pokeduel_cog.enter_matchmaking(interaction.user)
        await interaction.message.edit("You have been entered into matchmaking.", ephemeral=True)

        button.disabled = True
        await interaction.message.edit(view=self)
