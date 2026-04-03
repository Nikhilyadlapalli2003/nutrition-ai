import csv
from django.core.management.base import BaseCommand
from nutrition.models import Food


class Command(BaseCommand):
    help = "Smart USDA Import with Intelligent Filtering + Micronutrients"

    def add_arguments(self, parser):
        parser.add_argument('food_csv', type=str)
        parser.add_argument('food_nutrient_csv', type=str)
        parser.add_argument('nutrient_csv', type=str)

    def handle(self, *args, **kwargs):

        food_csv = kwargs['food_csv']
        food_nutrient_csv = kwargs['food_nutrient_csv']
        nutrient_csv = kwargs['nutrient_csv']

        self.stdout.write("Loading nutrient definitions...")

        nutrient_map = {}
        with open(nutrient_csv, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                nutrient_map[row['id']] = row['name'].lower()

        self.stdout.write("Loading nutrient values...")

        nutrient_data = {}
        with open(food_nutrient_csv, encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                fdc_id = row['fdc_id']
                nutrient_id = row['nutrient_id']
                amount = row['amount']

                nutrient_name = nutrient_map.get(nutrient_id, "")

                if fdc_id not in nutrient_data:
                    nutrient_data[fdc_id] = {}

                nutrient_data[fdc_id][nutrient_name] = amount

        self.stdout.write("Importing food items with macros + micros...")

        created_count = 0

        with open(food_csv, encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                fdc_id = row['fdc_id']
                description = row['description']

                if fdc_id not in nutrient_data:
                    continue

                nutrients = nutrient_data[fdc_id]

                try:
                    # ----------------------
                    # MACROS
                    # ----------------------
                    calories = float(nutrients.get('energy', 0))
                    protein = float(nutrients.get('protein', 0))
                    carbs = float(nutrients.get('carbohydrate, by difference', 0))
                    fats = float(nutrients.get('total lipid (fat)', 0))

                    # ----------------------
                    # MICROS
                    # ----------------------
                    fiber = float(nutrients.get('fiber, total dietary', 0))
                    iron = float(nutrients.get('iron, fe', 0))
                    calcium = float(nutrients.get('calcium, ca', 0))
                    sodium = float(nutrients.get('sodium, na', 0))
                    vitamin_c = float(
                        nutrients.get('vitamin c, total ascorbic acid', 0)
                    )

                except:
                    continue

                if calories == 0:
                    continue

                name_lower = description.lower()

                # ----------------------
                # DIET TYPE DETECTION
                # ----------------------
                nonveg_keywords = [
                    "chicken", "beef", "pork", "fish", "mutton",
                    "lamb", "turkey", "egg", "shrimp", "crab"
                ]

                vegan_keywords = [
                    "tofu", "soy", "lentil", "bean",
                    "chickpea", "spinach", "broccoli"
                ]

                diet_type = "veg"

                if any(word in name_lower for word in nonveg_keywords):
                    diet_type = "nonveg"
                elif any(word in name_lower for word in vegan_keywords):
                    diet_type = "vegan"

                # ----------------------
                # CATEGORY DETECTION
                # ----------------------
                breakfast_keywords = [
                    "oats", "cereal", "milk", "toast",
                    "pancake", "banana", "smoothie"
                ]

                snack_keywords = [
                    "chips", "nuts", "cookie",
                    "chocolate", "bar"
                ]

                dinner_keywords = [
                    "rice", "curry", "chicken", "fish",
                    "beef", "paneer", "dal"
                ]

                category = "lunch"

                if any(word in name_lower for word in breakfast_keywords):
                    category = "breakfast"
                elif any(word in name_lower for word in snack_keywords):
                    category = "snack"
                elif any(word in name_lower for word in dinner_keywords):
                    category = "dinner"

                # Prevent duplicate import
                if Food.objects.filter(external_id=fdc_id).exists():
                    continue

                Food.objects.create(
                    name=description[:200],
                    calories=calories,
                    protein=protein,
                    carbs=carbs,
                    fats=fats,
                    fiber=fiber,
                    iron=iron,
                    calcium=calcium,
                    sodium=sodium,
                    vitamin_c=vitamin_c,
                    category=category,
                    diet_type=diet_type,
                    external_id=fdc_id,
                    source="USDA"
                )

                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Smart USDA Import Completed. {created_count} foods added with macros + micros."
        ))