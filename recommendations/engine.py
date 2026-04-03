from nutrition.models import Food, FoodFeedback
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .collaborative import get_collaborative_recommendations
from .ml_models import (
    KNNFoodRecommender,
    KNNMealPlanner,
    UserPreferenceKNN,
    Nutrients,
    RandomForestMealSuitability,
    RandomForestMealEngine,
    SVMMealClassifier,
    SVMMealEngine,
    LinearRegressionMealPredictor,
    LinearRegressionNutrientEstimator,
    LinearRegressionMealPlanner
)


# =====================================================
# 🔥 PORTION NORMALIZATION (Phase 12)
# =====================================================
def normalize_portion(meal, meal_target_calories):

    if meal.calories <= meal_target_calories:
        meal.adjusted_calories = meal.calories
        meal.adjusted_protein = meal.protein
        meal.adjusted_carbs = meal.carbs
        meal.adjusted_fats = meal.fats
        return meal

    scale = meal_target_calories / meal.calories

    meal.adjusted_calories = meal.calories * scale
    meal.adjusted_protein = meal.protein * scale
    meal.adjusted_carbs = meal.carbs * scale
    meal.adjusted_fats = meal.fats * scale

    return meal


# =====================================================
# HEALTH FILTER
# =====================================================
def apply_health_filter(foods, medical_condition):
    """
    Filter foods based on medical conditions
    
    Args:
        foods: QuerySet of Food objects
        medical_condition: String like 'diabetes', 'hypertension', 'heart_disease', or None
    
    Returns:
        Filtered QuerySet
    """
    if not medical_condition or medical_condition == 'none':
        return foods
    
    medical_condition = medical_condition.lower()
    
    if medical_condition == 'diabetes':
        # For diabetes: lower carbs, higher fiber
        foods = foods.filter(carbs__lt=40, fiber__gt=2)
    
    elif medical_condition == 'hypertension':
        # For hypertension: lower sodium, lower fats
        foods = foods.filter(sodium__lt=500, fats__lt=15)
    
    elif medical_condition == 'heart_disease':
        # For heart disease: low saturated fats, low sodium, low cholesterol
        foods = foods.filter(sodium__lt=400, fats__lt=10)
    
    elif medical_condition == 'obesity':
        # For obesity: limit extremely high calorie and high fat items
        foods = foods.filter(calories__lt=500, fats__lt=20)
    
    return foods


def apply_allergy_filter(foods, allergies_list):
    """
    Filter out foods containing allergens
    
    Args:
        foods: QuerySet of Food objects
        allergies_list: List of allergen names (lowercased)
    
    Returns:
        Filtered QuerySet excluding foods with allergens
    """
    if not allergies_list:
        return foods
    
    # Exclude foods whose names contain any allergen (handles plural forms)
    for allergen in allergies_list:
        term = allergen.lower().strip()
        if not term:
            continue
        # start with the given term
        foods = foods.exclude(name__icontains=term)
        # also try singular version if plural
        if term.endswith('s'):
            singular = term[:-1]
            foods = foods.exclude(name__icontains=singular)
    
    return foods


def apply_sodium_limit_filter(foods, sodium_limit_mg):
    """
    Filter foods based on sodium limits
    
    Args:
        foods: QuerySet of Food objects
        sodium_limit_mg: Maximum sodium per meal in mg
    
    Returns:
        Filtered QuerySet
    """
    if not sodium_limit_mg or sodium_limit_mg <= 0:
        return foods
    
    return foods.filter(sodium__lte=sodium_limit_mg)


# =====================================================
# ALERT FUNCTIONS FOR SODIUM AND SUGAR
# =====================================================
def check_sodium_alerts(meal_plan, profile):
    """
    Check if daily meal plan exceeds sodium limits
    
    Args:
        meal_plan: dict with meal_type -> Food object
        profile: UserProfile object
    
    Returns:
        dict with alerts info: {'total_sodium': float, 'limit': int, 'alert': bool, 'message': str}
    """
    sodium_limit = getattr(profile, 'sodium_limit_mg', 2300)
    total_sodium = 0
    
    for meal in meal_plan.values():
        if meal:
            total_sodium += meal.sodium
    
    alert = total_sodium > sodium_limit
    
    return {
        'total_sodium': round(total_sodium, 2),
        'limit': sodium_limit,
        'alert': alert,
        'percentage': round((total_sodium / sodium_limit) * 100, 1),
        'message': f'Daily sodium intake ({total_sodium:.0f}mg) exceeds recommended limit ({sodium_limit}mg)' if alert else f'Sodium intake at {(total_sodium/sodium_limit)*100:.0f}% of daily limit'
    }


