from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal
from nutrition.models import Food, FoodFeedback, MealHistory
from .engine import structured_meal_plan, check_sodium_alerts, check_sugar_alerts, check_condition_compliance
from .ml_models import RandomForestMealEngine
from datetime import date


@login_required
def recommendation_view(request):

    profile = UserProfile.objects.get(user=request.user)

    # ----------------------------------
    # 1️⃣ BMR + TDEE + Goal Adjustment
    # ----------------------------------
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)

    # ----------------------------------
    # 2️⃣ Check for existing meals today
    # ----------------------------------
    today = date.today()
    existing_meal_count = MealHistory.objects.filter(
        user=request.user,
        date=today
    ).count()

    # ----------------------------------
    # 3️⃣ Get or Generate Meal Plan
    # ----------------------------------
    meal_histories = {}  # Will store actual calorie values from MealHistory
    
    if existing_meal_count == 0:
        # ✏️ Generate NEW meal plan only if none exists for today
        meal_plan = structured_meal_plan(profile, target_calories, request.user)
        
        # 🔥 Save to database
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
                
                # Store the values for totals calculation
                meal_histories[meal_type] = {
                    'calories': cal,
                    'protein': pro,
                    'carbs': carb,
                    'fats': fat,
                }
    else:
        # ✅ Use existing meals from today (preserves replacements!)
        meal_plan = {}
        meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
        for meal_type in meal_types:
            meal_history = MealHistory.objects.filter(
                user=request.user,
                meal_type=meal_type,
                date=today
            ).first()
            if meal_history:
                meal_plan[meal_type] = meal_history.food
                # Store actual values from MealHistory
                meal_histories[meal_type] = {
                    'calories': meal_history.calories,
                    'protein': meal_history.protein,
                    'carbs': meal_history.carbs,
                    'fats': meal_history.fats,
                }
            else:
                meal_plan[meal_type] = None

    # ----------------------------------
    # 4️⃣ Attach Feedback Score & ML Decision Score
    # ----------------------------------
    rf_engine = RandomForestMealEngine(request.user, profile, target_calories)
    rf_engine.train_all_models()

    for meal_type, meal in meal_plan.items():
        if meal:
            feedback = FoodFeedback.objects.filter(
                user=request.user,
                food=meal
            ).first()
            meal.user_feedback_score = feedback.score if feedback else 0
            
            if not hasattr(meal, 'suitability_score'):
                if meal_type in rf_engine.rf_models:
                    score = rf_engine.rf_models[meal_type].predict_suitability(meal, return_probability=True)
                    meal.suitability_score = round(score * 100) if score is not None else None
                
                # Cold Start Fallback: Always display a score by calculating a baseline heuristic
                if getattr(meal, 'suitability_score', None) is None:
                    from .engine import smart_score
                    
                    # Estimate meal target calories
                    meal_ratios = {'breakfast': 0.25, 'lunch': 0.35, 'dinner': 0.30, 'snack': 0.10}
                    meal_target = target_calories * meal_ratios.get(meal_type, 0.25)
                    
                    calc_score = smart_score(meal, meal_target, profile)
                    meal.suitability_score = min(100, max(0, int(calc_score * 100)))

    # ----------------------------------
    # 5️⃣ Totals Calculation
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

    for meal_type, meal in meal_plan.items():
        if meal:
            # Use actual values from meal_histories (which are from MealHistory DB)
            if meal_type in meal_histories:
                cal = meal_histories[meal_type]['calories']
                pro = meal_histories[meal_type]['protein']
                carb = meal_histories[meal_type]['carbs']
                fat = meal_histories[meal_type]['fats']
            else:
                # Fallback for legacy meals without stored values
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
    # 6️⃣ Feedback Summary
    # ----------------------------------
    total_positive = FoodFeedback.objects.filter(
        user=request.user,
        score__gt=0
    ).count()

    total_negative = FoodFeedback.objects.filter(
        user=request.user,
        score__lt=0
    ).count()

    # ----------------------------------
    # 7️⃣ Get Recent Meal History
    # ----------------------------------
    meal_history = MealHistory.objects.filter(
        user=request.user
    ).order_by("-date", "-created_at")[:10]

    # ----------------------------------
    # 8️⃣ Context
    # ----------------------------------
    sodium_alert = check_sodium_alerts(meal_plan, profile)
    sugar_alert = check_sugar_alerts(meal_plan, profile)
    condition_compliance = check_condition_compliance(meal_plan, profile)
    
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

        "total_positive": total_positive,
        "total_negative": total_negative,

        "meal_history": meal_history,
        
        # 🔥 Alert information
        "sodium_alert": sodium_alert,
        "sugar_alert": sugar_alert,
        "condition_compliance": condition_compliance,
        "user_allergies": profile.get_allergies_list() if hasattr(profile, 'get_allergies_list') else [],
        "has_medical_condition": profile.has_medical_condition() if hasattr(profile, 'has_medical_condition') else False,
    }

    return render(request, "recommendations.html", context)


