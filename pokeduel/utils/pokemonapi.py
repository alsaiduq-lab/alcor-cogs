import os
import logging
import pokepy
import requests
from fuzzywuzzy import process

cache_directory = './data/sprites'
check_file = 'sprites_obtained_go_here'

full_path_to_check_file = os.path.join(cache_directory, check_file)
if not os.path.exists(cache_directory):
    os.makedirs(cache_directory)
    logging.info(f"Cache directory created at {cache_directory}")

if not os.path.exists(full_path_to_check_file):
    with open(full_path_to_check_file, 'w') as check_file:
        check_file.write('')
    logging.info(f"'{check_file}' file created in {cache_directory}")

client = pokepy.V2Client(cache='in_disk', cache_location=cache_directory)


def get_closest_pokemon_name(pokemon_name, pokemon_names):
    """
    Find the closest match for the given pokemon_name from the list of pokemon_names.
    """
    try:
        closest_match = process.extractOne(pokemon_name, pokemon_names)[0]
        logging.debug(f"Closest match for '{pokemon_name}' is '{closest_match}'")
        return closest_match
    except Exception as e:
        logging.error(f"Error in finding closest match for '{pokemon_name}': {e}", exc_info=True)
        return None


def download_sprite(url, filename):
    """
    Download a sprite from the given URL and save it to the specified filename.
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as file:
                file.write(response.content)
            logging.debug(f"Downloaded sprite: {filename}")
    except Exception as e:
        logging.error(f"Error downloading sprite from '{url}': {e}", exc_info=True)


def get_pokemon_data(pokemon_name, json_data):
    """
    Fetch Pokémon data from Pokepy using a fuzzy search match on the Pokémon name.
    """
    closest_match = None
    try:
        pokemon_names = list(json_data.keys())
        closest_match = get_closest_pokemon_name(pokemon_name, pokemon_names)

        if closest_match is None:
            logging.warning(f"No close match found for '{pokemon_name}'.")
            return None

        pokemon = client.get_pokemon(closest_match)
        sprite_url = pokemon.sprites.front_default
        if sprite_url:
            sprite_filename = os.path.join(cache_directory, f"{closest_match}.png")
            if not os.path.exists(sprite_filename):
                download_sprite(sprite_url, sprite_filename)
            return sprite_filename
        return None
    except Exception as e:
        logging.error(f"Error fetching data for Pokemon '{closest_match if closest_match else pokemon_name}': {e}", exc_info=True)
        return None


def cache_info():
    """
    Return cache information of the Pokepy client.
    """
    return client.cache_info()


def clear_cache():
    """
    Clear the cache of the Pokepy client.
    """
    client.cache_clear()