def check_sugar_alerts(meal_plan, profile):
    """
    Check if daily meal plan exceeds sugar limits
    Note: Food model doesn't have sugar field, but this is ready for expansion
    
    Args:
        meal_plan: dict with meal_type -> Food object
        profile: UserProfile object
    
    Returns:
        dict with alerts info: {'total_sugar': float, 'limit': int, 'alert': bool, 'message': str}
    """
    sugar_limit = getattr(profile, 'sugar_limit_g', 50)
    total_sugar = 0
    
    # Currently Food model doesn't have sugar field
    # This will work once sugar field is added to Food model
    for meal in meal_plan.values():
        if meal:
            total_sugar += getattr(meal, 'sugar', 0)
    
    alert = total_sugar > sugar_limit
    
    return {
        'total_sugar': round(total_sugar, 2),
        'limit': sugar_limit,
        'alert': alert,
        'percentage': round((total_sugar / sugar_limit) * 100, 1) if sugar_limit > 0 else 0,
        'message': f'Daily sugar intake ({total_sugar:.0f}g) exceeds recommended limit ({sugar_limit}g)' if alert else f'Sugar intake at {(total_sugar/sugar_limit)*100:.0f}% of daily limit' if sugar_limit > 0 else 'No sugar tracking'
    }


def check_condition_compliance(meal_plan, profile):
    """
    Check if meal plan is compliant with medical condition requirements
    
    Args:
        meal_plan: dict with meal_type -> Food object
        profile: UserProfile object
    
    Returns:
        dict with compliance info
    """
    medical_condition = getattr(profile, 'medical_conditions', None) or profile.health_condition
    if not medical_condition or medical_condition == 'none':
        return {'compliant': True, 'warnings': []}
    
    warnings = []
    medical_condition = medical_condition.lower()
    
    if medical_condition == 'diabetes':
        # Check carb limits
        for meal_type, meal in meal_plan.items():
            if meal and meal.carbs > 40:
                warnings.append(f'{meal_type.capitalize()}: High carbs ({meal.carbs}g) - may affect blood sugar')
    
    elif medical_condition == 'hypertension':
        # Check sodium and fat limits
        total_sodium = sum(meal.sodium for meal in meal_plan.values() if meal)
        if total_sodium > 2300:
            warnings.append(f'High sodium intake ({total_sodium:.0f}mg) - exceeds daily limit for hypertension')
        
        for meal_type, meal in meal_plan.items():
            if meal and meal.fats > 15:
                warnings.append(f'{meal_type.capitalize()}: High fats ({meal.fats}g) - may affect blood pressure')
    
    elif medical_condition == 'heart_disease':
        # Check sodium, fats, and balance
        total_sodium = sum(meal.sodium for meal in meal_plan.values() if meal)
        if total_sodium > 2000:
            warnings.append(f'High sodium intake ({total_sodium:.0f}mg) - strictly limit for heart disease')
        
        for meal_type, meal in meal_plan.items():
            if meal and meal.fats > 10:
                warnings.append(f'{meal_type.capitalize()}: High fats ({meal.fats}g) - limit saturated fats for heart health')
    
    elif medical_condition == 'obesity':
        # For obesity, warn when meals are excessively high in calories or fats
        for meal_type, meal in meal_plan.items():
            if meal and meal.calories > 600:
                warnings.append(f'{meal_type.capitalize()}: Very high calories ({meal.calories} kcal) - consider lighter options')
            if meal and meal.fats > 25:
                warnings.append(f'{meal_type.capitalize()}: High fats ({meal.fats}g) - may contribute to weight gain')
    
    return {
        'compliant': len(warnings) == 0,
        'condition': profile.get_medical_condition_display_name() if hasattr(profile, 'get_medical_condition_display_name') else medical_condition,
        'warnings': warnings
    }


# =====================================================
# VECTOR FUNCTIONS
# =====================================================
def food_to_vector(food):

    calories = getattr(food, "adjusted_calories", food.calories)
    protein = getattr(food, "adjusted_protein", food.protein)
    carbs = getattr(food, "adjusted_carbs", food.carbs)
    fats = getattr(food, "adjusted_fats", food.fats)

    return np.array([calories, protein, carbs, fats])


