import re
import uuid
import discord
from discord import ButtonStyle, SelectOption, Interaction, Embed
from discord.ui import Select, View, Button
from .data import sprites


class InventoryView(View):
    def __init__(self, user_id, db, page=0):
        super().__init__()
        logging.debug(f"Initializing InventoryView: user_id={user_id}, page={page}")
        self.content = None
        self.user_id = user_id
        self.db = db
        self.page = page
        self.max_items_per_page = 8
        self.previous_button_id = f"previous_{user_id}"
        self.next_button_id = f"next_{user_id}"
        self.update_view()

    def update_view(self):
        logging.debug(f"Updating view: page={self.page}")
        self.clear_items()
        try:
            inventory = self.db.get_inventory(self.user_id)

            aggregated_inventory = {}
            for item in inventory:
                key = (item['item'], item['rarity'])
                if key in aggregated_inventory:
                    aggregated_inventory[key]['count'] += 1
                else:
                    aggregated_inventory[key] = {'count': 1, 'item': item['item'], 'rarity': item['rarity']}

            sorted_aggregated_inventory = sorted(aggregated_inventory.values(),
                                                 key=lambda x: (-self.rarity_to_int(x['rarity']), x['item']))
            total_items = len(sorted_aggregated_inventory)
            total_pages = (total_items + self.max_items_per_page - 1) // self.max_items_per_page

            start = self.page * self.max_items_per_page
            end = start + self.max_items_per_page
            page_items = sorted_aggregated_inventory[start:end]
            self.content = '\n'.join([f"{item['item']} ({item['rarity']}) ({item['count']})" for item in page_items])

            if self.page > 0:
                previous_button = Button(label='Previous', style=ButtonStyle.grey, custom_id=self.previous_button_id)
                previous_button.callback = self.previous_button_callback
                self.add_item(previous_button)

            if self.page < total_pages - 1:
                next_button = Button(label='Next', style=ButtonStyle.grey, custom_id=self.next_button_id)
                next_button.callback = self.next_button_callback
                self.add_item(next_button)

            logging.debug(f"Updated content: {self.content}")
        except Exception as ex:
            logging.error(f"Error in update_view: {ex}", exc_info=True)

    @staticmethod
    def rarity_to_int(rarity):
        rarity_order = {"UX": 5, "EX": 4, "R": 3, "UC": 2, "C": 1}
        return rarity_order.get(rarity, 0)

    async def previous_button_callback(self, interaction):
        logging.debug("Previous button pressed")
        if self.page > 0:
            self.page -= 1
            self.update_view()
            await interaction.response.edit_message(content=self.content, view=self)
        logging.debug(f"Previous button processing complete: new page={self.page}")

    async def next_button_callback(self, interaction):
        logging.debug("Next button pressed")
        self.page += 1
        self.update_view()
        await interaction.response.edit_message(content=self.content, view=self)
        logging.debug(f"Next button processing complete: new page={self.page}")
