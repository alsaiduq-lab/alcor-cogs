import json
import random
from datetime import datetime, timedelta
from redbot.core import commands, Config
from discord import Member, ButtonStyle, SelectOption
from discord.ext import commands
from discord.ui import Select


from pokeduel.gatcha import ShopView
from pokeduel.party import PartyManager
from pokeduel.ingame import GameManager
from pokeduel.utils.board import BoardManager
from pokeduel.data.database import DatabaseManager

# predicate saves
def has_started_save():
    async def predicate(ctx):
        return ctx.cog.db.has_started_save(ctx.author.id)
    return commands.check(predicate)

class PokeDuel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager('./pokeduel_db.sqlite')
        self.party_manager = PartyManager()
        self.board_manager = BoardManager(self.party_manager)
        self.game_manager = GameManager(self.bot, self.db, self.board_manager)
        self.config = Config.get_conf(self, identifier=10112123, force_registration=True)
        self.config.register_user(**default_user)
        self.gacha = PokeGacha()
        self.plates_data = self.load_json('./plates.json')
        self.pokemon_data = self.load_json('./pokemon.json')

    @commands.command()
    async def start(self, ctx):
        await ctx.send("Welcome to PokeDuel! Type `!newgame` to begin your journey!")

    @commands.command(aliases=['begin', 'start'])
    async def newgame(self, ctx):
        await self.handle_new_game(ctx)

    @commands.command()
    @has_started_save()
    async def shop(self, ctx):
        user_id = ctx.author.id
        shop_view = ShopView(user_id, self.db, self.pokemon_data, self.plates_data)
        await ctx.send("Welcome to the Shop!", view=shop_view)

    @commands.command()
    @has_started_save()
    async def customize_party(self, ctx):
        user_id = ctx.author.id
        party_button_view = PartyButtonView(self.db, user_id)
        await party_button_view.refresh(ctx)

    @commands.command()
    @has_started_save()
    async def duel(self, ctx, opponent: Member):
        if ctx.author.id in self.matchmaking_queue or opponent.id in self.matchmaking_queue:
            await ctx.send("One of the players is currently in matchmaking.")
            return

        if ctx.author.id in self.ongoing_duels or opponent.id in self.ongoing_duels:
            await ctx.send("One of the players is currently in a duel.")
            return

        self.prepare_for_duel(ctx.author, opponent)
        await ctx.send(f"Duel between {ctx.author.mention} and {opponent.mention} has started!")

    # Helper methods
    def load_json(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)

    async def handle_new_game(self, ctx):
        user_id = ctx.author.id
        if self.is_new_player(user_id):
            self.initialize_new_player(user_id)
            await ctx.send(f"New game started with 5000 crystals!")
        else:
            await ctx.send("Resuming your existing game.")

    def is_new_player(self, user_id):
        return not self.db.has_started_save(user_id)

    def initialize_new_player(self, user_id):
        self.db.initialize_new_user(user_id, 5000)

    def prepare_for_duel(self, player1, player2):
        self.setup_game(player1)
        self.setup_game(player2)
        self.game_manager.start_game(player1, player2)

    def setup_game(self, player):
        self.board_manager.setup_board()
        self.party_manager.select_party(player)

    def is_player_available_for_duel(self, player):
        return self.db.is_player_available(player.id)

    async def enter_matchmaking(self, player):
        self.matchmaking_queue[player.id] = datetime.now()
        await asyncio.sleep(30)  # Wait for 30 seconds
        if player.id in self.matchmaking_queue:
            await self.find_match(player)

    async def find_match(self, player):
        for opponent_id, time_joined in self.matchmaking_queue.items():
            if opponent_id != player.id and datetime.now() - time_joined < timedelta(seconds=30):
                self.prepare_for_duel(player, self.bot.get_user(opponent_id))
                self.leave_matchmaking(player)
                self.leave_matchmaking(self.bot.get_user(opponent_id))
                break

    def leave_matchmaking(self, player):
        self.matchmaking_queue.pop(player.id, None)

class StartGameView(View):
    def __init__(self, ctx, cog):
        super().__init__()
        self.ctx = ctx
        self.cog = cog

        self.add_item(Button(label='New Game', style=ButtonStyle.green, custom_id='new_game'))
        self.add_item(Button(label='Resume Game', style=ButtonStyle.green, custom_id='resume_game'))

    async def interaction_check(self, interaction) -> bool:
        return interaction.user == self.ctx.author

    async def on_timeout(self):
        await self.ctx.send("Game selection timed out.")

    async def on_error(self, interaction, error, item):
        await self.ctx.send(f"An error occurred: {str(error)}")

class GameStatusView(View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

        self.add_item(Button(label='Game Status', style=ButtonStyle.grey, custom_id='game_status'))
        self.add_item(Button(label='Help', style=ButtonStyle.grey, custom_id='help'))
        self.add_item(Button(label='Enter Matchmaking', style=ButtonStyle.blue, custom_id='matchmaking'))

    @discord.ui.button(label='Game Status', style=ButtonStyle.grey)
    async def game_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        game_status = self.cog.get_game_status(interaction.user)
        await interaction.response.send_message(f"Game Status: {game_status}" if game_status else "No active game found.")

    @discord.ui.button(label='Help', style=ButtonStyle.grey)
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        help_message = self.cog.get_help_message()
        await interaction.response.send_message(help_message)

    async def matchmaking(self, button, interaction):
        await self.cog.enter_matchmaking(interaction.user)
        await interaction.response.send_message("Searching for an opponent...")