def target_vector(calories):
    protein = (calories * 0.30) / 4
    carbs = (calories * 0.40) / 4
    fats = (calories * 0.30) / 9
    return np.array([calories, protein, carbs, fats])


# =====================================================
# SMART RULE-BASED SCORING
# =====================================================
def smart_score(meal, target_calories, profile):

    calories = getattr(meal, "adjusted_calories", meal.calories)
    protein = getattr(meal, "adjusted_protein", meal.protein)
    carbs = getattr(meal, "adjusted_carbs", meal.carbs)
    fats = getattr(meal, "adjusted_fats", meal.fats)

    calorie_diff = abs(calories - target_calories)
    calorie_score = max(0, 150 - calorie_diff)

    protein_bonus = protein * 2
    macro_bonus = 10 if carbs > 0 and fats > 0 else 0

    goal_bonus = 0

    if profile.goal == "loss":
        goal_bonus += protein * 3
        goal_bonus -= carbs * 0.5

    elif profile.goal == "gain":
        goal_bonus += protein * 3
        goal_bonus += carbs * 1

    elif profile.goal == "maintain":
        goal_bonus += protein * 2

    if profile.health_condition:
        if "diabetes" in profile.health_condition.lower():
            goal_bonus -= carbs * 1.5

    total = calorie_score + protein_bonus + macro_bonus + goal_bonus

    return total / 300


# =====================================================
# USER FEEDBACK SCORE
# =====================================================
def get_user_feedback_score(user, meal):
    feedback = FoodFeedback.objects.filter(user=user, food=meal).first()
    return feedback.score if feedback else 0


# =====================================================
# 🤖 KNN-BASED MEAL SELECTION
# =====================================================
def get_best_meal_knn(foods, category, meal_target_calories, user, profile):
    """
    Use K-Nearest Neighbors to find the best meal for given category/calories
    Considers:
    1. Nutritional similarity to calorie target
    2. User preference history (feedback scores)
    3. Dietary preferences
    4. Meal diversity (avoid recent repeats)
    """
    
    # Filter by category and dietary preference
    meals = foods.filter(category=category)
    
    # Apply diversity filter - exclude recently eaten meals
    meals = apply_diversity_filter(user, meals, days_back=3)
    
    if not meals.exists() and category == "dinner":
        meals = foods.filter(category="lunch")
        meals = apply_diversity_filter(user, meals, days_back=3)
    
    if not meals.exists():
        # If no diverse meals available, allow recent ones but prefer older ones
        meals = foods.filter(category=category)
        if not meals.exists() and category == "dinner":
            meals = foods.filter(category="lunch")
    
    if not meals.exists():
        return None
    
    # Build KNN recommender
    try:
        knn = KNNFoodRecommender(n_neighbors=min(5, meals.count()))
        knn.build_index(meals)
        
        # Get recommendations based on calorie target
        recommendations = knn.recommend_by_target(
            meal_target_calories,
            meal_type=category,
            k=min(5, meals.count())
        )
        
        if not recommendations:
            return meals.first()
        
        # Score recommendations by user preference
        best_meal = None
        best_score = -1
        
        for rec in recommendations:
            meal = rec['food']
            # Normalize portion
            meal = normalize_portion(meal, meal_target_calories)
            
            # KNN similarity score (0-1)
            knn_score = rec['similarity_score']
            
            # User feedback boost
            feedback_score = get_user_feedback_score(user, meal)
            feedback_bonus = (feedback_score / 5.0) * 0.3  # Max 0.3
            
            # Final score combines KNN similarity + user preference
            final_score = (knn_score * 0.7) + feedback_bonus
            
            if final_score > best_score:
                best_score = final_score
                best_meal = meal
        
        return best_meal if best_meal else meals.first()
    
    except Exception as e:
        # Fallback to first meal if KNN fails
        print(f"KNN Error: {e}")
        return meals.first()


