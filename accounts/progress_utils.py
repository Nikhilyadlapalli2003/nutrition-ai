"""
Utilities for tracking user progress: weight loss, muscle gain, calorie adherence, and habit tracking.
"""
from django.db.models import Q, Avg, Sum
from datetime import datetime, timedelta
from .models import WeightLog, HabitTrack
from nutrition.models import MealHistory
from nutrition.utils import calculate_bmr, calculate_tdee, adjust_calories_by_goal


# =====================================================
# WEIGHT TRACKING UTILITIES
# =====================================================

def log_weight(user, weight, notes=''):
    """
    Log user's weight for a given day
    
    Args:
        user: User object
        weight: Weight in kg
        notes: Optional notes
    
    Returns:
        WeightLog object
    """
    weight_log = WeightLog.objects.create(
        user=user,
        weight=weight,
        notes=notes
    )
    return weight_log


def get_weight_logs(user, days_back=30):
    """
    Get weight logs for the past N days
    
    Args:
        user: User object
        days_back: Number of days to retrieve
    
    Returns:
        QuerySet of WeightLog objects
    """
    start_date = datetime.now().date() - timedelta(days=days_back)
    return WeightLog.objects.filter(
        user=user,
        date__gte=start_date
    ).order_by('date')


def calculate_weight_change(user, days_back=30):
    """
    Calculate weight change over the past N days
    
    Args:
        user: User object
        days_back: Number of days to analyze
    
    Returns:
        dict with weight change metrics
    """
    logs = get_weight_logs(user, days_back)
    
    if logs.count() < 2:
        return {
            'start_weight': None,
            'current_weight': None,
            'weight_change': None,
            'weight_change_percent': None,
            'status': 'Insufficient data',
            'trend': 'N/A',
            'logs_count': logs.count()
        }
    
    start_weight = logs.first().weight
    current_weight = logs.last().weight
    weight_change = current_weight - start_weight
    weight_change_percent = (weight_change / start_weight) * 100 if start_weight != 0 else 0
    
    # Determine trend
    if weight_change < -0.5:
        trend = 'Losing weight ↓'
    elif weight_change > 0.5:
        trend = 'Gaining weight ↑'
    else:
        trend = 'Stable →'
    
    return {
        'start_weight': round(start_weight, 2),
        'current_weight': round(current_weight, 2),
        'weight_change': round(weight_change, 2),
        'weight_change_percent': round(weight_change_percent, 2),
        'status': 'Success' if weight_change < 0 else 'Monitor',
        'trend': trend,
        'logs_count': logs.count(),
        'days': days_back
    }


def get_goal_weight(user):
    """
    Get goal weight based on user's profile and goal
    
    Args:
        user: User object
    
    Returns:
        dict with goal weight calculation
    """
    from .models import UserProfile
    
    profile = UserProfile.objects.get(user=user)
    current_weight = profile.weight
    goal = profile.goal
    
    if goal == 'loss':
        goal_weight = current_weight * 0.90  # Assume 10% weight loss goal
        goal_description = "Weight loss goal: 10% reduction"
    elif goal == 'gain':
        goal_weight = current_weight * 1.10  # Assume 10% muscle gain
        goal_description = "Muscle gain goal: 10% increase"
    else:
        goal_weight = current_weight
        goal_description = "Maintenance goal: Current weight"
    
    return {
        'current_weight': round(current_weight, 2) if current_weight else None,
        'goal_weight': round(goal_weight, 2),
        'goal_description': goal_description,
        'goal_type': goal
    }


# =====================================================
# CALORIE ADHERENCE UTILITIES
# =====================================================

def calculate_calorie_adherence(user, days_back=7):
    """
    Calculate how well user adhered to calorie targets
    
    Args:
        user: User object
        days_back: Number of days to analyze
    
    Returns:
        dict with adherence metrics
    """
    from .models import UserProfile
    
    profile = UserProfile.objects.get(user=user)
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)
    target_calories = adjust_calories_by_goal(tdee, profile.goal)
    
    start_date = datetime.now().date() - timedelta(days=days_back)
    
    # Get daily totals
    daily_calories = MealHistory.objects.filter(
        user=user,
        date__gte=start_date
    ).values('date').annotate(
        total_calories=Sum('calories')
    ).order_by('date')
    
    if not daily_calories:
        return {
            'target_calories': target_calories,
            'average_calories': 0,
            'adherence_percent': 0,
            'days_tracked': 0,
            'in_range_days': 0,
            'status': 'No data'
        }
    
    total_calories = 0
    in_range_count = 0
    tolerance = target_calories * 0.10  # 10% tolerance
    
    for day in daily_calories:
        actual = day['total_calories']
        total_calories += actual
        
        # Check if within ±10%
        if abs(actual - target_calories) <= tolerance:
            in_range_count += 1
    
    avg_calories = total_calories / len(daily_calories) if daily_calories else 0
    adherence_percent = (in_range_count / len(daily_calories)) * 100 if daily_calories else 0
    
    return {
        'target_calories': round(target_calories, 2),
        'average_calories': round(avg_calories, 2),
        'adherence_percent': round(adherence_percent, 2),
        'days_tracked': len(daily_calories),
        'in_range_days': in_range_count,
        'status': 'Excellent' if adherence_percent >= 80 else 'Good' if adherence_percent >= 60 else 'Needs Improvement'
    }


# =====================================================
# HABIT TRACKING UTILITIES
# =====================================================

