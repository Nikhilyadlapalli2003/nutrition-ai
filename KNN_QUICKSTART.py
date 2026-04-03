"""
=====================================================
QUICKSTART GUIDE - KNN RECOMMENDATIONS
=====================================================
Simple examples to get started with the ML integration
"""

# =====================================================
# EXAMPLE 1: Generate KNN-based meal plan for user
# =====================================================
from django.contrib.auth.models import User
from accounts.models import UserProfile
from recommendations.engine import get_knn_personalized_plan
from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal

# Get user and profile
user = User.objects.get(username='john_doe')
profile = UserProfile.objects.get(user=user)

# Calculate target calories
bmr = calculate_bmr(profile)
tdee = calculate_tdee(bmr, profile.activity_level)
target_calories = adjust_calories_by_goal(tdee, profile.goal)

# Generate KNN meal plan
meal_plan = get_knn_personalized_plan(user, profile, target_calories)

# Display results
for meal_type, food in meal_plan.items():
    if food:
        print(f"{meal_type}: {food.name} ({food.calories} cal)")


# =====================================================
# EXAMPLE 2: Find similar foods to a given food
# =====================================================
from nutrition.models import Food
from recommendations.engine import get_food_alternatives

# Get a food item
chicken = Food.objects.get(name="Chicken Breast")

# Find similar foods
alternatives = get_food_alternatives(chicken, k=5)

print(f"\nFoods similar to {chicken.name}:")
for alt in alternatives:
    score = alt['similarity_score']
    print(f"  - {alt['food'].name} (Similarity: {score:.3f})")


# =====================================================
# EXAMPLE 3: Learn user's food preferences
# =====================================================
from recommendations.ml_models import UserPreferenceKNN
from nutrition.models import FoodFeedback

# Create sample feedback (for testing)
user = User.objects.get(username='john_doe')
chicken = Food.objects.get(name="Chicken Breast")
FoodFeedback.objects.create(user=user, food=chicken, score=5)

# Learn preferences
user_pref = UserPreferenceKNN(user, min_feedback_score=3)

print(f"\nUser's Preferred Macros:")
macro = user_pref.get_favorite_nutrient_profile()
print(f"  Protein: {macro['protein']*100:.1f}%")
print(f"  Carbs: {macro['carbs']*100:.1f}%")
print(f"  Fats: {macro['fats']*100:.1f}%")

print(f"\nLiked Foods ({len(user_pref.liked_foods)} total):")
for food in user_pref.liked_foods[:5]:
    print(f"  - {food.name}")


# =====================================================
# EXAMPLE 4: Get recommendations by calorie target
# =====================================================
from recommendations.ml_models import KNNFoodRecommender

# Build KNN index
knn = KNNFoodRecommender(n_neighbors=5)
all_foods = Food.objects.all()
knn.build_index(all_foods)

# Get meals matching 500 calorie target for lunch
recommendations = knn.recommend_by_target(
    target_calories=500,
    meal_type='lunch',
    k=5
)

print(f"\nLunch options (≈500 cal):")
for rec in recommendations:
    score = rec['similarity_score']
    print(f"  - {rec['food'].name}: {rec['food'].calories} cal (Match: {score:.2f})")


# =====================================================
# EXAMPLE 5: API usage - Get food alternatives
# =====================================================
import requests
from django.urls import reverse

# Get alternatives via API
food_id = 1
url = reverse('food_alternatives', args=[food_id])
# response = requests.get(f"http://localhost:8000{url}")
# alternatives = response.json()['alternatives']

# Or in Django shell:
from recommendations.knn_views import get_alternatives_api
# Call view directly: get_alternatives_api(request, food_id)


# =====================================================
# EXAMPLE 6: View user's preference statistics
# =====================================================
from recommendations.ml_models import get_knn_recommendation_stats

user = User.objects.get(username='john_doe')
stats = get_knn_recommendation_stats(user)

print(f"\nUser Statistics:")
print(f"  Liked Foods: {stats['liked_foods_count']}")
print(f"  Avg Feedback Score: {stats['avg_feedback_score']:.2f}")
print(f"  Macro Preference: {stats['preferred_macro_ratio']}")


# =====================================================
# EXAMPLE 7: Compare hybrid vs KNN approach
# =====================================================
from recommendations.engine import structured_meal_plan

# Hybrid approach (original)
hybrid_plan = structured_meal_plan(profile, target_calories, user, use_knn=False)

# KNN approach (new)
knn_plan = get_knn_personalized_plan(user, profile, target_calories)

print(f"\nHybrid vs KNN Comparison:")
print(f"Breakfast - Hybrid: {hybrid_plan['breakfast'].name if hybrid_plan['breakfast'] else 'None'}")
print(f"Breakfast - KNN: {knn_plan['breakfast'].name if knn_plan['breakfast'] else 'None'}")


# =====================================================
# EXAMPLE 8: Build food similarity matrix
# =====================================================
from recommendations.ml_models import compute_food_similarity_matrix

# Compute pairwise similarities
similarity_matrix = compute_food_similarity_matrix(Food.objects.all())

# Get similar foods for first food
first_food_id = list(similarity_matrix.keys())[0]
similar = similarity_matrix[first_food_id]

print(f"\nSimilar foods to ID {first_food_id}:")
for item in similar:
    print(f"  - {item['food_name']} (Score: {item['similarity_score']:.3f})")


# =====================================================
# EXAMPLE 9: Handling errors gracefully
# =====================================================
from recommendations.ml_models import KNNFoodRecommender

try:
    # This might fail if no foods exist
    knn = KNNFoodRecommender(n_neighbors=5)
    empty_queryset = Food.objects.filter(name="NonExistent")
    knn.build_index(empty_queryset)
except ValueError as e:
    print(f"Error: {e}")
    print("Solution: Ensure Food objects exist in database")


# =====================================================
# EXAMPLE 10: Using with Django management command
# =====================================================
"""
# Create a custom management command: nutrition/management/commands/generate_knn_plans.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from recommendations.engine import get_knn_personalized_plan
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Generate KNN meal plans for all users'
    
    def handle(self, *args, **options):
        for user in User.objects.all():
            profile = UserProfile.objects.get(user=user)
            plan = get_knn_personalized_plan(user, profile, 2000)
            self.stdout.write(f"Generated plan for {user.username}")
"""


# =====================================================
# DATABASE SETUP (Run these once)
# =====================================================
"""
# 1. Ensure Food objects exist
# python manage.py import_usda

# 2. Create sample user feedback
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from nutrition.models import Food, FoodFeedback
>>> user = User.objects.first()
>>> food = Food.objects.first()
>>> FoodFeedback.objects.create(user=user, food=food, score=5)

# 3. Test KNN
>>> from recommendations.ml_models import KNNFoodRecommender
>>> knn = KNNFoodRecommender()
>>> knn.build_index(Food.objects.all())
>>> similar = knn.find_similar_foods(food, k=3)
>>> print(similar)
"""

print("\n✅ Examples loaded successfully!")
print("Run individual examples in Django shell: python manage.py shell")