# =====================================================
# 🔥 HYBRID + COLLABORATIVE ENGINE
# =====================================================
def get_best_meal_hybrid(foods, category, meal_target_calories, user, profile):

    meals = foods.filter(category=category)

    # Apply diversity filter - exclude recently eaten meals
    meals = apply_diversity_filter(user, meals, days_back=3)

    # Dinner fallback
    if not meals.exists() and category == "dinner":
        meals = foods.filter(category="lunch")
        meals = apply_diversity_filter(user, meals, days_back=3)

    if not meals.exists():
        # If no diverse meals available, allow recent ones but prefer older ones
        meals = foods.filter(category=category)
        if not meals.exists() and category == "dinner":
            meals = foods.filter(category="lunch")

    # Collaborative recommendations
    collaborative_food_ids = get_collaborative_recommendations(user)

    target_vec = target_vector(meal_target_calories).reshape(1, -1)

    best_meal = None
    best_score = -1

    for meal in meals:

        # Portion normalize
        meal = normalize_portion(meal, meal_target_calories)

        meal_vec = food_to_vector(meal).reshape(1, -1)

        # Content similarity
        cosine_sim = cosine_similarity(meal_vec, target_vec)[0][0]

        # Smart rule score
        s_score = smart_score(meal, meal_target_calories, profile)

        # Feedback boost
        feedback_bonus = get_user_feedback_score(user, meal) * 0.1

        # Collaborative boost
        collaborative_bonus = 0
        if meal.id in collaborative_food_ids:
            collaborative_bonus = 0.2

        final_score = (
            (cosine_sim * 0.5) +
            (s_score * 0.3) +
            feedback_bonus +
            collaborative_bonus
        )

        if final_score > best_score:
            best_score = final_score
            best_meal = meal

    return best_meal


# =====================================================
# 🌳 RANDOM FOREST MEAL SELECTION
# =====================================================
def get_best_meal_rf(foods, category, meal_target_calories, user, profile, rf_model=None):
    """
    Use Random Forest to find the best meal for given category/calories
    """
    meals = foods.filter(category=category)
    meals = apply_diversity_filter(user, meals, days_back=3)
    
    if not meals.exists() and category == "dinner":
        meals = foods.filter(category="lunch")
        meals = apply_diversity_filter(user, meals, days_back=3)
    
    if not meals.exists():
        meals = foods.filter(category=category)
        if not meals.exists() and category == "dinner":
            meals = foods.filter(category="lunch")
            
    if not meals.exists():
        return None
        
    if rf_model is None:
        # Cold Start Fallback: Rank using heuristic smart_score if ML model has no data yet
        scored_meals = []
        for meal in meals[:30]:  # Limit to top 30 candidates for performance
            score = smart_score(meal, meal_target_calories, profile)
            scored_meals.append((meal, score))
            
        if not scored_meals:
            return meals.first()
            
        scored_meals.sort(key=lambda x: x[1], reverse=True)
        best_meal = scored_meals[0][0]
        best_meal = normalize_portion(best_meal, meal_target_calories)
        
        # Scale score to 0-100% and attach
        best_meal.suitability_score = min(100, max(0, int(scored_meals[0][1] * 100)))
        return best_meal
        
    # Rank using the trained Random Forest Decision Trees
    ranked = rf_model.rank_foods(meals, top_k=10)
    
    if not ranked:
        meal = meals.first()
        if meal:
            meal = normalize_portion(meal, meal_target_calories)
            score = smart_score(meal, meal_target_calories, profile)
            meal.suitability_score = min(100, max(0, int(score * 100)))
        return meal
        
    best_item = ranked[0]
    best_food = best_item['food']
    best_score = best_item['suitability_score']
    
    for item in ranked:
        food = item['food']
        # Normalize portion to check calorie difference
        norm_food = normalize_portion(food, meal_target_calories)
        calories_diff = abs(norm_food.adjusted_calories - meal_target_calories)
        
        # Prefer foods closer to target but weight suitability highly
        best_norm = normalize_portion(best_food, meal_target_calories)
        if calories_diff < abs(best_norm.adjusted_calories - meal_target_calories) and item['suitability_score'] > best_score - 0.1:
            best_food = food
            best_score = item['suitability_score']
            
    best_food = normalize_portion(best_food, meal_target_calories)
    best_food.suitability_score = round(best_score * 100)
    return best_food


