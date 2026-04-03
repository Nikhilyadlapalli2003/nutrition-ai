"""
=====================================================
KNN-BASED RECOMMENDATION VIEWS
=====================================================
Enhanced recommendation views using Machine Learning
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from accounts.models import UserProfile
from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal
from nutrition.models import Food, FoodFeedback, MealHistory
from .engine import (
    get_knn_personalized_plan,
    structured_meal_plan,
    get_food_alternatives,
    get_svm_healthy_plan,
    classify_meal_health_svm,
    get_healthy_food_filter
)
from .ml_models import (
    KNNMealPlanner,
    UserPreferenceKNN,
    get_knn_recommendation_stats,
    SVMMealClassifier,
    SVMMealEngine,
    get_svm_model_stats
)
from datetime import date
import json


# =====================================================
# 🤖 KNN PERSONALIZED MEAL PLAN VIEW
# =====================================================
@login_required
def knn_recommendation_view(request):
    """
    KNN-enhanced personalized meal plan
    Uses K-Nearest Neighbors for food similarity detection
    and user preference learning
    """
    profile = UserProfile.objects.get(user=request.user)

    # ----------------------------------
    # 1️⃣ Calculate Target Calories
    # ----------------------------------
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)

    # ----------------------------------
    # 2️⃣ KNN Personalized Meal Plan
    # ----------------------------------
    try:
        meal_plan = get_knn_personalized_plan(profile, target_calories, request.user)
    except Exception as e:
        # Fallback to hybrid approach
        print(f"KNN Plan Error: {e}")
        meal_plan = structured_meal_plan(profile, target_calories, request.user, use_knn=False)

    # ----------------------------------
    # 3️⃣ Attach Feedback Score & Alternatives
    # ----------------------------------
    for meal_type, meal in meal_plan.items():
        if meal:
            # Feedback score
            feedback = FoodFeedback.objects.filter(
                user=request.user,
                food=meal
            ).first()
            meal.user_feedback_score = feedback.score if feedback else 0
            
            # Get similar food alternatives
            try:
                alternatives = get_food_alternatives(meal, k=3)
                meal.alternatives = alternatives
            except:
                meal.alternatives = []

    # ----------------------------------
    # 4️⃣ Save Meal History
    # ----------------------------------
    today = date.today()
    MealHistory.objects.filter(
        user=request.user,
        date=today
    ).delete()

    for meal_type, meal in meal_plan.items():
        if meal:
            cal = getattr(meal, "adjusted_calories", meal.calories)
            pro = getattr(meal, "adjusted_protein", meal.protein)
            carb = getattr(meal, "adjusted_carbs", meal.carbs)
            fat = getattr(meal, "adjusted_fats", meal.fats)

            MealHistory.objects.create(
                user=request.user,
                food=meal,
                meal_type=meal_type,
                calories=cal,
                protein=pro,
                carbs=carb,
                fats=fat
            )

    # ----------------------------------
    # 5️⃣ Calculate Totals
    # ----------------------------------
    calories_data = []
    protein_total = 0
    carbs_total = 0
    fats_total = 0
    fiber_total = 0
    iron_total = 0
    calcium_total = 0
    sodium_total = 0
    vitamin_c_total = 0

    for meal in meal_plan.values():
        if meal:
            cal = getattr(meal, "adjusted_calories", meal.calories)
            pro = getattr(meal, "adjusted_protein", meal.protein)
            carb = getattr(meal, "adjusted_carbs", meal.carbs)
            fat = getattr(meal, "adjusted_fats", meal.fats)

            calories_data.append(round(cal, 2))
            protein_total += pro
            carbs_total += carb
            fats_total += fat
            fiber_total += meal.fiber
            iron_total += meal.iron
            calcium_total += meal.calcium
            sodium_total += meal.sodium
            vitamin_c_total += meal.vitamin_c
        else:
            calories_data.append(0)

    # ----------------------------------
    # 6️⃣ KNN Statistics & Preferences
    # ----------------------------------
    pref_knn = UserPreferenceKNN(request.user)
    preferred_ratio = pref_knn.get_favorite_nutrient_profile()

    # ----------------------------------
    # 7️⃣ Context
    # ----------------------------------
    context = {
        "meal_plan": meal_plan,
        "target_calories": round(target_calories, 2),
        
        "calories_data": calories_data,
        "protein_total": round(protein_total, 2),
        "carbs_total": round(carbs_total, 2),
        "fats_total": round(fats_total, 2),
        
        "fiber_total": round(fiber_total, 2),
        "iron_total": round(iron_total, 2),
        "calcium_total": round(calcium_total, 2),
        "sodium_total": round(sodium_total, 2),
        "vitamin_c_total": round(vitamin_c_total, 2),
        
        "preferred_protein_ratio": round(preferred_ratio['protein'] * 100, 1),
        "preferred_carbs_ratio": round(preferred_ratio['carbs'] * 100, 1),
        "preferred_fats_ratio": round(preferred_ratio['fats'] * 100, 1),
        
        "liked_foods_count": len(pref_knn.liked_foods),
        "recommendation_engine": "KNN (Machine Learning)",
    }

    return render(request, "recommendations.html", context)


# =====================================================
# 🤖 FOOD ALTERNATIVES API (JSON)
# =====================================================
@login_required
def get_alternatives_api(request, food_id):
    """
    API endpoint to get similar foods for a given food
    Returns JSON with alternatives and similarity scores
    """
    try:
        food = Food.objects.get(id=food_id)
        alternatives = get_food_alternatives(food, k=5, user=request.user, exclude_recent=True)
        
        data = {
            "success": True,
            "food": {
                "id": food.id,
                "name": food.name,
                "calories": food.calories,
            },
            "alternatives": [
                {
                    "id": alt['food'].id,
                    "name": alt['food'].name,
                    "calories": alt['food'].calories,
                    "similarity_score": round(alt['similarity_score'], 3),
                    "category": alt['food'].category,
                }
                for alt in alternatives
            ]
        }
        return JsonResponse(data)
    
    except Food.DoesNotExist:
        return JsonResponse({"success": False, "error": "Food not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =====================================================
# 🤖 USER PREFERENCE ANALYTICS
# =====================================================
@login_required
def preference_analytics_view(request):
    """
    View user's KNN-based preference analysis
    Shows learned food preferences and recommendations
    """
    pref_knn = UserPreferenceKNN(request.user, min_feedback_score=3)
    
    # Get user's liked foods
    liked_foods = pref_knn.liked_foods
    
    # Get macro ratio preference
    macro_ratio = pref_knn.get_favorite_nutrient_profile()
    
    # Get recommendations based on preferences
    all_foods = Food.objects.all()
    recommendations = pref_knn.get_recommendations_from_preferences(all_foods, k=10)
    
    context = {
        "liked_foods": liked_foods,
        "liked_foods_count": len(liked_foods),
        
        "recommended_foods": recommendations,
        
        "preferred_protein_ratio": f"{macro_ratio['protein']*100:.1f}%",
        "preferred_carbs_ratio": f"{macro_ratio['carbs']*100:.1f}%",
        "preferred_fats_ratio": f"{macro_ratio['fats']*100:.1f}%",
        
        "recommendation_engine": "KNN",
    }
    
    return render(request, "preference_analytics.html", context)


# =====================================================
# 🤖 KNN STATS API
# =====================================================
@login_required
def knn_stats_api(request):
    """
    API endpoint for KNN recommendation statistics
    Used for dashboard widgets and analytics
    """
    try:
        pref_knn = UserPreferenceKNN(request.user)
        macro_ratio = pref_knn.get_favorite_nutrient_profile()
        
        data = {
            "success": True,
            "liked_foods_count": len(pref_knn.liked_foods),
            "preferred_macros": {
                "protein": round(macro_ratio['protein'] * 100, 1),
                "carbs": round(macro_ratio['carbs'] * 100, 1),
                "fats": round(macro_ratio['fats'] * 100, 1),
            },
            "recommendation_model": "KNN",
        }
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =====================================================
# 🤖 MEAL REPLACEMENT VIEW
# =====================================================
@login_required
def meal_replacement_view(request, meal_type, current_food_id):
    """
    View for replacing a specific meal with alternatives
    Shows current meal and top 5 diverse alternatives
    Fetches the actual current meal from database, not from URL parameter
    """
    try:
        from datetime import date
        
        # Get user profile for calorie calculations
        profile = UserProfile.objects.get(user=request.user)
        bmr = calculate_bmr(profile)
        tdee = calculate_tdee(bmr, profile.activity_level)
        target_calories = adjust_calories_by_goal(tdee, profile.goal)
        
        # Calculate target calories for this meal type
        meal_calorie_targets = {
            "breakfast": target_calories * 0.25,
            "lunch": target_calories * 0.35,
            "dinner": target_calories * 0.30,
            "snack": target_calories * 0.10,
        }
        meal_target_calories = meal_calorie_targets.get(meal_type, target_calories * 0.25)
        
        # IMPORTANT: Fetch the ACTUAL current meal from MealHistory, not from URL
        # This ensures we always show the latest meal, even after replacements
        today = date.today()
        meal_history = MealHistory.objects.filter(
            user=request.user,
            meal_type=meal_type,
            date=today
        ).first()
        
        if meal_history:
            # Use the actual meal from the database
            current_food = meal_history.food
        else:
            # Fallback to the food_id from URL if no meal history found
            current_food = Food.objects.get(id=current_food_id)
        
        # Get alternatives (top 5, diverse)
        alternatives = get_food_alternatives(current_food, k=5, user=request.user, exclude_recent=True)
        
        # Normalize portions for display
        from .engine import normalize_portion
        current_food = normalize_portion(current_food, meal_target_calories)
        
        for alt in alternatives:
            alt['food'] = normalize_portion(alt['food'], meal_target_calories)
        
        context = {
            "meal_type": meal_type,
            "current_food": current_food,
            "alternatives": alternatives,
            "meal_target_calories": round(meal_target_calories, 2),
        }
        
        return render(request, "meal_replacement.html", context)
        
    except Food.DoesNotExist:
        return render(request, "error.html", {"error": "Meal not found"})
    except Exception as e:
        return render(request, "error.html", {"error": str(e)})


# =====================================================
# 🤖 MEAL REPLACEMENT API
# =====================================================
@login_required
def replace_meal_api(request):
    """
    API endpoint to replace a meal in the current plan
    Updates meal history and returns updated plan data
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)
    
    try:
        meal_type = request.POST.get('meal_type')
        new_food_id = request.POST.get('new_food_id')
        
        logger.info(f"Replace meal API called: meal_type={meal_type}, food_id={new_food_id}, user={request.user}")
        
        if not meal_type or not new_food_id:
            logger.error("Missing parameters")
            return JsonResponse({"success": False, "error": "Missing parameters: meal_type or new_food_id"}, status=400)
        
        # Get new food
        try:
            new_food = Food.objects.get(id=new_food_id)
            logger.info(f"Found food: {new_food.name}")
        except Food.DoesNotExist:
            logger.error(f"Food with id {new_food_id} not found")
            return JsonResponse({"success": False, "error": f"Food with id {new_food_id} not found"}, status=404)
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            logger.error("User profile not found")
            return JsonResponse({"success": False, "error": "User profile not found"}, status=404)
            
        bmr = calculate_bmr(profile)
        tdee = calculate_tdee(bmr, profile.activity_level)
        target_calories = adjust_calories_by_goal(tdee, profile.goal)
        
        # Calculate target calories for this meal type
        meal_calorie_targets = {
            "breakfast": target_calories * 0.25,
            "lunch": target_calories * 0.35,
            "dinner": target_calories * 0.30,
            "snack": target_calories * 0.10,
        }
        meal_target_calories = meal_calorie_targets.get(meal_type, target_calories * 0.25)
        
        # Normalize portion
        from .engine import normalize_portion
        new_food = normalize_portion(new_food, meal_target_calories)
        
        # Update today's meal history
        from datetime import date
        today = date.today()
        
        logger.info(f"Looking for existing meal: user={request.user}, meal_type={meal_type}, date={today}")
        
        # Get the old meal to preserve its timestamp
        old_meal = MealHistory.objects.filter(
            user=request.user,
            meal_type=meal_type,
            date=today
        ).first()
        
        if old_meal:
            logger.info(f"Found existing meal (id={old_meal.id}), updating...")
            # Update existing meal directly using update() to preserve timestamps
            calories_val = getattr(new_food, "adjusted_calories", new_food.calories)
            protein_val = getattr(new_food, "adjusted_protein", new_food.protein)
            carbs_val = getattr(new_food, "adjusted_carbs", new_food.carbs)
            fats_val = getattr(new_food, "adjusted_fats", new_food.fats)
            
            logger.info(f"Updating meal with: calories={calories_val}, protein={protein_val}, carbs={carbs_val}, fats={fats_val}")
            
            update_count = MealHistory.objects.filter(id=old_meal.id).update(
                food=new_food,
                calories=calories_val,
                protein=protein_val,
                carbs=carbs_val,
                fats=fats_val,
            )
            
            logger.info(f"Update count: {update_count}")
            
            if update_count == 0:
                logger.error("Failed to update meal - update_count was 0")
                return JsonResponse({"success": False, "error": "Failed to update meal"}, status=500)
        else:
            logger.info("No existing meal found, creating new...")
            # If no old meal exists, create a new one
            MealHistory.objects.create(
                user=request.user,
                food=new_food,
                meal_type=meal_type,
                calories=getattr(new_food, "adjusted_calories", new_food.calories),
                protein=getattr(new_food, "adjusted_protein", new_food.protein),
                carbs=getattr(new_food, "adjusted_carbs", new_food.carbs),
                fats=getattr(new_food, "adjusted_fats", new_food.fats),
            )
        
        logger.info(f"Successfully replaced meal with {new_food.name}")
        
        return JsonResponse({
            "success": True,
            "message": f"Successfully replaced {meal_type} with {new_food.name}",
            "new_meal": {
                "id": new_food.id,
                "name": new_food.name,
                "calories": round(getattr(new_food, "adjusted_calories", new_food.calories), 2),
                "protein": round(getattr(new_food, "adjusted_protein", new_food.protein), 2),
                "carbs": round(getattr(new_food, "adjusted_carbs", new_food.carbs), 2),
                "fats": round(getattr(new_food, "adjusted_fats", new_food.fats), 2),
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Exception in replace_meal_api: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = f"{str(e)} - {traceback.format_exc()}"
        return JsonResponse({"success": False, "error": error_msg}, status=500)


# =====================================================
# 🤖 SVM HEALTHY MEAL PLAN VIEW
# =====================================================
@login_required
def svm_healthy_recommendation_view(request):
    """
    SVM-based healthy meal plan
    Uses Support Vector Machine for health classification
    """
    profile = UserProfile.objects.get(user=request.user)

    # ----------------------------------
    # 1️⃣ Calculate Target Calories
    # ----------------------------------
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)

    # ----------------------------------
    # 2️⃣ SVM Healthy Meal Plan
    # ----------------------------------
    try:
        meal_plan = get_svm_healthy_plan(request.user, profile, target_calories)
    except Exception as e:
        # Fallback to hybrid approach
        print(f"SVM Plan Error: {e}")
        meal_plan = structured_meal_plan(profile, target_calories, request.user, use_knn=False)

    # ----------------------------------
    # 3️⃣ Attach Health Scores & Classification
    # ----------------------------------
    for meal_type, meal in meal_plan.items():
        if meal:
            # Health classification
            try:
                health_info = classify_meal_health_svm(request.user, meal)
                meal.health_classification = health_info.get('classification', 'unknown')
                meal.health_confidence = health_info.get('confidence', 0.0)
            except:
                meal.health_classification = 'unknown'
                meal.health_confidence = 0.0

            # Get similar healthy alternatives
            try:
                all_alternatives = get_food_alternatives(meal, k=10)
                # Filter to healthy alternatives only
                healthy_alternatives = get_healthy_food_filter(
                    request.user,
                    Food.objects.filter(id__in=[alt['food'].id for alt in all_alternatives])
                )
                meal.healthy_alternatives = list(healthy_alternatives[:3])
            except:
                meal.healthy_alternatives = []

    # ----------------------------------
    # 4️⃣ Save Meal History
    # ----------------------------------
    today = date.today()
    MealHistory.objects.filter(
        user=request.user,
        date=today
    ).delete()

    for meal_type, meal in meal_plan.items():
        if meal:
            cal = getattr(meal, "adjusted_calories", meal.calories)
            pro = getattr(meal, "adjusted_protein", meal.protein)
            carb = getattr(meal, "adjusted_carbs", meal.carbs)
            fat = getattr(meal, "adjusted_fats", meal.fats)

            MealHistory.objects.create(
                user=request.user,
                food=meal,
                meal_type=meal_type,
                calories=cal,
                protein=pro,
                carbs=carb,
                fats=fat
            )

    # ----------------------------------
    # 5️⃣ Calculate Totals
    # ----------------------------------
    calories_data = []
    protein_total = 0
    carbs_total = 0
    fats_total = 0
    fiber_total = 0
    iron_total = 0
    calcium_total = 0
    sodium_total = 0
    vitamin_c_total = 0

    for meal in meal_plan.values():
        if meal:
            cal = getattr(meal, "adjusted_calories", meal.calories)
            pro = getattr(meal, "adjusted_protein", meal.protein)
            carb = getattr(meal, "adjusted_carbs", meal.carbs)
            fat = getattr(meal, "adjusted_fats", meal.fats)

            calories_data.append(round(cal, 2))
            protein_total += pro
            carbs_total += carb
            fats_total += fat
            fiber_total += meal.fiber
            iron_total += meal.iron
            calcium_total += meal.calcium
            sodium_total += meal.sodium
            vitamin_c_total += meal.vitamin_c
        else:
            calories_data.append(0)

    # ----------------------------------
    # 6️⃣ SVM Statistics
    # ----------------------------------
    svm_stats = get_svm_model_stats(request.user)

    # ----------------------------------
    # 7️⃣ Context
    # ----------------------------------
    context = {
        "meal_plan": meal_plan,
        "target_calories": round(target_calories, 2),

        "calories_data": calories_data,
        "protein_total": round(protein_total, 2),
        "carbs_total": round(carbs_total, 2),
        "fats_total": round(fats_total, 2),

        "fiber_total": round(fiber_total, 2),
        "iron_total": round(iron_total, 2),
        "calcium_total": round(calcium_total, 2),
        "sodium_total": round(sodium_total, 2),
        "vitamin_c_total": round(vitamin_c_total, 2),

        "svm_stats": svm_stats,
        "recommendation_engine": "SVM (Support Vector Machine)",
        "health_focused": True,
    }

    return render(request, "recommendations.html", context)


# =====================================================
# 🤖 MEAL HEALTH CLASSIFICATION API (JSON)
# =====================================================
@login_required
def meal_health_api(request, food_id):
    """
    API endpoint to classify meal health using SVM
    Returns JSON with health classification and confidence
    """
    try:
        food = Food.objects.get(id=food_id)
        health_info = classify_meal_health_svm(request.user, food)

        data = {
            "success": True,
            "food": {
                "id": food.id,
                "name": food.name,
                "calories": food.calories,
                "category": food.category,
            },
            "health_analysis": health_info
        }
        return JsonResponse(data)

    except Food.DoesNotExist:
        return JsonResponse({"success": False, "error": "Food not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =====================================================
# 🤖 HEALTHY FOODS FILTER API
# =====================================================
@login_required
def healthy_foods_api(request, meal_type=None):
    """
    API endpoint to get healthy food recommendations
    Filters foods using SVM health classification
    """
    try:
        # Get base queryset
        if meal_type:
            foods = Food.objects.filter(category=meal_type)
        else:
            foods = Food.objects.all()

        # Apply SVM health filter
        healthy_foods = get_healthy_food_filter(request.user, foods)

        # Convert to JSON
        foods_data = []
        for food in healthy_foods[:20]:  # Limit to 20 results
            health_info = classify_meal_health_svm(request.user, food)

            foods_data.append({
                "id": food.id,
                "name": food.name,
                "calories": food.calories,
                "protein": food.protein,
                "carbs": food.carbs,
                "fats": food.fats,
                "category": food.category,
                "health_classification": health_info.get('classification'),
                "health_confidence": health_info.get('confidence')
            })

        data = {
            "success": True,
            "meal_type": meal_type,
            "healthy_foods": foods_data,
            "total_count": len(foods_data)
        }
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =====================================================
# 🤖 SVM STATS API
# =====================================================
@login_required
def svm_stats_api(request):
    """
    API endpoint for SVM model statistics
    Used for dashboard widgets and analytics
    """
    try:
        svm_stats = get_svm_model_stats(request.user)

        data = {
            "success": True,
            "svm_models": svm_stats,
            "recommendation_model": "SVM",
            "health_focused": True,
        }
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
