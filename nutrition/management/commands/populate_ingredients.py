from django.core.management.base import BaseCommand
from nutrition.models import Ingredient, Food, FoodIngredient

class Command(BaseCommand):
    help = 'Populate database with sample ingredients and food-ingredient relationships'

    def handle(self, *args, **options):
        # Create sample ingredients
        ingredients_data = [
            # Dairy
            {'name': 'Milk', 'category': 'dairy', 'unit': 'l'},
            {'name': 'Cheese', 'category': 'dairy', 'unit': 'g'},
            {'name': 'Yogurt', 'category': 'dairy', 'unit': 'g'},
            {'name': 'Butter', 'category': 'dairy', 'unit': 'g'},

            # Meat
            {'name': 'Chicken', 'category': 'meat', 'unit': 'kg'},
            {'name': 'Beef', 'category': 'meat', 'unit': 'kg'},
            {'name': 'Fish', 'category': 'meat', 'unit': 'kg'},
            {'name': 'Eggs', 'category': 'meat', 'unit': 'pieces'},

            # Vegetables
            {'name': 'Rice', 'category': 'grain', 'unit': 'kg'},
            {'name': 'Wheat flour', 'category': 'grain', 'unit': 'kg'},
            {'name': 'Oats', 'category': 'grain', 'unit': 'kg'},
            {'name': 'Bread', 'category': 'grain', 'unit': 'pieces'},

            # Vegetables
            {'name': 'Tomatoes', 'category': 'vegetable', 'unit': 'kg'},
            {'name': 'Onions', 'category': 'vegetable', 'unit': 'kg'},
            {'name': 'Potatoes', 'category': 'vegetable', 'unit': 'kg'},
            {'name': 'Carrots', 'category': 'vegetable', 'unit': 'kg'},
            {'name': 'Spinach', 'category': 'vegetable', 'unit': 'g'},
            {'name': 'Broccoli', 'category': 'vegetable', 'unit': 'g'},

            # Fruits
            {'name': 'Apples', 'category': 'fruit', 'unit': 'kg'},
            {'name': 'Bananas', 'category': 'fruit', 'unit': 'kg'},
            {'name': 'Oranges', 'category': 'fruit', 'unit': 'kg'},

            # Other
            {'name': 'Oil', 'category': 'oil', 'unit': 'l'},
            {'name': 'Salt', 'category': 'spice', 'unit': 'g'},
            {'name': 'Sugar', 'category': 'other', 'unit': 'g'},
        ]

        self.stdout.write('Creating ingredients...')
        for ing_data in ingredients_data:
            ingredient, created = Ingredient.objects.get_or_create(
                name=ing_data['name'],
                defaults={
                    'category': ing_data['category'],
                    'unit': ing_data['unit']
                }
            )
            if created:
                self.stdout.write(f'  Created: {ingredient.name}')

        # Create some sample food-ingredient relationships
        self.stdout.write('\nCreating food-ingredient relationships...')

        # Get some foods and ingredients
        foods = Food.objects.all()[:20]  # Get first 20 foods
        ingredients = list(Ingredient.objects.all())

        if not foods:
            self.stdout.write('No foods found in database!')
            return

        # Sample mappings (simplified)
        food_mappings = {
            'oats': ['Oats', 'Milk'],
            'chicken': ['Chicken', 'Oil', 'Salt'],
            'rice': ['Rice', 'Oil', 'Salt'],
            'bread': ['Wheat flour', 'Oil'],
            'milk': ['Milk'],
            'eggs': ['Eggs'],
            'cheese': ['Cheese'],
            'yogurt': ['Yogurt'],
            'fish': ['Fish', 'Oil'],
            'beef': ['Beef', 'Oil'],
        }

        for food in foods:
            food_name_lower = food.name.lower()

            # Find matching ingredients
            matched_ingredients = []
            for key, ing_names in food_mappings.items():
                if key in food_name_lower:
                    matched_ingredients.extend(ing_names)

            # Create relationships
            for ing_name in matched_ingredients:
                try:
                    ingredient = Ingredient.objects.get(name=ing_name)
                    FoodIngredient.objects.get_or_create(
                        food=food,
                        ingredient=ingredient,
                        defaults={
                            'quantity': 1.0,
                            'unit': ingredient.unit
                        }
                    )
                    self.stdout.write(f'  Linked: {food.name} -> {ingredient.name}')
                except Ingredient.DoesNotExist:
                    continue

        self.stdout.write('\n✅ Sample ingredients and relationships created!')