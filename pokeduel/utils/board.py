from collections import deque
from discord import ButtonStyle, Button
from discord.ui import Select, View, Button
from PIL import Image, ImageDraw

class BoardManager:
    def __init__(self, party_manager):
        self.party_manager = party_manager
        self.board = self.initialize_board()
        self.action_history = deque([], maxlen=5)

    @staticmethod
    def initialize_board():
        board = [["E" for _ in range(7)] for _ in range(8)]
        for i in [0, 7]:
            for j in [0, 6]:
                board[i][j] = "S"
            board[i][3] = "G"
        return board

    def create_button_for_cell(self, x, y):
        cell_value = self.board[x][y]
        label = self.get_label_for_cell(cell_value)
        return Button(style=ButtonStyle.secondary, label=label, custom_id=f"{x},{y}")

    def get_label_for_cell(self, cell_value):
        labels = {
            "E": "Empty",
            "S": "Spawn",
            "G": "Goal"
        }
        return labels.get(cell_value, "Unknown")

    def refresh_buttons(self, view: View):
        for x in range(8):
            for y in range(7):
                button = self.create_button_for_cell(x, y)
                view.add_item(button)



class BoardVisualizer:
    def __init__(self, board_manager):
        self.board_manager = board_manager
        self.cell_size = 100
        self.colors = {
            'G': 'purple',
            'S': 'blue',
            'E': 'green',
            'P': 'black',
            'B': 'grey',
            'PC': 'pink',
            'Y': 'yellow'
        }
        self.board_width = 8
        self.board_height = 7
        self.image_width = self.cell_size * self.board_width
        self.image_height = self.cell_size * self.board_height
        self.img = Image.new('RGB', (self.image_width, self.image_height), 'white')
        self.draw = ImageDraw.Draw(self.img)

    def draw_cell(self, x, y, cell_type):
        top_left_corner = (x * self.cell_size, y * self.cell_size)
        bottom_right_corner = ((x + 1) * self.cell_size, (y + 1) * self.cell_size)
        self.draw.rectangle([top_left_corner, bottom_right_corner], fill=self.colors[cell_type], outline="black")

    def draw_nodes_and_lines(self):
        # Nodes are only on SEG tiles
        nodes = [(x, y) for y in range(self.board_height) for x in range(self.board_width)
                 if self.board_manager.board[y][x] in ['E', 'S', 'G']]
        for x, y in nodes:
            center = (x * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2)
            self.draw.ellipse((center[0] - 5, center[1] - 5, center[0] + 5, center[1] + 5), fill='black')

        for x, y in nodes:
            if (x + 1, y) in nodes:
                self.draw.line([(x * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2),
                               ((x + 1) * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2)], fill='black')
            if (x, y + 1) in nodes:
                self.draw.line([(x * self.cell_size + self.cell_size // 2, y * self.cell_size + self.cell_size // 2),
                               (x * self.cell_size + self.cell_size // 2, (y + 1) * self.cell_size + self.cell_size // 2)], fill='black')

        diagonal_connections = [((2, 1), (3, 2)), ((3, 4), (4, 5))]
        for start, end in diagonal_connections:
            start_center = (start[0] * self.cell_size + self.cell_size // 2, start[1] * self.cell_size + self.cell_size // 2)
            end_center = (end[0] * self.cell_size + self.cell_size // 2, end[1] * self.cell_size + self.cell_size // 2)
            self.draw.line([start_center, end_center], fill='black', width=2)

    def draw_spawn_rectangle(self):
        spawn_points = [(x, y) for y in range(self.board_height) for x in range(self.board_width)
                        if self.board_manager.board[y][x] == 'S']
        if spawn_points:
            min_x = min(sp[0] for sp in spawn_points) * self.cell_size
            min_y = min(sp[1] for sp in spawn_points) * self.cell_size
            max_x = (max(sp[0] for sp in spawn_points) + 1) * self.cell_size
            max_y = (max(sp[1] for sp in spawn_points) + 1) * self.cell_size
            self.draw.rectangle([min_x, min_y, max_x, max_y], outline="blue", width=2)

    def render_board(self):
        for y in range(self.board_height):
            for x in range(self.board_width):
                cell_value = self.board_manager.board[y][x] if y < len(self.board_manager.board) else 'B'
                cell_value = 'PC' if (y == 0 or y == self.board_height - 1) and x >= self.board_width - 2 else cell_value
                self.draw_cell(x, y, cell_value)
        self.draw_nodes_and_lines()
        self.draw_spawn_rectangle()
        return self.img

    def save_image(self, path):
        self.img.save(path)

    @staticmethod
    def initialize_board():
        # Initialize the game board with 8x7 dimensions
        board = [["E" for _ in range(8)] for _ in range(7)]

        # Set spawn (S) points
        board[1][0] = "S"
        board[1][6] = "S"
        board[5][0] = "S"
        board[5][6] = "S"

        # Set goal (G) points
        board[1][3] = "G"
        board[5][3] = "G"

        # Set bench (Y) rows on top and bottom and player character (PC) on the rightmost columns
        for i in range(8):
            board[0][i] = "Y"  # Top bench row
            board[6][i] = "Y"  # Bottom bench row
            if i in [6, 7]:  # Rightmost columns for knocked out pieces
                for j in range(1, 6):
                    board[j][i] = "PC"

        return board

    def move_piece(self, player_id, from_coords, to_coords):
        piece = self.board[from_coords[0]][from_coords[1]]
        if piece != player_id:  # TODO: sprites integration
            return False
        party = self.party_manager.get_party(player_id)

        piece = self.board[from_coords[0]][from_coords[1]]
        self.action_history.append(f"Moved from {from_coords} to {to_coords}")

        movement_points = next((pokemon['movement'] for pokemon in party if pokemon['name'] == piece), 1)

        dx = abs(to_coords[0] - from_coords[0])
        dy = abs(to_coords[1] - from_coords[1])
        distance = max(dx, dy)

        if piece['owner'] != player_id:
            raise ValueError("The selected piece does not belong to you.")
        if distance > movement_points:
            raise ValueError("Insufficient movement points.")
        if self.board[to_coords[0]][to_coords[1]] != 'E':
            raise ValueError("Target cell is not empty.")
        if self.is_path_blocked(from_coords, to_coords):
            raise ValueError("Path is blocked.")

        if distance > movement_points:
            return False

        if self.board[to_coords[0]][to_coords[1]] != 'E':
            return False

        if self.is_path_blocked(from_coords, to_coords):
            return False

        self.board[to_coords[0]][to_coords[1]] = piece
        self.board[from_coords[0]][from_coords[1]] = "E"
        return True

    def move_piece_diagonally(self, from_coords, to_coords):
        x1, y1 = from_coords
        x2, y2 = to_coords
        step_x = 1 if x2 > x1 else -1
        step_y = 1 if y2 > y1 else -1

        for step in range(1, abs(x2 - x1) + 1):
            new_coords = (x1 + step * step_x, y1 + step * step_y)
            if self.board[new_coords[0]][new_coords[1]] != 'E':
                return False

        piece = self.board[from_coords[0]][from_coords[1]]
        self.board[to_coords[0]][to_coords[1]] = piece
        self.board[from_coords[0]][from_coords[1]] = 'E'
        return True

    def is_path_blocked(self, from_coords, to_coords):
        x1, y1 = from_coords
        x2, y2 = to_coords
        dx, dy = abs(x2 - x1), abs(y2 - y1)

        if dx == dy:  # diagonal movement
            for step in range(1, dx):
                x, y = x1 + step if x1 < x2 else x1 - step, y1 + step if y1 < y2 else y1 - step
                if self.board[x][y] != 'E':
                    return True
        elif x1 == x2:
            for y in range(min(y1, y2) + 1, max(y1, y2)):
                if self.board[x1][y] != 'E':
                    return True
        elif y1 == y2:
            for x in range(min(x1, x2) + 1, max(x1, x2)):
                if self.board[x][y1] != 'E':
                    return True

        return False

    def update_board(self, x, y, value):
        # Update the board at a specific coordinate
        self.board[x][y] = value
