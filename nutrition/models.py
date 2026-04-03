from django.db import models
from django.contrib.auth.models import User


# =====================================================
# FOOD MODEL
# =====================================================
class Food(models.Model):

    CATEGORY_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]

    DIET_CHOICES = [
        ('veg', 'Vegetarian'),
        ('nonveg', 'Non-Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Keto'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="lunch")
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES, default="veg")

    # -------------------
    # MACRONUTRIENTS
    # -------------------
    calories = models.FloatField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fats = models.FloatField()

    # -------------------
    # MICRONUTRIENTS
    # -------------------
    fiber = models.FloatField(default=0)
    iron = models.FloatField(default=0)
    calcium = models.FloatField(default=0)
    sodium = models.FloatField(default=0)
    vitamin_c = models.FloatField(default=0)
    sugar = models.FloatField(default=0, help_text="Added sugar in grams")

    external_id = models.CharField(max_length=100, null=True, blank=True)
    source = models.CharField(max_length=100, default="manual")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =====================================================
# USER FEEDBACK MODEL
# =====================================================
class FoodFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'food')

    def __str__(self):
        return f"{self.user.username} - {self.food.name}"


# =====================================================
# 🔥 MEAL HISTORY MODEL (NEW)
# =====================================================
class MealHistory(models.Model):

    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)

    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)

    date = models.DateField(auto_now_add=True)

    # Store portion-normalized values at time of recommendation
    calories = models.FloatField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fats = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.meal_type} - {self.date}"


# =====================================================
# INGREDIENT MODEL
# =====================================================
class Ingredient(models.Model):
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50, choices=[
        ('dairy', 'Dairy'),
        ('meat', 'Meat'),
        ('vegetable', 'Vegetable'),
        ('fruit', 'Fruit'),
        ('grain', 'Grain'),
        ('spice', 'Spice'),
        ('oil', 'Oil'),
        ('other', 'Other'),
    ], default='other')

    # Common units for shopping
    unit = models.CharField(max_length=20, default='pieces', choices=[
        ('pieces', 'pieces'),
        ('kg', 'kg'),
        ('g', 'g'),
        ('l', 'l'),
        ('ml', 'ml'),
        ('cups', 'cups'),
        ('tbsp', 'tbsp'),
        ('tsp', 'tsp'),
        ('oz', 'oz'),
        ('lb', 'lb'),
    ])

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =====================================================
# FOOD INGREDIENT RELATIONSHIP
# =====================================================
class FoodIngredient(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    # Quantity per serving
    quantity = models.FloatField(default=1.0)
    unit = models.CharField(max_length=20, default='pieces')

    # Optional: preparation notes
    notes = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('food', 'ingredient')

    def __str__(self):
        return f"{self.food.name} - {self.ingredient.name}"


# =====================================================
# GROCERY LIST MODEL
# =====================================================
class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, default="Weekly Grocery List")
    week_start_date = models.DateField()

    # Store aggregated ingredients
    ingredients_data = models.JSONField(default=dict)  # {'ingredient_name': {'quantity': 2.0, 'unit': 'kg'}}

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'week_start_date')

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.week_start_date})"


# =====================================================
# USER INGREDIENTS (Available at home)
# =====================================================
class UserIngredient(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)

    # Quantity available
    quantity = models.FloatField(default=0)
    unit = models.CharField(max_length=20, default='pieces')

    # Expiry date
    expiry_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'ingredient')

    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name}"