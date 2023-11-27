import logging
import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import time

import asyncakinator
from asyncakinator import Answer
import discord
from redbot.core import commands

log = logging.getLogger("red.alcor.aki.menus")

NSFW_WORDS = ("porn", "sex")


def channel_is_nsfw(channel) -> bool:
    return getattr(channel, "nsfw", False)


class AkiView(discord.ui.View):
    def __init__(self, game, color, author_id, sfw_mode):
        super().__init__(timeout=60)
        self.aki = game
        self.color = color
        self.author_id = author_id
        self.sfw_mode = sfw_mode
        self.num = 1

    @staticmethod
    def contains_nsfw_content(text: str) -> bool:
        """
        Check if the given text contains NSFW content based on specific words.

        Args:
            text (str): The text to check for NSFW content.

        Returns:
            bool: True if NSFW content is found, False otherwise.
        """
        nsfw_words = ["boobs", "breasts"]
        text_lower = text.lower()
        return any(nsfw_word in text_lower for nsfw_word in nsfw_words)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This isn't your Akinator game.", ephemeral=True
            )
            return False
        await interaction.response.defer()
        return True

    async def send_initial_message(self, channel: discord.TextChannel) -> discord.Message:
        return await channel.send(embed=self.current_question_embed(), view=self)

    async def start(self, interaction: discord.Interaction):
        ctx_channel = interaction.channel
        return await ctx_channel.send(embed=self.current_question_embed(), view=self)

    @discord.ui.button(label="yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("y", interaction)

    @discord.ui.button(label="no", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("no", interaction)

    @discord.ui.button(label="idk", style=discord.ButtonStyle.blurple)
    async def idk(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("idk", interaction)

    @discord.ui.button(label="probably", style=discord.ButtonStyle.blurple)
    async def probably(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("probably", interaction)

    @discord.ui.button(label="probably not", style=discord.ButtonStyle.blurple)
    async def probably_not(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.answer_question("probably not", interaction)

    @discord.ui.button(label="back", style=discord.ButtonStyle.gray)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.aki.back()
        except asyncakinator.exceptions.CantGoBackAnyFurther:
            await interaction.followup.send(
                "You can't go back on the first question, try a different option instead.",
                ephemeral=True,
            )
        else:
            self.num -= 1
            await self.send_current_question(interaction)

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.green, row=1)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Starting a new game...", ephemeral=True)

        try:
            view = discord.ui.View()
            view.add_item(self.play_again)
            view.add_item(self.continue_game)
            view.add_item(self.cancel_game)
            await interaction.message.edit(embed=embed, view=view)

        except Exception as e:
            log.exception("Failed to start a new Akinator game", exc_info=e)
            await interaction.followup.send("An error occurred while starting a new game. Please try again later.",
                                            ephemeral=True)

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.gray)
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.blurple, row=1)
    async def continue_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.continue_attempts < 3:
            self.continue_attempts += 1
            await self.send_current_question(interaction)
        else:
            await self.cancel(interaction, "You have bested me!")

    async def answer_question(self, answer: str, interaction: discord.Interaction):
        self.num += 1
        try:
            akinator_answer = self.convert_to_akinator_answer(answer)
            question = await self.aki.answer(akinator_answer)
            if question:
                await self.send_current_question(interaction)
            else:
                await self.win(interaction)
        except Exception as error:
            log.exception("Error during answering question", exc_info=True)
            await interaction.followup.send(f"Error: {str(error)}")

    @staticmethod
    def convert_to_akinator_answer(answer: str):
        conversion_dict = {
            "yes": Answer.YES,
            "no": Answer.NO,
            "idk": Answer.I_DONT_KNOW,
            "probably": Answer.PROBABLY,
            "probably not": Answer.PROBABLY_NOT
        }
        return conversion_dict.get(answer, Answer.I_DONT_KNOW)

    async def answer(self, message: str, interaction: discord.Interaction):
        try:
            await self.aki.answer(message)
        except asyncakinator.AkiNoQuestions:
            await self.win(interaction)
        except asyncakinator.AkiTimedOut:
            await self.cancel(interaction, "The connection to the Akinator servers was lost.")
        except Exception as error:
            log.exception(
                f"Encountered an exception while answering with {message} during Akinator session",
                exc_info=True,
            )
            await self.edit_or_send(
                interaction, content=f"Akinator game has an error:\n`{error}`", embed=None
            )
            self.stop()

    @staticmethod
    async def edit_or_send(interaction: discord.Interaction, **kwargs):
        try:
            await interaction.message.edit(**kwargs)
        except discord.NotFound:
            await interaction.followup.send(**kwargs)
        except discord.Forbidden:
            pass

    def current_question_embed(self):
        e = discord.Embed(
            color=self.color,
            title=f"Question #{self.num}",
            description=self.aki.question,
        )
        if self.aki.progression > 0:
            e.set_footer(text=f"{round(self.aki.progression, 2)}% guessed")
        return e

    def get_winner_embed(self, winner: dict) -> discord.Embed:
        if 'absolute_picture_path' in winner and winner['absolute_picture_path']:
            image_url = winner["absolute_picture_path"]
        else:
            image_url = search_image(winner['name'])
            if not image_url:
                image_url = 'default_image_url'

        win_embed = discord.Embed(
            color=self.color,
            title=f"I'm {round(float(winner['proba']) * 100)}% sure it's {winner['name']}!",
            description=winner["description"]
        )
        win_embed.set_image(url=image_url)
        return win_embed

    @staticmethod
    def search_image(search_list):
        best_match = process.extractOne(query, search_list, score_cutoff=80)
        if not best_match:
            return None

        search_url = f"https://google.com/search?q={best_match[0]}"
        try:
            response = requests.get(search_url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error during requests to {search_url}: {str(e)}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        image_tags = soup.find_all('img')

        pattern = re.compile(r'https?://.*\.(jpg|jpeg|png|gif|bmp)')

        for tag in image_tags:
            image_url = tag.get('src')
            if pattern.match(image_url):
                return image_url

        return None

    def get_nsfw_embed(self):
        return discord.Embed(
            color=self.color,
            title="I guessed it, but this result is inappropriate.",
            description="Try again in a NSFW channel.",
        )

    @staticmethod
    def text_is_nsfw(text: str) -> bool:
        text = text.lower()
        return any(word in text for word in NSFW_WORDS)

    async def win(self, interaction: discord.Interaction):
        current_time = time.time()
        if current_time - AkiView.last_win_time < 60:
            await interaction.response.send_message("Please wait before starting a new game.", ephemeral=True)
            return

        try:
            winner = await self.aki.win()
            AkiView.last_win_time = current_time
            description = winner["description"]

            if self.sfw_mode and self.contains_nsfw_content(description):
                embed = self.get_nsfw_embed()
            else:
                embed = self.get_winner_embed(winner)

            if self.continue_attempts < 3:
                view = discord.ui.View()
                view.add_item(self.play_again)
                view.add_item(self.continue_game)
                view.add_item(self.cancel_game)
                await interaction.message.edit(embed=embed, view=view)
            else:
                view = discord.ui.View()
                view.add_item(self.play_again)
                view.add_item(self.cancel_game)
                await interaction.message.edit(embed=embed, view=view)
                self.stop()

        except Exception as e:
            log.exception("An error occurred while trying to win an Akinator game.", exc_info=e)
            embed = discord.Embed(
                color=self.color,
                title="An error occurred while trying to win the game.",
                description="Try again later.",
            )
            view = discord.ui.View()
            view.add_item(self.play_again)
            await interaction.message.edit(embed=embed, view=view)
            self.stop()

    async def edit(self, interaction: discord.Interaction):
        await interaction.message.edit(embed=self.current_question_embed(), view=self)

    async def cancel(
            self, interaction: discord.Interaction, message: str = "Akinator game cancelled."
    ):
        await self.edit_or_send(interaction, content=message, embed=None, view=None)
        self.stop()

    async def send_current_question(self, interaction: discord.Interaction):
        if self.aki.progression < 80:
            try:
                await self.edit(interaction)
            except discord.HTTPException:
                await self.cancel(interaction)
        else:
            await self.win(interaction)
