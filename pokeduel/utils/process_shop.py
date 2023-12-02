class PokemonProcessor:
    def __init__(self, pokemon_data):
        self.pokemon_data = pokemon_data

    @staticmethod
    def find_strongest_attack(pokemon):
        max_effective_damage = 0
        strongest_attack = None
        for attack in pokemon["Base Wheel Size"]:
            try:
                damage = 0
                if attack["Move Type"] in ["White", "Blue"]:
                    damage = int(attack["Damage"])
                elif attack["Move Type"] == "Purple":
                    damage = 70
                elif attack["Move Type"] == "Gold":
                    damage = int(attack["Damage"]) * 1.5

                if damage > max_effective_damage:
                    max_effective_damage = damage
                    strongest_attack = attack["Name"]
            except (ValueError, KeyError):
                continue

        return (strongest_attack, max_effective_damage) if strongest_attack else ("Unknown", 0)

    def process_pokemon_data(self):
        processed_data = []
        for name, details in self.pokemon_data.items():
            strongest_attack, attack_damage = self.find_strongest_attack(details)
            processed_data.append({
                "name": name,
                "rarity": details["Rarity"],
                "strongest_attack": strongest_attack,
                "attack_damage": attack_damage
            })

        return processed_data

    def process_pokemon(self, pokemon):
        strongest_attack, attack_damage = self.find_strongest_attack(pokemon)
        return {
            "name": pokemon['name'],
            "rarity": pokemon['Rarity'],
            "strongest_attack": strongest_attack,
            "attack_damage": attack_damage
        }


class PlateProcessor:
    def __init__(self, plates_data):
        self.plates_data = plates_data

    def process_plates_data(self):
        processed_data = []

        for plate in self.plates_data:
            cost = int(plate["Cost"]) if plate["Cost"].isdigit() else 0

            plate_info = {
                "id": plate["ID"],
                "name": plate["Name"],
                "cost": cost,
                "rarity": plate["Rarity"].strip(),
                "color": plate["Color"],
                "effect": plate["Effect"]
            }
            processed_data.append(plate_info)

        return processed_data

    @staticmethod
    def process_plate(plate):
        return {
            "id": plate["plate_id"],
            "color": plate["Color"],
            "name": plate["Name"],
            "rarity": plate["Rarity"].strip(),
            "cost": int(plate["Cost"]) if plate["Cost"].isdigit() else 0,
            "effect": plate["Effect"]
        }


class ShopDataProcessor:
    def __init__(self, pokemon_data, plates_data):
        self.pokemon_processor = PokemonProcessor(pokemon_data)
        self.plate_processor = PlateProcessor(plates_data)

    def create_shop_data_template(self, num_pokemon=5, num_plates=3):
        if isinstance(self.pokemon_processor.pokemon_data, dict):
            pokemon_list = [{'name': name, **details} for name, details in self.pokemon_processor.pokemon_data.items()]
        else:
            pokemon_list = self.pokemon_processor.pokemon_data

        if 'plates' in self.plate_processor.plates_data:
            plates_list = [{'plate_id': re.search(r'\d+', plate['ID']).group(), **plate} for plate in
                           self.plate_processor.plates_data['plates']]
        else:
            plates_list = self.plate_processor.plates_data

        num_pokemon = min(num_pokemon, len(pokemon_list))
        num_plates = min(num_plates, len(plates_list))

        selected_pokemon = random.sample(pokemon_list, num_pokemon) if num_pokemon > 0 else []
        selected_plates = random.sample(plates_list, num_plates) if num_plates > 0 else []

        pokemon_items = [self.pokemon_processor.process_pokemon(p) for p in selected_pokemon]
        plate_items = [self.plate_processor.process_plate(p) for p in selected_plates]

        return {"pokemon": pokemon_items, "plates": plate_items}