# =====================================================
# STRUCTURED DAILY MEAL PLAN
# =====================================================
def structured_meal_plan(profile, target_calories, user, use_knn=False, use_rf=True):
    """
    Generate structured meal plan for the day
    
    Args:
        profile: UserProfile object
        target_calories: Daily calorie target
        user: User object
        use_knn: Boolean to use KNN-based recommendations (default: False)
        use_rf: Boolean to use Random Forest recommendations (default: True)
    
    Returns:
        dict with meals for each category
    """

    foods = Food.objects.filter(
        diet_type=profile.dietary_preference
    )

    # Apply medical condition filtering (use new field if available, fallback to old)
    medical_condition = getattr(profile, 'medical_conditions', None) or profile.health_condition
    foods = apply_health_filter(foods, medical_condition)
    
    # Apply allergy filtering
    allergies_list = getattr(profile, 'get_allergies_list', lambda: [])()
    foods = apply_allergy_filter(foods, allergies_list)
    
    # Apply sodium limit filtering
    sodium_limit = getattr(profile, 'sodium_limit_mg', 2300)
    # Sodium limit per meal (divide by 4 meals, but allow some variance)
    meal_sodium_limit = sodium_limit / 3  # Be stricter at meal level
    foods = apply_sodium_limit_filter(foods, meal_sodium_limit)

    breakfast_cal = target_calories * 0.25
    lunch_cal = target_calories * 0.35
    dinner_cal = target_calories * 0.30
    snack_cal = target_calories * 0.10

    if use_rf:
        # Pre-train RF models for the user
        rf_engine = RandomForestMealEngine(user, profile, target_calories)
        rf_engine.train_all_models()
        
        return {
            "breakfast": get_best_meal_rf(foods, "breakfast", breakfast_cal, user, profile, rf_engine.rf_models.get("breakfast")),
            "lunch": get_best_meal_rf(foods, "lunch", lunch_cal, user, profile, rf_engine.rf_models.get("lunch")),
            "dinner": get_best_meal_rf(foods, "dinner", dinner_cal, user, profile, rf_engine.rf_models.get("dinner")),
            "snack": get_best_meal_rf(foods, "snack", snack_cal, user, profile, rf_engine.rf_models.get("snack")),
        }

    # Choose engine based on preference
    meal_selector = get_best_meal_knn if use_knn else get_best_meal_hybrid

    return {
        "breakfast": meal_selector(
            foods, "breakfast", breakfast_cal, user, profile
        ),
        "lunch": meal_selector(
            foods, "lunch", lunch_cal, user, profile
        ),
        "dinner": meal_selector(
            foods, "dinner", dinner_cal, user, profile
        ),
        "snack": meal_selector(
            foods, "snack", snack_cal, user, profile
        ),
    }


# =====================================================
# KNN-ENHANCED PERSONALIZED MEAL PLAN
# =====================================================
def get_knn_personalized_plan(user, profile, target_calories):
    """
    Generate fully personalized meal plan using KNN + user preferences
    This combines:
    - Nutritional target matching via KNN
    - User preference learning from feedback history
    - Dietary type and health condition filters
    
    Returns: dict with personalized meal plan
    """
    try:
        planner = KNNMealPlanner(user, profile, target_calories)
        return planner.generate_meal_plan()
    except Exception as e:
        print(f"KNN Planned Error: {e}")
        # Fallback to hybrid approach
        return structured_meal_plan(profile, target_calories, user, use_knn=False)


# =====================================================
# MEAL DIVERSITY CONTROL
# =====================================================
def check_meal_diversity(user, food, days_back=3):
    """
    Check if a meal has been eaten recently to prevent repetition
    Returns True if meal is diverse (not recently eaten), False if too recent
    
    Args:
        user: User object
        food: Food object to check
        days_back: Number of days to check for repetition (default: 3)
    
    Returns: bool - True if diverse, False if recently eaten
    """
    from datetime import date, timedelta
    from nutrition.models import MealHistory
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Check if this food was eaten in the recent period
    recent_meals = MealHistory.objects.filter(
        user=user,
        food=food,
        date__range=[start_date, end_date]
    )
    
    return not recent_meals.exists()


def apply_diversity_filter(user, foods_queryset, days_back=3):
    """
    Filter out recently eaten foods from a queryset
    Used to ensure meal variety in recommendations
    
    Args:
        user: User object
        foods_queryset: Django queryset of Food objects
        days_back: Days to check for repetition
    
    Returns: Filtered queryset excluding recent meals
    """
    from datetime import date, timedelta
    from nutrition.models import MealHistory
    
    # Get recently eaten food IDs
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    recent_food_ids = MealHistory.objects.filter(
        user=user,
        date__range=[start_date, end_date]
    ).values_list('food_id', flat=True).distinct()
    
    # Exclude recently eaten foods
    return foods_queryset.exclude(id__in=recent_food_ids)


