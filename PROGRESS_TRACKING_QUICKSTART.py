"""
Quick start guide for weight tracking, habit tracking, and progress dashboard features.
"""

# =====================================================
# FEATURE 1: WEIGHT TRACKING
# =====================================================

from accounts.progress_utils import (
    log_weight,
    get_weight_logs,
    calculate_weight_change,
    get_goal_weight
)
from django.contrib.auth.models import User

# Get user
user = User.objects.get(username='john')

# === Log weight ===
log_weight(user, weight=75.5, notes="morning, after workout")
log_weight(user, weight=75.2, notes="evening")

# === Get weight history ===
logs = get_weight_logs(user, days_back=30)
for log in logs:
    print(f"{log.date}: {log.weight}kg")

# === Calculate progress ===
change = calculate_weight_change(user, days_back=30)
print(f"Weight change: {change['weight_change']}kg ({change['weight_change_percent']}%)")
print(f"Trend: {change['trend']}")
print(f"Status: {change['status']}")

# === Check goal ===
goal = get_goal_weight(user)
print(f"Goal weight: {goal['goal_weight']}kg")
print(f"Goal type: {goal['goal_type']}")


# =====================================================
# FEATURE 2: HABIT TRACKING
# =====================================================

from accounts.progress_utils import (
    log_meal_habit,
    get_eating_consistency,
    get_weekly_habit_summary,
    calculate_consistency_streak
)

# === Log meal adherence ===
log_meal_habit(
    user, 
    meal_type='breakfast',
    completed=True,
    adherence_score=95,
    notes="Had the recommended oatmeal"
)

log_meal_habit(user, 'lunch', completed=True, adherence_score=85)
log_meal_habit(user, 'dinner', completed=True, adherence_score=90)
log_meal_habit(user, 'snack', completed=False, adherence_score=0)

# === Get consistency metrics ===
consistency = get_eating_consistency(user, days_back=30)
print(f"Completion rate: {consistency['completion_rate']}%")
print(f"Average score: {consistency['average_adherence_score']}%")
print(f"Streak: {consistency['consistency_streak']} days")
print(f"Status: {consistency['status']}")

# === Get weekly breakdown ===
weekly = get_weekly_habit_summary(user)
for day_name, day_data in weekly.items():
    print(f"{day_name}: {day_data['percentage']}%")
    for meal in day_data['meals']:
        status = "✓" if meal['completed'] else "✗"
        print(f"  {status} {meal['meal_type']} ({meal['score']}%)")

# === Check consistency streak ===
streak = calculate_consistency_streak(user)
print(f"Current streak: {streak} consecutive perfect days")


# =====================================================
# FEATURE 3: CALORIE ADHERENCE
# =====================================================

from accounts.progress_utils import calculate_calorie_adherence

# === Calculate adherence ===
adherence = calculate_calorie_adherence(user, days_back=30)
print(f"Target: {adherence['target_calories']} kcal")
print(f"Average: {adherence['average_calories']} kcal")
print(f"Adherence: {adherence['adherence_percent']}%")
print(f"Status: {adherence['status']}")
print(f"Days in range: {adherence['in_range_days']} / {adherence['days_tracked']}")


# =====================================================
# FEATURE 4: COMPLETE PROGRESS SUMMARY
# =====================================================

from accounts.progress_utils import (
    get_user_progress_summary,
    get_progress_goals
)

# === Get everything at once ===
summary = get_user_progress_summary(user, days_back=30)

# Weight data
print("=== WEIGHT ===")
print(f"Current: {summary['weight']['current_weight']}kg")
print(f"Change: {summary['weight']['weight_change']}kg")
print(f"Trend: {summary['weight']['trend']}")

# Goal data
print("\n=== GOAL ===")
print(f"Current: {summary['goal_weight']['current_weight']}kg")
print(f"Target: {summary['goal_weight']['goal_weight']}kg")

