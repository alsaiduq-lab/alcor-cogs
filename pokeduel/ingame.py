from datetime import datetime
import random
from .utils.board import BoardManager
from .logic.combat import CombatManager
from discord import ButtonStyle
from discord.ui import Button, View
from .data import sprites
from .party import PartyButtonView, DatabaseManager


class GameButtons(View):
    def __init__(self):
        super().__init__()
        self.add_item(Button(style=ButtonStyle.primary, label="Move", custom_id="move"))
        self.add_item(Button(style=ButtonStyle.primary, label="Battle", custom_id="battle"))
        self.add_item(Button(style=ButtonStyle.primary, label="End Turn", custom_id="end_turn"))


def get_selected_piece_position(board, piece_id):
    for y, row in enumerate(board):
        for x, cell in enumerate(row):
            if cell == piece_id:
                return x, y
    return None, None


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

    @staticmethod
    def find_piece_position(board, piece_id):
        for y, row in enumerate(board):
            for x, cell in enumerate(row):
                if cell == piece_id:  # Replace with your piece identification logic
                    return x, y
        return None, None

    async def handle_move(self, ctx, game_id, current_player_id, interaction):
        game = self.ongoing_games[game_id]
        board = game[f'player{current_player_id}']['board']
        piece_id = self.get_current_player_piece_id(current_player_id)

        current_x, current_y = self.find_piece_position(board, piece_id)
        if current_x is None:
            await ctx.send("Piece not found on the board.", ephemeral=True)
            return

        selected_direction = interaction.custom_id.split(',')
        if len(selected_direction) != 2:
            await ctx.send("Invalid move!", ephemeral=True)
            return

        new_x, new_y = map(int, selected_direction)

        if not self.is_valid_move():
            await ctx.send("Invalid move!", ephemeral=True)
            return

        board[current_y][current_x] = None
        board[new_y][new_x] = piece_id

        game[f'player{current_player_id}']['board'] = board

        await ctx.send(f"Moved piece to {new_x, new_y}", ephemeral=True)

    def get_current_player_piece_id(self, current_player_id):
        try:
            game_state = self.db.get_game_state(current_player_id)
            return game_state.get('active_piece_id', None)
        except Exception as e:
            print(f"Error getting game state: {e}")
            return None

    def is_valid_move(self):
        valid_moves = []
        x, y = self.current_piece_coords

        # Example: Add adjacent cells for a movement range of 1
        if self.movement_range == 1:
            adjacent_cells = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            for new_x, new_y in adjacent_cells:
                if self.board_manager.is_valid_cell(new_x, new_y):
                    direction = f"{new_x},{new_y}"
                    label = f"Move to ({new_x}, {new_y})"
                    valid_moves.append((direction, label))
        # TODO: Add logic for other movement ranges

        return valid_moves

    @staticmethod
    def get_target_piece_position(interaction):
        # Assuming the target is determined by the interaction (e.g., a button click)
        target_position = interaction.data  # Replace with how the target is identified
        return target_position

    def get_movement_range(self, piece):
        return self.pokemon_data.get(piece, {}).get('Movement', 1)