# =====================================================
# GET FOOD ALTERNATIVES (KNN-BASED)
# =====================================================
def get_food_alternatives(food, k=5, user=None, exclude_recent=True):
    """
    Find k similar foods to the given food using KNN
    Useful for meal variations and preferences
    
    Args:
        food: Food object
        k: Number of alternatives to return
        user: User object (optional, for diversity control)
        exclude_recent: Whether to exclude recently eaten meals
    
    Returns:
        list of similar foods with scores
    """
    all_foods = Food.objects.exclude(id=food.id)
    
    # Apply diversity filter if user provided
    if user and exclude_recent:
        all_foods = apply_diversity_filter(user, all_foods, days_back=3)
    
    if not all_foods.exists():
        return []
    
    try:
        knn = KNNFoodRecommender(n_neighbors=k)
        knn.build_index(all_foods)
        
        similar = knn.find_similar_foods(food, k=k)
        return similar
    except Exception as e:
        print(f"Alternatives Error: {e}")
        return []


# =====================================================
# SVM-BASED HEALTHY MEAL PLAN
# =====================================================
def get_svm_healthy_plan(user, profile, target_calories, health_threshold=0.6):
    """
    Generate healthy meal plan using SVM health classification
    Focuses on meals classified as healthy/suitable by SVM

    Args:
        user: User object
        profile: UserProfile object
        target_calories: Target daily calories
        health_threshold: Minimum health score (0-1)

    Returns: dict with healthy meal plan
    """
    try:
        engine = SVMMealEngine(user, profile, target_calories, health_threshold)
        engine.train_all_models()
        return engine.generate_healthy_meal_plan()
    except Exception as e:
        print(f"SVM Healthy Plan Error: {e}")
        # Fallback to structured plan
        return structured_meal_plan(profile, target_calories, user, use_knn=False)


# =====================================================
# SVM HEALTH CLASSIFICATION
# =====================================================
def classify_meal_health_svm(user, food):
    """
    Classify if a meal is healthy/suitable using SVM
    Returns: dict with classification and confidence score
    """
    try:
        svm = SVMMealClassifier(user)
        if not svm.train():
            return {
                'classification': 'unknown',
                'confidence': 0.0,
                'reason': 'insufficient_data'
            }

        health_score = svm.classify_meal_health(food, return_probability=True)
        classification = 'healthy' if health_score >= 0.5 else 'less_suitable'

        return {
            'classification': classification,
            'confidence': float(health_score),
            'food_name': food.name,
            'food_id': food.id
        }

    except Exception as e:
        print(f"SVM Classification Error: {e}")
        return {
            'classification': 'error',
            'confidence': 0.0,
            'error': str(e)
        }


# =====================================================
# FILTER HEALTHY FOODS (SVM)
# =====================================================
def get_healthy_food_filter(user, foods_queryset, health_threshold=0.6):
    """
    Filter a queryset of foods to only include healthy ones using SVM
    Useful for improving recommendation quality

    Args:
        user: User object
        foods_queryset: Django queryset of Food objects
        health_threshold: Minimum health score (0-1)

    Returns: Filtered queryset of healthy foods
    """
    try:
        svm = SVMMealClassifier(user)
        if not svm.train():
            return foods_queryset  # Return all if no model

        foods_list = list(foods_queryset)
        healthy_foods = svm.filter_healthy_meals(foods_list, health_threshold)

        # Convert back to queryset
        healthy_ids = [f.id for f in healthy_foods]
        return foods_queryset.filter(id__in=healthy_ids)

    except Exception as e:
        print(f"SVM Filter Error: {e}")
        return foods_queryset  # Return original on error


# =====================================================
# LINEAR REGRESSION OPTIMIZED MEAL PLAN
# =====================================================
def get_linear_regression_optimized_plan(user, profile, target_calories):
    """
    Generate optimized meal plan using Linear Regression predictions
    Combines suitability prediction with nutrient distribution estimation

    Args:
        user: User object
        profile: UserProfile object
        target_calories: Target daily calories

    Returns: tuple (meal_plan, nutrient_plan)
    """
    try:
        planner = LinearRegressionMealPlanner(user, profile, target_calories)
        planner.train_models()
        return planner.generate_optimized_meal_plan()
    except Exception as e:
        print(f"Linear Regression Plan Error: {e}")
        # Fallback to structured plan
        return structured_meal_plan(profile, target_calories, user, use_knn=False), {}


