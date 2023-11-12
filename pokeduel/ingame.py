from datetime import datetime
import random
from pokeduel.utils.board import BoardManager
from pokeduel.logic.combat import CombatManager
from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button

from pokeduel.party import PartyButtonView, DatabaseManager

class GameButtons(View):
    def __init__(self):
        super().__init__()
        self.add_item(Button(style=ButtonStyle.primary, label="Move", custom_id="move"))
        self.add_item(Button(style=ButtonStyle.primary, label="Battle", custom_id="battle"))
        self.add_item(Button(style=ButtonStyle.primary, label="End Turn", custom_id="end_turn"))


class MoveButtons(View):
    def __init__(self, board_manager, current_piece_coords, movement_range):
        super().__init__()
        self.board_manager = board_manager
        self.current_piece_coords = current_piece_coords
        self.movement_range = movement_range
        move_button = Button(style=ButtonStyle.primary, label="Move", custom_id="move")
        move_button.callback = self.handle_move
        self.add_item(move_button)

        for direction, label in self.valid_movements():
            self.add_item(Button(style=ButtonStyle.secondary, label=label, custom_id=direction))

    def valid_movements(self):
        valid_moves = []
        x, y = self.current_piece_coords

        # Example: Add adjacent cells for a movement range of 1
        if self.movement_range == 1:
            adjacent_cells = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
            for new_x, new_y in adjacent_cells:
                if self.board_manager.is_valid_cell(new_x, new_y):
                    direction = f"{new_x},{new_y}"
                    label = f"Move to ({new_x}, {new_y})"
                    valid_moves.append((direction, label))
        # TODO: Add logic for other movement ranges

        return valid_moves

    async def handle_move(self, interaction):
        # Logic to move a piece
        # You might need to update the game state, move a piece on the board, etc.
        # Example:
        selected_direction = interaction.custom_id
        # Perform the movement based on `selected_direction`
        await interaction.response.send_message(f"Moved piece to {selected_direction}", ephemeral=True)


class GameManager:
    def __init__(self, bot, db_path):
        self.bot = bot
        self.db = DatabaseManager(db_path)
        self.board_manager = BoardManager()
        self.combat_manager = CombatManager()
        self.ongoing_games = {}

    async def start_duel(self, ctx, player1, player2):
        game_id = self.create_game_id(player1, player2)
        self.setup_game(game_id, player1.id, player2.id)
        await self.game_loop(ctx, game_id)

    def create_game_id(self, player1, player2):
        timestamp_duel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"{player1.id} vs. {player2.id} {timestamp_duel}"

    def setup_game(self, game_id, player1_id, player2_id):
        starting_player = random.choice([player1_id, player2_id])
        player1_party = self.db.get_user_party(player1_id)
        player2_party = self.db.get_user_party(player2_id)
        self.ongoing_games[game_id] = {
            'turn': starting_player,
            'player1': {'board': self.board_manager.setup_initial_board(player1_party), 'party': player1_party},
            'player2': {'board': self.board_manager.setup_initial_board(player2_party), 'party': player2_party},
            'turn_counter': 0
        }

    async def game_loop(self, ctx, game_id):
        while True:
            game = self.ongoing_games[game_id]
            current_player_id = game['turn']
            opponent_id = self.get_opponent_id(game_id, current_player_id)

            await self.perform_turn_actions(ctx, game_id, current_player_id)

            if self.check_win_condition(game_id, current_player_id):
                await self.end_game(ctx, game_id, current_player_id)
                break

            self.switch_turn(game_id)

    def get_opponent_id(self, game_id, current_player_id):
        game = self.ongoing_games[game_id]
        return game['player2']['id'] if game['player1']['id'] == current_player_id else game['player1']['id']

    async def perform_turn_actions(self, ctx, game_id, current_player_id):
        await self.display_boards(ctx, game_id, current_player_id)
        game_buttons = GameButtons()
        await ctx.send("Choose an action:", view=game_buttons)

        interaction = await self.bot.wait_for('button_click', check=lambda i: i.user.id == current_player_id)
        if interaction.custom_id == 'move':
            await self.handle_move(ctx, game_id, current_player_id, interaction)
        elif interaction.custom_id == 'battle':
            await self.handle_battle(ctx, game_id, current_player_id, interaction)
        elif interaction.custom_id == 'end_turn':
            self.handle_end_of_turn(ctx, game_id, current_player_id)

    def handle_end_of_turn(self, ctx, game_id, current_player_id):
        self.handle_special_features(game_id, current_player_id)
        self.switch_turn(game_id)

    # Implement end turn logic

    # End turn logic

    def switch_turn(self, game_id):
        current_game = self.ongoing_games[game_id]
        current_player_id = current_game['turn']
        current_game['turn'] = current_game['player2']['id'] if current_game['player1']['id'] == current_player_id else current_game['player1']['id']
        current_game['turn_counter'] += 1



    def handle_special_features(self, game_id, current_player_id):
        # Implement game-specific features like evolutions, Z-Moves, etc.
        # Example:
        game = self.ongoing_games[game_id]
        # Check and apply any special features
        # This might involve modifying the game state, applying effects, etc.

    def check_win_condition(self, game_id, current_player_id):
        current_game = self.ongoing_games[game_id]
        opponent_id = self.get_opponent_id(game_id, current_player_id)
        if self.has_reached_goal(current_game[f'player{opponent_id}']['board']):
            return True
        return False

    async def end_game(self, ctx, game_id, winning_player_id):
        await ctx.send(f"Game over! {ctx.guild.get_member(winning_player_id).mention} won the game!")
        del self.ongoing_games[game_id]

    def get_movement_range(self, piece):
        return self.pokemon_data.get(piece, {}).get('Movement', 1)

    async def end_of_turn_phase(self, ctx, game_id, player1, player2):
        game = self.ongoing_games.get(game_id)
        if game is None:
            return

        game['turn_counter'] += 1

        # Check for turn limit (300 turns)
        if game['turn_counter'] >= 300:
            await ctx.send("Game over! Turn limit reached.")
            self.end_game(game_id)
            return

        # Check for win condition
        if await self.check_win_condition(game['board'], discord.Member(id=game['turn'])):
            await ctx.send(f"{discord.Member(id=game['turn']).mention} won the game!")
            self.end_game(game_id)
            return

        # TODO: Add any other end-of-turn effects or checks here

        game['turn'] = player2.id if game['turn'] == player1.id else player1.id
        await ctx.send(f"It's now {discord.Member(id=game['turn']).mention}'s turn!")

    async def check_win_condition(self, opponent_board, current_player):
        if opponent_board[4][3] in current_player.pokemons:
            return True
        return False

    def end_game(self, game_id):
        del self.ongoing_games[game_id]
