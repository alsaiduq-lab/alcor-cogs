import random
from typing import List, Any, Dict

class Pokemon:
    def __init__(self, data: dict):
        """
        Initialize a new Pokemon object.

        Parameters:
            data (dict): The data dictionary containing Pokemon attributes.
        """
        self.data = data



    @property
    def name(self) -> str:
        """Return the name of the Pokemon."""
        return self.data.get('Name', 'Unknown')

    @property
    def movement(self) -> int:
        """Return the movement points of the Pokemon."""
        return self.data.get('Movement', 0)

    @property
    def type(self) -> List[str]:
        """Return the type(s) of the Pokemon."""
        return self.data.get('Type', [])

    @property
    def rarity(self) -> str:
        """Return the rarity of the Pokemon."""
        return self.data.get('Rarity', 'Unknown')

    @property
    def base_wheel_size(self) -> List[Any]:
        """Return the base wheel size(s) of the Pokemon."""
        return self.data.get('Base Wheel Size', [])

    @property
    def special_ability(self) -> str:
        """Return the special ability of the Pokemon."""
        return self.data.get('Special Ability', 'None')

class Ability:
    def __init__(self, description: str):
        self.description = description

    def execute(self, pokemon, opponent):
        raise NotImplementedError("This method should be overridden by subclass")