# =====================================================
# WEEKLY MEAL PLAN GENERATOR
# =====================================================
def generate_weekly_meal_plan(user, profile, target_calories, days=7):
    """
    Generate a weekly meal plan with diversity control

    Args:
        user: User object
        profile: UserProfile object
        target_calories: Daily calorie target
        days: Number of days to plan (default: 7)

    Returns: dict with daily meal plans
    """
    from datetime import date, timedelta

    weekly_plan = {}
    start_date = date.today()

    # Track meals used this week to ensure diversity
    used_meals = set()

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)

        # Generate daily plan with diversity
        daily_plan = structured_meal_plan(profile, target_calories, user, use_knn=True)

        # Apply additional diversity check for the week
        for meal_type, meal in daily_plan.items():
            if meal:
                meal_key = f"{meal.id}_{meal_type}"
                if meal_key in used_meals:
                    # Try to find an alternative
                    alternatives = get_food_alternatives(meal, k=3, user=user, exclude_recent=True)
                    for alt in alternatives:
                        alt_key = f"{alt['food'].id}_{meal_type}"
                        if alt_key not in used_meals:
                            daily_plan[meal_type] = alt['food']
                            used_meals.add(alt_key)
                            break
                else:
                    used_meals.add(meal_key)

        weekly_plan[current_date] = daily_plan

    return weekly_plan


# =====================================================
# GROCERY LIST GENERATOR
# =====================================================
def generate_grocery_list(user, profile, target_calories, days=7):
    """
    Generate a grocery list from a weekly meal plan

    Args:
        user: User object
        profile: UserProfile object
        target_calories: Daily calorie target
        days: Number of days to plan (default: 7)

    Returns: dict with aggregated ingredients
    """
    from nutrition.models import FoodIngredient, GroceryList
    from datetime import date, timedelta
    from collections import defaultdict

    # Generate weekly meal plan
    weekly_plan = generate_weekly_meal_plan(user, profile, target_calories, days)

    # Aggregate ingredients
    ingredient_totals = defaultdict(lambda: {'quantity': 0.0, 'unit': 'pieces', 'category': 'other'})

    for daily_plan in weekly_plan.values():
        for meal in daily_plan.values():
            if meal:
                # Get ingredients for this food
                food_ingredients = FoodIngredient.objects.filter(food=meal)

                for food_ing in food_ingredients:
                    ing_name = food_ing.ingredient.name
                    quantity = food_ing.quantity
                    unit = food_ing.unit
                    category = food_ing.ingredient.category

                    # Aggregate quantities (simplified - assumes same units)
                    if ingredient_totals[ing_name]['unit'] == unit:
                        ingredient_totals[ing_name]['quantity'] += quantity
                    else:
                        # Different units - keep the first one and add quantity
                        ingredient_totals[ing_name]['quantity'] += quantity

                    ingredient_totals[ing_name]['unit'] = unit
                    ingredient_totals[ing_name]['category'] = category

    # Round quantities for better display
    for ing_data in ingredient_totals.values():
        ing_data['quantity'] = round(ing_data['quantity'], 2)

    # Save to database
    week_start = date.today()
    grocery_list, created = GroceryList.objects.get_or_create(
        user=user,
        week_start_date=week_start,
        defaults={
            'name': f'Weekly Grocery List ({week_start})',
            'ingredients_data': dict(ingredient_totals)
        }
    )

    if not created:
        grocery_list.ingredients_data = dict(ingredient_totals)
        grocery_list.save()

    return dict(ingredient_totals), grocery_list


