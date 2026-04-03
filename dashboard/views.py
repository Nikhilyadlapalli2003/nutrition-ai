from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
from accounts.progress_utils import get_user_progress_summary, get_progress_goals, calculate_weight_change, calculate_calorie_adherence
from nutrition.utils import (
    calculate_bmr,
    calculate_tdee,
    adjust_calories_by_goal,
    calculate_macros
)
from nutrition.models import MealHistory
from datetime import datetime, timedelta


@login_required
def dashboard_view(request):

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)

    target_calories = adjust_calories_by_goal(tdee, profile.goal)
    macros = calculate_macros(target_calories)

    # Get today's calories consumed
    today = datetime.now().date()
    todays_meals = MealHistory.objects.filter(user=request.user, date=today)
    calories_consumed = sum(meal.calories for meal in todays_meals)

    # Calculate calorie percentage for donut chart
    if target_calories > 0:
        calorie_percentage = min(100, (calories_consumed / target_calories) * 100)
    else:
        calorie_percentage = 0

    # Get progress data for trends
    weight_change = calculate_weight_change(request.user, days_back=7)
    calorie_adherence = calculate_calorie_adherence(request.user, days_back=7)

    # Get today's meals for the strip
    todays_meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
    todays_meals_data = {}
    for meal_type in todays_meal_types:
        meals = todays_meals.filter(meal_type=meal_type)
        if meals.exists():
            meal = meals.first()  # Take the first one, or could aggregate
            todays_meals_data[meal_type] = {
                'name': meal.food.name,
                'calories': meal.calories,
                'completed': True
            }
        else:
            todays_meals_data[meal_type] = {
                'name': 'Not logged',
                'calories': 0,
                'completed': False
            }

    # Personalized greeting
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting_time = "Good morning"
    elif current_hour < 17:
        greeting_time = "Good afternoon"
    else:
        greeting_time = "Good evening"

    # Determine progress status
    if profile.goal == 'loss':
        if weight_change['weight_change'] and weight_change['weight_change'] < 0:
            progress_status = "you're on track for Weight Loss today"
        else:
            progress_status = "let's focus on your Weight Loss goal"
    elif profile.goal == 'gain':
        if weight_change['weight_change'] and weight_change['weight_change'] > 0:
            progress_status = "you're on track for Muscle Gain today"
        else:
            progress_status = "let's focus on your Muscle Gain goal"
    else:
        if calorie_adherence['adherence_percent'] >= 80:
            progress_status = "you're maintaining well today"
        else:
            progress_status = "let's keep up the good work"

    context = {
        "profile": profile,
        "bmr": bmr,
        "tdee": tdee,
        "target_calories": target_calories,
        "macros": macros,
        "calories_consumed": calories_consumed,
        "calories_remaining": max(0, target_calories - calories_consumed),
        "weight_change": weight_change,
        "calorie_adherence": calorie_adherence,
        "todays_meals": todays_meals_data,
        "greeting_time": greeting_time,
        "progress_status": progress_status,
    }

    return render(request, "dashboard.html", context)


# =====================================================
# 🔥 GOAL PROGRESS DASHBOARD
# =====================================================
@login_required
def progress_dashboard_view(request):
    """
    Comprehensive goal progress dashboard
    Tracks:
    - Weight loss/gain progress
    - Calorie adherence
    - Eating consistency & habits
    - Goal completion percentage
    """
    
    profile = UserProfile.objects.get(user=request.user)
    
    # Get progress summary
    progress_summary = get_user_progress_summary(request.user, days_back=30)
    progress_goals = get_progress_goals(request.user)
    
    # Calculate overall progress percentage
    overall_progress = 0
    if profile.goal == 'loss':
        # Weight loss goal
        weight_data = progress_summary['weight']
        goal_weight = progress_summary['goal_weight']
        
        if goal_weight['current_weight'] and goal_weight['goal_weight']:
            total_to_lose = goal_weight['current_weight'] - goal_weight['goal_weight']
            already_lost = abs(weight_data['weight_change']) if weight_data['weight_change'] else 0
            progress_pct = (already_lost / total_to_lose * 100) if total_to_lose > 0 else 0
            overall_progress = min(progress_pct, 100)
    
    elif profile.goal == 'gain':
        # Muscle gain goal
        weight_data = progress_summary['weight']
        goal_weight = progress_summary['goal_weight']
        
        if goal_weight['current_weight'] and goal_weight['goal_weight']:
            total_to_gain = goal_weight['goal_weight'] - goal_weight['current_weight']
            already_gained = weight_data['weight_change'] if weight_data['weight_change'] and weight_data['weight_change'] > 0 else 0
            progress_pct = (already_gained / total_to_gain * 100) if total_to_gain > 0 else 0
            overall_progress = min(progress_pct, 100)
    
    else:
        # Maintenance: calorie adherence
        overall_progress = progress_summary['calorie_adherence']['adherence_percent']
    
    # Package for template
    context = {
        'profile': profile,
        'progress_summary': progress_summary,
        'progress_goals': progress_goals,
        'overall_progress': round(overall_progress, 1),
        'weight': progress_summary['weight'],
        'goal_weight': progress_summary['goal_weight'],
        'calorie_adherence': progress_summary['calorie_adherence'],
        'eating_consistency': progress_summary['eating_consistency'],
        'weekly_habits': progress_summary['weekly_habits'],
    }
    
    return render(request, "progress_dashboard.html", context)