class GameManager:
    def __init__(self, bot, db_path, party_manager):
        self.bot = bot
        self.db = DatabaseManager(db_path)
        self.board_manager = BoardManager(party_manager)
        self.combat_manager = CombatManager()
        self.ongoing_games = {}

    async def start_duel(self, ctx, player1, player2):
        # Create a unique game identifier for the duel
        game_id = self.create_game_id(player1, player2)

        # Set up the initial game state
        self.setup_game(game_id, player1.id, player2.id)

        # Start the main game loop
        await self.game_loop(ctx, game_id)

    @staticmethod
    def create_game_id(player1, player2):
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
            await ctx.send(
                f"{ctx.guild.get_member(opponent_id).mention}, it's {ctx.guild.get_member(current_player_id).mention}'s turn!")

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

    @staticmethod
    async def handle_battle(self, ctx, game_id, current_player_id, interaction):
        # Retrieve the game data
        game = self.ongoing_games.get(game_id)
        if not game:
            await ctx.send("Error: Game data not found.", ephemeral=True)
            return

        # Identify the opponent
        opponent_id = self.get_opponent_id(game_id, current_player_id)
        current_player_board = game[f'player{current_player_id}']['board']
        opponent_board = game[f'player{opponent_id}']['board']

        # Determine the battling pieces (this logic depends on your game's design)
        # Example:
        attacking_piece_position = self.get_selected_piece_position(current_player_board)
        defending_piece_position = self.get_target_piece_position(opponent_board, interaction)

        # Resolve the battle using the combat manager
        battle_result = self.combat_manager.resolve_combat(attacking_piece_position, defending_piece_position)

        # Update the boards based on the battle result
        # This might involve removing pieces, changing positions, etc.
        self.update_boards_after_battle(current_player_board, opponent_board, battle_result)

        # Update the game state
        game[f'player{current_player_id}']['board'] = current_player_board
        game[f'player{opponent_id}']['board'] = opponent_board

        # Send the battle result message
        message = self.format_battle_message(battle_result)
        await ctx.send(message, ephemeral=True)

        # Check for any post-battle effects or conditions
        self.check_post_battle_conditions(game_id, current_player_id, opponent_id)

    # Add the following methods to GameManager

    def handle_end_of_turn(self, game_id):
        self.handle_special_features(game_id)
        self.switch_turn(game_id)

    # Implement end turn logic

    # End turn logic

    def switch_turn(self, game_id):
        current_game = self.ongoing_games[game_id]
        current_player_id = current_game['turn']
        current_game['turn'] = current_game['player2']['id'] if current_game['player1']['id'] == current_player_id else \
            current_game['player1']['id']
        current_game['turn_counter'] += 1

    def handle_special_features(self, game_id):
        # Implement game-specific features like evolutions, Z-Moves, etc.
        # Example:
        # Check and apply any special features
        # This might involve modifying the game state, applying effects, etc.
        pass

    def check_win_condition(self, game_id, current_player_id):
        try:
            game = self.ongoing_games[game_id]
            opponent_id = self.get_opponent_id(game_id, current_player_id)
            if self.has_reached_goal(game[f'player{opponent_id}']['board']):
                return True
            return False
        except KeyError:
            print(f"Game ID {game_id} not found in ongoing games.")
            return False

    async def end_game(self, ctx, game_id, winning_player_id):
        await ctx.send(f"Game over! {ctx.guild.get_member(winning_player_id).mention} won the game!")
        del self.ongoing_games[game_id]

    async def end_of_turn_phase(self, ctx, game_id, player1, player2):
        game = self.ongoing_games.get(game_id)
        if game is None:
            return

        game['turn_counter'] += 1
        if game['turn_counter'] >= 300:
            winning_player_id = None
            await ctx.send("Game over! Turn limit reached.")
            await self.end_game(ctx, game_id, winning_player_id)
            return

        current_player_id = game['turn']
        if await self.check_win_condition(game['board'], discord.Member(id=current_player_id)):
            await ctx.send(f"{discord.Member(id=current_player_id).mention} won the game!")
            await self.end_game(ctx, game_id, current_player_id)
            return

        # TODO: any other end-of-turn effects or checks here

        game['turn'] = player2.id if game['turn'] == player1.id else player1.id
        await ctx.send(f"It's now {discord.Member(id=game['turn']).mention}'s turn!")

    @staticmethod
    def update_boards_after_battle(player_board, opponent_board, battle_result):

        try:
            attacking_x, attacking_y = get_selected_piece_position(player_board, attacking_piece_id)
            defending_x, defending_y = get_target_piece_position(opponent_board, defending_piece_id)
            if battle_result == 'win':
                opponent_board[defending_y][defending_x] = None  # Move it to PC
            elif battle_result == 'loss':
                player_board[attacking_y][attacking_x] = None  # Move it to PC
        except Exception as e:
            print(f"Error updating boards after battle: {e}")

    @staticmethod
    def format_battle_message(battle_result):
        if battle_result == 'win':
            return "You won the battle!"
        elif battle_result == 'loss':
            return "You lost the battle!"
        else:
            return "The battle ended in a draw!"

    def check_post_battle_conditions(self, game_id, current_player_id):
        if self.check_win_condition(game_id, current_player_id):
            self.end_game(ctx, game_id, current_player_id)

    def create_board_visual(self, board):
        try:
            return self.board_manager.render_board(board)
        except Exception as e:
            print(f"Error rendering board: {e}")
            return "Board rendering error."