# Calorie data
print("\n=== CALORIE ADHERENCE ===")
print(f"Target: {summary['calorie_adherence']['target_calories']}kcal")
print(f"Average: {summary['calorie_adherence']['average_calories']}kcal")
print(f"Adherence: {summary['calorie_adherence']['adherence_percent']}%")

# Consistency data
print("\n=== MEAL CONSISTENCY ===")
print(f"Completion: {summary['eating_consistency']['completion_rate']}%")
print(f"Avg Score: {summary['eating_consistency']['average_adherence_score']}%")
print(f"Streak: {summary['eating_consistency']['consistency_streak']} days")

# === Get goal-specific info ===
goals = get_progress_goals(user)
print(f"\n=== GOAL TYPE ===")
print(f"Primary: {goals['goal_description']}")

if goals['primary_goal'] == 'loss':
    loss = goals['targets']['weight_loss']
    print(f"Target weight: {loss['target']}kg")
    print(f"Progress: {loss['progress']}kg")
    print(f"Status: {loss['status']}")


# =====================================================
# FEATURE 5: VIEWING PROGRESS DASHBOARD
# =====================================================

# The progress dashboard is accessible at:
# http://yoursite.com/dashboard/progress/

# It automatically displays all progress data:
# - Overall progress bar
# - Weight tracking section
# - Weekly habit grid  
# - Calorie adherence metrics
# - Goal targets
# - Quick action buttons

# Logged-in users can:
# 1. Click "View Progress" in meal recommendations
# 2. Click "Progress" in navigation bar
# 3. Log weight directly from the dashboard
# 4. See all metrics in real-time


# =====================================================
# ADMIN INTERFACE
# =====================================================

# Django admin integration at: /admin/accounts/weightlog/ and /admin/accounts/habittrack/

# Admins can:
# 1. View all weight logs
# 2. Filter by user and date
# 3. Edit entries
# 4. View all habit tracks
# 5. Search by username
# 6. Filter by meal type and date


# =====================================================
# TESTING
# =====================================================

# Run tests with:
# python manage.py test accounts.tests_progress

# Tests cover:
# - Weight logging and calculations
# - Habit tracking and consistency
# - Calorie adherence calculations
# - Progress summaries
# - Goal progress tracking


# =====================================================
# INTEGRATION WITH MEAL RECOMMENDATIONS
# =====================================================

# After user receives meal recommendations:
from nutrition.models import MealHistory

# System automatically logs meal history
meal_history = MealHistory.objects.filter(
    user=user,
    date='2026-03-09'
)

# User can log how well they followed the plan
for meal in meal_history:
    log_meal_habit(
        user,
        meal_type=meal.meal_type,
        completed=True,
        adherence_score=90,
        notes=f"Had {meal.food.name}"
    )


# =====================================================
# CUSTOMIZING HEALTH LIMITS
# =====================================================

from accounts.models import UserProfile

profile = UserProfile.objects.get(user=user)

# Update sodium limit
profile.sodium_limit_mg = 2000  # Stricter limit

# Update sugar limit
profile.sugar_limit_g = 25  # Stricter than default 50g

# Set medical condition
profile.medical_conditions = 'diabetes'

# Save changes
profile.save()

# These limits are used in meal recommendations and alerts


# =====================================================
# WEIGHT LOGGING IN VIEWS
# =====================================================

# In your view, handle weight logging:

from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from accounts.progress_utils import log_weight

@login_required
@require_http_methods(["POST"])
def log_weight_view(request):
    weight = float(request.POST.get('weight'))
    notes = request.POST.get('notes', '')
    
    log_weight(request.user, weight, notes)
    
    return redirect('progress_dashboard')


# =====================================================
# HABIT LOGGING IN VIEWS
# =====================================================

# Log meal adherence after user rates meal:

from accounts.progress_utils import log_meal_habit

def log_meal_adherence(user, meal_type, was_completed, rating_score):
    """
    Log how well user followed the meal plan
    """
    log_meal_habit(
        user=user,
        meal_type=meal_type,
        completed=was_completed,
        adherence_score=rating_score,
        notes=f"User rating: {rating_score}%"
    )
