import sqlite3
import json
import logging
from discord.ext import commands
from discord import ButtonStyle, SelectOption
from discord.ui import Select, View, Button


class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        logging.debug(f"Database connected at {db_path}")
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
        inventory_json = json.dumps([]) if inventory is None else json.dumps(inventory)
        party_json = json.dumps([]) if party is None else json.dumps(party)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (id, crystals, dust, inventory, party) VALUES (?, ?, ?, ?, ?)",
                (user_id, crystals, dust, inventory_json, party_json))

    def get_crystals(self, user_id):
        try:
            with self.conn:
                cur = self.conn.execute("SELECT crystals FROM users WHERE id = ?", (user_id,))
                crystals = cur.fetchone()[0]
                logging.debug(f"Crystals for user {user_id}: {crystals}")
                return crystals
        except Exception as e:
            logging.error(f"Error getting crystals for user {user_id}: {e}")
            return None

    def update_crystals(self, user_id, new_crystal_count):
        with self.conn:
            self.conn.execute("UPDATE users SET crystals = ? WHERE id = ?", (new_crystal_count, user_id))

    def get_dust(self, user_id):
        try:
            with self.conn:
                cur = self.conn.execute("SELECT dust FROM users WHERE id = ?", (user_id,))
                dust = cur.fetchone()[0]
                logging.debug(f"Dust for user {user_id}: {dust}")
                return dust
        except Exception as e:
            logging.error(f"Error getting dust for user {user_id}: {e}")
            return None

    def update_dust(self, user_id, new_dust_amount):
        with self.conn:
            self.conn.execute("UPDATE users SET dust = ? WHERE id = ?", (new_dust_amount, user_id))

    def get_inventory(self, user_id):
        logging.debug(f"Attempting to fetch inventory for user ID: {user_id}")
        try:
            with self.conn:
                cur = self.conn.execute("SELECT inventory FROM users WHERE id = ?", (user_id,))
                inventory_str = cur.fetchone()[0]
                logging.debug(f"Inventory string fetched from database for user {user_id}: {inventory_str}")
                inventory = json.loads(inventory_str)
                logging.debug(f"Inventory for user {user_id} after JSON parsing: {inventory}")
                return inventory
        except Exception as e:
            logging.error(f"Error getting inventory for user {user_id}: {e}", exc_info=True)
            return []

    def update_inventory(self, user_id, new_inventory):
        with self.conn:
            inventory_str = json.dumps(new_inventory)
            self.conn.execute("UPDATE users SET inventory = ? WHERE id = ?", (inventory_str, user_id))
            self.conn.commit()

    def get_user_party(self, user_id):
        try:
            with self.conn:
                cur = self.conn.execute("SELECT party FROM users WHERE id = ?", (user_id,))
                party_str = cur.fetchone()[0]
                logging.debug(f"Party for user {user_id}: {party_str}")
                return json.loads(party_str)
        except Exception as e:
            logging.error(f"Error getting party for user {user_id}: {e}")
            return []

    def update_user_party(self, user_id, new_party):
        with self.conn:
            party_str = json.dumps(new_party)
            self.conn.execute("UPDATE users SET party = ? WHERE id = ?", (party_str, user_id))

    def add_to_inventory(self, user_id, item, rarity):
        try:
            inventory = self.get_inventory(user_id)
            logging.debug(f"Current inventory for user {user_id}: {inventory}")

            new_item = {'item': item, 'rarity': rarity}
            inventory.append(new_item)
            self.update_inventory(user_id, inventory)

            logging.info(f"Added {item} of rarity {rarity} to user {user_id}'s inventory.")
            logging.debug(f"Updated inventory for user {user_id}: {inventory}")
        except Exception as e:
            logging.error(f"Error adding item to inventory for user {user_id}: {e}")

    def add_plate_to_inventory(self, user_id, plate):
        inventory = self.get_inventory(user_id)
        inventory.append(plate)
        self.update_inventory(user_id, inventory)

    def has_started_save(self, user_id):
        with self.conn:
            cur = self.conn.execute("SELECT crystals, inventory, party FROM users WHERE id = ?", (user_id,))
            result = cur.fetchone()

            if result is None:
                return False

            crystals, inventory, party = result
            inventory = json.loads(inventory)
            party = json.loads(party)

            if crystals == 5000 and len(inventory) == 0 and len(party) == 0:
                return False

            return True

    def is_player_available(self, user_id):
        pass

    def initialize_player_game_state(self, user_id, initial_resources):
        pass
