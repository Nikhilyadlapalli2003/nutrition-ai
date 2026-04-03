#!/usr/bin/env python
"""
Test script for Grocery List Generator and Ingredient-Based Recommendations
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nutrition_ai.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile
from nutrition.models import Food, Ingredient, FoodIngredient, GroceryList, UserIngredient
from recommendations.engine import generate_grocery_list, get_meals_from_ingredients

def test_grocery_list():
    """Test grocery list generation"""
    print("🛒 Testing Grocery List Generator...")

    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return False

        profile = UserProfile.objects.get(user=user)

        # Calculate target calories
        from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal
        bmr = calculate_bmr(profile)
        tdee = calculate_tdee(bmr, profile.activity_level)
        target_calories = adjust_calories_by_goal(tdee, profile.goal)

        # Generate grocery list
        ingredients_data, grocery_list_obj = generate_grocery_list(user, profile, target_calories, days=7)

        print(f"✅ Grocery list generated: {len(ingredients_data)} items")
        print(f"   List saved for user: {user.username}")
        print(f"   Week start: {grocery_list_obj.week_start_date}")

        # Show sample ingredients
        sample_items = list(ingredients_data.items())[:5]
        for ing_name, data in sample_items:
            print(f"   • {ing_name}: {data['quantity']} {data['unit']}")

        return True

    except Exception as e:
        print(f"❌ Grocery list test failed: {e}")
        return False

def test_ingredient_recommendations():
    """Test ingredient-based meal recommendations"""
    print("\n🥘 Testing Ingredient-Based Recommendations...")

    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return False

        profile = UserProfile.objects.get(user=user)

        # Calculate target calories
        from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal
        bmr = calculate_bmr(profile)
        tdee = calculate_tdee(bmr, profile.activity_level)
        target_calories = adjust_calories_by_goal(tdee, profile.goal)

        # Test with some common ingredients
        test_ingredients = ['Chicken', 'Rice', 'Oil', 'Salt']

        recommendations = get_meals_from_ingredients(user, test_ingredients, profile, target_calories)

        print(f"✅ Recommendations generated for ingredients: {', '.join(test_ingredients)}")
        print(f"   Found meals for: {list(recommendations.keys())}")

        for meal_type, meal in recommendations.items():
            print(f"   • {meal_type.title()}: {meal.name}")

        return True

    except Exception as e:
        print(f"❌ Ingredient recommendations test failed: {e}")
        return False

def test_user_ingredients():
    """Test user ingredient management"""
    print("\n📝 Testing User Ingredient Management...")

    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return False

        # Get some ingredients
        ingredients = Ingredient.objects.all()[:3]
        if not ingredients:
            print("❌ No ingredients found in database")
            return False

        # Add user ingredients
        for ing in ingredients:
            user_ing, created = UserIngredient.objects.get_or_create(
                user=user,
                ingredient=ing,
                defaults={'quantity': 2.0, 'unit': ing.unit}
            )
            if created:
                print(f"   Added: {ing.name} ({user_ing.quantity} {user_ing.unit})")

        # Check user ingredients
        user_ingredients = UserIngredient.objects.filter(user=user)
        print(f"✅ User has {user_ingredients.count()} ingredients saved")

        return True

    except Exception as e:
        print(f"❌ User ingredients test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Grocery List & Ingredient Features Tests\n")

    results = []
    results.append(test_grocery_list())
    results.append(test_ingredient_recommendations())
    results.append(test_user_ingredients())

    passed = sum(results)
    total = len(results)

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Grocery list and ingredient features are working.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)