def log_meal_habit(user, meal_type, completed=True, adherence_score=100, notes=''):
    """
    Log meal adherence for a day
    
    Args:
        user: User object
        meal_type: 'breakfast', 'lunch', 'dinner', 'snack'
        completed: Whether user completed/followed meal plan
        adherence_score: 0-100 score of adherence
        notes: Optional notes
    
    Returns:
        HabitTrack object
    """
    habit_track, created = HabitTrack.objects.update_or_create(
        user=user,
        date=datetime.now().date(),
        meal_type=meal_type,
        defaults={
            'completed': completed,
            'adherence_score': adherence_score,
            'notes': notes
        }
    )
    return habit_track


def get_eating_consistency(user, days_back=30):
    """
    Calculate eating habit consistency over N days
    
    Args:
        user: User object
        days_back: Number of days to analyze
    
    Returns:
        dict with habit tracking metrics
    """
    start_date = datetime.now().date() - timedelta(days=days_back)
    
    habits = HabitTrack.objects.filter(
        user=user,
        date__gte=start_date
    )
    
    if not habits:
        return {
            'total_meals_tracked': 0,
            'completed_meals': 0,
            'completion_rate': 0,
            'average_adherence_score': 0,
            'consistency_streak': 0,
            'status': 'No data',
            'days_tracked': 0
        }
    
    completed = habits.filter(completed=True).count()
    total = habits.count()
    avg_score = habits.aggregate(Avg('adherence_score'))['adherence_score__avg'] or 0
    
    # Calculate consistency streak (consecutive days with all 4 meals)
    streak = calculate_consistency_streak(user)
    
    # Get unique dates tracked
    unique_dates = habits.values('date').distinct().count()
    
    return {
        'total_meals_tracked': total,
        'completed_meals': completed,
        'completion_rate': round((completed / total) * 100, 2) if total > 0 else 0,
        'average_adherence_score': round(avg_score, 2),
        'consistency_streak': streak,
        'status': 'Excellent' if (completed/total)*100 >= 80 else 'Good' if (completed/total)*100 >= 60 else 'Needs Improvement' if total > 0 else 'No data',
        'days_tracked': unique_dates
    }


def calculate_consistency_streak(user):
    """
    Calculate consecutive days of perfect meal adherence
    
    Args:
        user: User object
    
    Returns:
        int: Number of consecutive days with all 4 meals completed
    """
    streak = 0
    current_date = datetime.now().date()
    
    while True:
        # Check if all 4 meals completed on this date
        meals_on_date = HabitTrack.objects.filter(
            user=user,
            date=current_date,
            completed=True
        ).count()
        
        if meals_on_date == 4:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak


def get_weekly_habit_summary(user):
    """
    Get habit tracking summary for the past week
    
    Args:
        user: User object
    
    Returns:
        dict with daily breakdown for the week
    """
    start_date = datetime.now().date() - timedelta(days=7)
    
    daily_summary = {}
    for i in range(7):
        date = start_date + timedelta(days=i)
        day_name = date.strftime('%A')
        
        habits = HabitTrack.objects.filter(
            user=user,
            date=date
        )
        
        completed = habits.filter(completed=True).count()
        total = habits.count()
        
        daily_summary[day_name] = {
            'date': date,
            'completed': completed,
            'total': total,
            'percentage': round((completed/total)*100, 1) if total > 0 else 0,
            'meals': []
        }
        
        # Add meal details
        for habit in habits.order_by('meal_type'):
            daily_summary[day_name]['meals'].append({
                'meal_type': habit.get_meal_type_display(),
                'completed': habit.completed,
                'score': habit.adherence_score
            })
    
    return daily_summary


# =====================================================
# GOAL PROGRESS SUMMARY
# =====================================================

def get_user_progress_summary(user, days_back=30):
    """
    Get comprehensive progress summary across all metrics
    
    Args:
        user: User object
        days_back: Number of days to analyze
    
    Returns:
        dict with all progress metrics
    """
    return {
        'weight': calculate_weight_change(user, days_back),
        'goal_weight': get_goal_weight(user),
        'calorie_adherence': calculate_calorie_adherence(user, days_back),
        'eating_consistency': get_eating_consistency(user, days_back),
        'weekly_habits': get_weekly_habit_summary(user),
        'days_analyzed': days_back
    }


def get_progress_goals(user):
    """
    Get user's progress goals and current status
    
    Args:
        user: User object
    
    Returns:
        dict with goal tracking information
    """
    from .models import UserProfile
    
    profile = UserProfile.objects.get(user=user)
    weight_change = calculate_weight_change(user, 30)
    calorie_adhere = calculate_calorie_adherence(user, 30)
    consistency = get_eating_consistency(user, 30)
    
    goals = {
        'primary_goal': profile.goal,
        'goal_description': dict(UserProfile.GOAL_CHOICES).get(profile.goal),
        'targets': {
            'weight_loss': {
                'enabled': profile.goal == 'loss',
                'target': round(profile.weight * 0.90, 2) if profile.weight else None,
                'current': weight_change['current_weight'],
                'progress': weight_change['weight_change'],
                'status': weight_change['status'] if weight_change['status'] else 'Not applicable'
            },
            'muscle_gain': {
                'enabled': profile.goal == 'gain',
                'target': round(profile.weight * 1.10, 2) if profile.weight else None,
                'current': weight_change['current_weight'],
                'progress': weight_change['weight_change'],
                'status': 'Gaining' if weight_change['weight_change'] and weight_change['weight_change'] > 0 else 'Monitor'
            },
            'calorie_adherence': {
                'target_calories': calorie_adhere['target_calories'],
                'average_calories': calorie_adhere['average_calories'],
                'adherence_percent': calorie_adhere['adherence_percent'],
                'status': calorie_adhere['status']
            },
            'meal_consistency': {
                'completion_rate': consistency['completion_rate'],
                'consistency_streak': consistency['consistency_streak'],
                'average_score': consistency['average_adherence_score'],
                'status': consistency['status']
            }
        }
    }
    
    return goals