# =====================================================
# INGREDIENT-BASED MEAL RECOMMENDATIONS
# =====================================================
def get_meals_from_ingredients(user, available_ingredients, profile, target_calories):
    """
    Recommend meals based on available ingredients

    Args:
        user: User object
        available_ingredients: list of ingredient names
        profile: UserProfile object
        target_calories: Daily calorie target

    Returns: dict with recommended meals by category
    """
    from nutrition.models import FoodIngredient, Ingredient
    from django.db.models import Q

    # Get ingredient objects (case-insensitive)
    ingredient_ids = []
    for ing_name in available_ingredients:
        ing_name = ing_name.strip()
        # Try exact match first (case-insensitive)
        ingredient = Ingredient.objects.filter(name__iexact=ing_name).first()
        if ingredient:
            ingredient_ids.append(ingredient.id)
        else:
            # Try partial match
            ingredient = Ingredient.objects.filter(name__icontains=ing_name).first()
            if ingredient:
                ingredient_ids.append(ingredient.id)

    ingredient_objects = Ingredient.objects.filter(id__in=ingredient_ids)

    if not ingredient_objects.exists():
        return {}

    # Find foods that contain these ingredients
    food_ids_with_ingredients = FoodIngredient.objects.filter(
        ingredient__in=ingredient_objects
    ).values_list('food_id', flat=True).distinct()

    # Get foods that match user's dietary preferences
    candidate_foods = Food.objects.filter(id__in=food_ids_with_ingredients)
    if profile.dietary_preference:
        candidate_foods = candidate_foods.filter(diet_type=profile.dietary_preference)

    # Apply health filter
    candidate_foods = apply_health_filter(candidate_foods, profile.health_condition)

    # Group by category and find best matches
    recommendations = {}

    for category in ['breakfast', 'lunch', 'dinner', 'snack']:
        category_foods = candidate_foods.filter(category=category)

        if category_foods.exists():
            # Score foods by how many ingredients they use
            scored_foods = []
            for food in category_foods:
                food_ingredients = FoodIngredient.objects.filter(food=food)
                matching_ingredients = food_ingredients.filter(ingredient__in=ingredient_objects).count()
                total_ingredients = food_ingredients.count()

                if total_ingredients > 0:
                    match_score = matching_ingredients / total_ingredients
                    scored_foods.append((food, match_score))

            # Sort by match score and get top recommendation
            if scored_foods:
                scored_foods.sort(key=lambda x: x[1], reverse=True)
                best_food = scored_foods[0][0]

                # Normalize portion
                meal_target_calories = target_calories * {
                    'breakfast': 0.25,
                    'lunch': 0.35,
                    'dinner': 0.30,
                    'snack': 0.10
                }[category]

                best_food = normalize_portion(best_food, meal_target_calories)
                recommendations[category] = best_food

    return recommendations


# =====================================================
# PREDICT MEAL SUITABILITY (LINEAR REGRESSION)
# =====================================================
def predict_meal_suitability_lr(user, food):
    """
    Predict meal suitability score using Linear Regression
    Returns: dict with suitability score and rating
    """
    try:
        predictor = LinearRegressionMealPredictor(user)
        if not predictor.train():
            return {
                'suitability_score': 0.5,
                'rating': 'unknown',
                'reason': 'insufficient_data'
            }

        score = predictor.predict_suitability(food)
        rating = 'Excellent' if score >= 0.8 else \
                'Good' if score >= 0.6 else \
                'Fair' if score >= 0.4 else 'Poor'

        return {
            'suitability_score': float(score),
            'rating': rating,
            'food_name': food.name,
            'food_id': food.id
        }

    except Exception as e:
        print(f"Linear Regression Prediction Error: {e}")
        return {
            'suitability_score': 0.5,
            'rating': 'error',
            'error': str(e)
        }


# =====================================================
# ESTIMATE NUTRIENT DISTRIBUTION (LINEAR REGRESSION)
# =====================================================
def estimate_nutrient_distribution_lr(user, profile, target_calories):
    """
    Estimate ideal nutrient distribution using Linear Regression
    Returns: dict with recommended macro ratios and targets
    """
    try:
        estimator = LinearRegressionNutrientEstimator(user)
        if not estimator.train():
            # Return default distribution
            return estimator._get_default_distribution(target_calories)

        return estimator.estimate_nutrient_distribution(profile, target_calories)

    except Exception as e:
        print(f"Linear Regression Estimation Error: {e}")
        # Return default distribution
        estimator = LinearRegressionNutrientEstimator(user)
        return estimator._get_default_distribution(target_calories)


# =====================================================
# GET SUITABILITY RANKINGS (LINEAR REGRESSION)
# =====================================================
def get_food_suitability_rankings(user, foods_queryset, top_k=10):
    """
    Rank foods by suitability score using Linear Regression
    Useful for personalized food recommendations

    Args:
        user: User object
        foods_queryset: Django queryset of Food objects
        top_k: Number of top foods to return

    Returns: list of ranked foods with scores
    """
    try:
        predictor = LinearRegressionMealPredictor(user)
        if not predictor.train():
            return []

        foods_list = list(foods_queryset)
        return predictor.rank_foods_by_suitability(foods_list, top_k=top_k)

    except Exception as e:
        print(f"Linear Regression Ranking Error: {e}")
        return []