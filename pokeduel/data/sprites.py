import requests
import os
import time
import logging
from functools import lru_cache, wraps
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rate_limited(max_per_hour):
    min_interval = 3600 / max_per_hour
    last_called = [0]

    def decorate(func):
        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_called[0] = int(time.time())
            return func(*args, **kwargs)

        return rate_limited_function

    return decorate


retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)


@lru_cache(maxsize=100)
@rate_limited(100)
def fetch_pokemon_sprite(pokemon_name):
    sprites_dir = 'sprites'
    sprite_file_path = os.path.join(sprites_dir, f"{pokemon_name.lower()}.png")

    if os.path.exists(sprite_file_path):
        return sprite_file_path

    try:
        response = http.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}")
        response.raise_for_status()

        data = response.json()
        sprite_url = data.get("sprites", {}).get("front_default")

        if not sprite_url:
            raise ValueError(f"No sprite URL found for {pokemon_name}")

        if not os.path.exists(sprites_dir):
            os.makedirs(sprites_dir)

        sprite_response = requests.get(sprite_url)
        sprite_response.raise_for_status()

        with open(sprite_file_path, 'wb') as file:
            file.write(sprite_response.content)

        return sprite_file_path

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while fetching sprite for {pokemon_name}: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred: {req_err}")
    except ValueError as val_err:
        logger.error(val_err)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    return None