# =====================================================
# GROCERY LIST VIEW
# =====================================================
@login_required
def grocery_list_view(request):
    """
    Generate and display grocery list from weekly meal plan
    """
    profile = UserProfile.objects.get(user=request.user)

    # Calculate target calories
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)

    # Generate grocery list
    from .engine import generate_grocery_list
    ingredients_data, grocery_list_obj = generate_grocery_list(
        request.user, profile, target_calories, days=7
    )

    # Group ingredients by category for better display
    categorized_ingredients = {}
    for ing_name, data in ingredients_data.items():
        category = data['category']
        if category not in categorized_ingredients:
            categorized_ingredients[category] = []
        categorized_ingredients[category].append({
            'name': ing_name,
            'quantity': data['quantity'],
            'unit': data['unit']
        })

    context = {
        "grocery_list": grocery_list_obj,
        "categorized_ingredients": categorized_ingredients,
        "total_items": len(ingredients_data),
        "week_start": grocery_list_obj.week_start_date,
    }

    return render(request, "grocery_list.html", context)


# =====================================================
# INGREDIENT-BASED RECOMMENDATIONS VIEW
# =====================================================
@login_required
def ingredient_recommendations_view(request):
    """
    Show form for ingredient input and display recommendations
    """
    profile = UserProfile.objects.get(user=request.user)

    # Calculate target calories
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)

    recommendations = {}
    available_ingredients = []

    if request.method == 'POST':
        # Get ingredients from form
        ingredients_text = request.POST.get('ingredients', '')
        available_ingredients = [ing.strip() for ing in ingredients_text.split(',') if ing.strip()]

        if available_ingredients:
            # Get recommendations
            from .engine import get_meals_from_ingredients
            recommendations = get_meals_from_ingredients(
                request.user, available_ingredients, profile, target_calories
            )

    # Get user's saved ingredients for suggestions
    from nutrition.models import UserIngredient
    saved_ingredients = UserIngredient.objects.filter(user=request.user)
    saved_ingredient_names = [ui.ingredient.name for ui in saved_ingredients]

    context = {
        "recommendations": recommendations,
        "available_ingredients": available_ingredients,
        "saved_ingredients": saved_ingredient_names,
        "target_calories": round(target_calories, 2),
    }

    return render(request, "ingredient_recommendations.html", context)


# =====================================================
# MANAGE USER INGREDIENTS VIEW
# =====================================================
@login_required
def manage_ingredients_view(request):
    """
    Allow users to manage their available ingredients
    """
    from nutrition.models import UserIngredient, Ingredient

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            ingredient_name = request.POST.get('ingredient_name')
            quantity = float(request.POST.get('quantity', 1))
            unit = request.POST.get('unit', 'pieces')

            try:
                ingredient = Ingredient.objects.get(name__iexact=ingredient_name.strip())
                UserIngredient.objects.get_or_create(
                    user=request.user,
                    ingredient=ingredient,
                    defaults={'quantity': quantity, 'unit': unit}
                )
            except Ingredient.DoesNotExist:
                # Could create new ingredient, but for now just skip
                pass

        elif action == 'remove':
            ingredient_id = request.POST.get('ingredient_id')
            UserIngredient.objects.filter(
                user=request.user,
                ingredient_id=ingredient_id
            ).delete()

        elif action == 'update':
            ingredient_id = request.POST.get('ingredient_id')
            quantity = float(request.POST.get('quantity', 0))

            UserIngredient.objects.filter(
                user=request.user,
                ingredient_id=ingredient_id
            ).update(quantity=quantity)

    # Get user's ingredients
    user_ingredients = UserIngredient.objects.filter(user=request.user).select_related('ingredient')

    # Get all available ingredients for suggestions
    all_ingredients = Ingredient.objects.all().order_by('category', 'name')

    context = {
        "user_ingredients": user_ingredients,
        "all_ingredients": all_ingredients,
    }

    return render(request, "manage_ingredients.html", context)


@login_required
def feedback_view(request, food_id, action):

    food = Food.objects.get(id=food_id)

    feedback, created = FoodFeedback.objects.get_or_create(
        user=request.user,
        food=food
    )

    if action == "accept":
        feedback.score += 1
    elif action == "reject":
        feedback.score -= 1

    feedback.save()

    return redirect("recommendations")


# =====================================================
# WEIGHT LOGGING VIEW
# =====================================================
@login_required
def log_weight_view(request):
    """
    Log user's weight entry
    """
    if request.method == 'POST':
        from accounts.progress_utils import log_weight
        
        weight = float(request.POST.get('weight'))
        notes = request.POST.get('notes', '')
        
        log_weight(request.user, weight, notes)
    
    return redirect('progress_dashboard')