# Weight Tracking, Habit Tracking & Goal Progress Dashboard

This document explains the weight tracking, habit tracking, and goal progress features in the Nutrition AI system.

## Overview

The system now includes three comprehensive tracking features:
1. **Weight Tracking** - Log and monitor weight changes over time
2. **Habit Tracking** - Track eating consistency and meal adherence
3. **Goal Progress Dashboard** - Visual progress tracking for weight loss, muscle gain, and calorie adherence

---

## Database Schema

### WeightLog Model

```python
class WeightLog(models.Model):
    user = ForeignKey(User)
    weight = FloatField()  # in kg
    date = DateField(auto_now_add=True)
    notes = TextField()  # Optional notes
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Ordered by date descending
    # Indexed for quick lookup by user and date
```

### HabitTrack Model

```python
class HabitTrack(models.Model):
    MEAL_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack/Hydration'),
    ]
    
    user = ForeignKey(User)
    date = DateField()
    meal_type = CharField(choices=MEAL_CHOICES)
    completed = BooleanField()  # Did user follow meal plan?
    adherence_score = IntegerField(0-100)  # How closely followed recommendations
    notes = TextField()  # Optional notes
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Unique together: (user, date, meal_type)
    # Ordered by date descending
```

---

## Weight Tracking

### Features

- **Log daily weights** with optional notes
- **Track weight trends** (losing, gaining, stable)
- **Calculate weight change** over custom time periods
- **Set goals** based on user's fitness objective
- **Visual progress** in dashboard

### Usage

#### Logging Weight

```python
from accounts.progress_utils import log_weight

# Log user's weight
log_weight(user, weight=75.5, notes="morning, after workout")
```

#### Retrieving Weight Logs

```python
from accounts.progress_utils import get_weight_logs

# Get weight logs for past 30 days
logs = get_weight_logs(user, days_back=30)

# Returns QuerySet ordered by date
for log in logs:
    print(f"{log.date}: {log.weight}kg - {log.notes}")
```

#### Calculating Weight Change

```python
from accounts.progress_utils import calculate_weight_change

# Get weight change summary
change = calculate_weight_change(user, days_back=30)

# Returns dict:
{
    'start_weight': 80.0,
    'current_weight': 77.5,
    'weight_change': -2.5,  # kg
    'weight_change_percent': -3.13,  # %
    'status': 'Success' or 'Monitor',
    'trend': 'Losing weight ↓' or 'Gaining weight ↑' or 'Stable →',
    'logs_count': 30,
    'days': 30
}
```

#### Getting Goal Weight

```python
from accounts.progress_utils import get_goal_weight

goal_info = get_goal_weight(user)

# Returns dict:
{
    'current_weight': 80.0,
    'goal_weight': 72.0,  # 10% reduction for loss goal
    'goal_description': 'Weight loss goal: 10% reduction',
    'goal_type': 'loss'
}
```

### Weight Progress in Dashboard

The progress dashboard displays:
- Starting weight
- Current weight
- Total change (in kg and %)
- Weight trend analysis
- Weight change status
- Button to log new weight entry

---

## Habit Tracking

### Features

- **Track meal completion** (yes/no for each meal)
- **Measure adherence score** (0-100%) for each meal
- **Calculate completion rates** across time periods
- **Build consistency streaks** (consecutive perfect days)
- **Weekly habit summary** with daily breakdown

### Usage

#### Logging Meal Habit

```python
from accounts.progress_utils import log_meal_habit

# Log meal adherence
habit = log_meal_habit(
    user=user,
    meal_type='breakfast',  # 'breakfast', 'lunch', 'dinner', 'snack'
    completed=True,  # Did user follow the plan?
    adherence_score=95,  # How closely (0-100)?
    notes='Had the recommended oatmeal breakfast'
)

# Automatically updates if already logged for that meal today
```

#### Getting Eating Consistency

```python
from accounts.progress_utils import get_eating_consistency

consistency = get_eating_consistency(user, days_back=30)

# Returns dict:
{
    'total_meals_tracked': 120,
    'completed_meals': 90,
    'completion_rate': 75.0,  # %
    'average_adherence_score': 85.5,  # %
    'consistency_streak': 5,  # consecutive perfect days
    'status': 'Good',  # 'Excellent' (>=80%), 'Good' (>=60%), 'Needs Improvement'
    'days_tracked': 30
}
```

#### Weekly Habit Summary

```python
from accounts.progress_utils import get_weekly_habit_summary

weekly = get_weekly_habit_summary(user)

# Returns dict:
{
    'Monday': {
        'date': date(2026, 3, 1),
        'completed': 3,  # meals completed
        'total': 4,  # meals tracked
        'percentage': 75.0,
        'meals': [
            {'meal_type': 'Breakfast', 'completed': True, 'score': 100},
            {'meal_type': 'Lunch', 'completed': True, 'score': 90},
            {'meal_type': 'Dinner', 'completed': True, 'score': 100},
            {'meal_type': 'Snack', 'completed': False, 'score': 0}
        ]
    },
    # ... other days
}
```

#### Calculating Consistency Streak

```python
from accounts.progress_utils import calculate_consistency_streak

streak = calculate_consistency_streak(user)
# Returns: int (number of consecutive perfect days)

# A "perfect day" = all 4 meals completed
```

### Habit Tracking in Dashboard

The dashboard displays:
- Weekly meal adherence grid (7-day view)
- Completion rate percentage
- Average adherence score
- Current consistency streak
- Daily meal breakdown with completion status

---

## Calorie Adherence

### Features

- **Calculate daily target calories** based on BMR, TDEE, and goal
- **Compare actual vs target** calorie consumption
- **Measure adherence percentage** (meals within ±10% of target)
- **Track adherence trends** over time

### Usage

```python
from accounts.progress_utils import calculate_calorie_adherence

adherence = calculate_calorie_adherence(user, days_back=30)

# Returns dict:
{
    'target_calories': 2000.0,  # Daily target
    'average_calories': 1950.0,  # What user actually consumed
    'adherence_percent': 85.7,  # % of days within ±10% of target
    'days_tracked': 7,
    'in_range_days': 6,  # Days within tolerance
    'status': 'Excellent'  # Based on adherence %
}
```

---

## Goal Progress Dashboard

### URL & View

```python
# Access at: /dashboard/progress/
# View: dashboard.progress_dashboard_view
```

### Displayed Metrics

#### Overall Progress
- Single progress bar showing overall goal completion
- Percentage completed toward goal
- Different calculations for different goal types:
  - **Weight Loss**: (Weight lost) / (Total to lose) × 100
  - **Muscle Gain**: (Weight gained) / (Total to gain) × 100
  - **Maintenance**: Calorie adherence %

#### Weight Progress Card
- Current weight (kg)
- Goal weight (kg)
- Total weight change
- Weight trend

#### Calorie Adherence Card
- Daily target calories
- Average calories consumed
- Adherence percentage
- Status (Excellent/Good/Needs Improvement)

#### Meal Consistency Card
- Meal completion rate
- Number of meals tracked
- Consistency streak (consecutive perfect days)
- Average adherence score

#### Weight Section
- Starting weight
- Current weight
- Total change (kg and %)
- Trend analysis
- Button to log new weight

#### Weekly Habit Grid
- 7-day view of meal completion
- Color-coded by adherence level:
  - Green (high): ≥80%
  - Yellow (medium): 50-79%
  - Red (low): <50%
- Quick view of which meals were completed each day

#### Goal Targets Summary
- Goal type (weight loss/gain/maintenance)
- Current and target values
- Progress toward goal
- Status indicator

### Example API Usage

```python
from accounts.progress_utils import get_user_progress_summary, get_progress_goals

# Get complete summary
summary = get_user_progress_summary(user, days_back=30)

# Returns:
{
    'weight': {...},  # Weight change data
    'goal_weight': {...},  # Goal information
    'calorie_adherence': {...},  # Calorie tracking
    'eating_consistency': {...},  # Habit tracking
    'weekly_habits': {...},  # Weekly breakdown
    'days_analyzed': 30
}

# Get goal-specific information
goals = get_progress_goals(user)

# Returns:
{
    'primary_goal': 'loss',
    'goal_description': 'Weight Loss',
    'targets': {
        'weight_loss': {
            'enabled': True,
            'target': 75.0,
            'current': 80.0,
            'progress': -2.0,
            'status': 'Success'
        },
        'muscle_gain': {...},
        'calorie_adherence': {...},
        'meal_consistency': {...}
    }
}
```

---

## Progress Dashboard Template

Located at: `templates/progress_dashboard.html`

### Features

- **Green theme** with consistent styling
- **Responsive design** (mobile-friendly)
- **Interactive weight logging form** (hidden/shown on button click)
- **Color-coded metrics**:
  - Green: Healthy/On track
  - Yellow: Warning/Needs attention
  - Red: Alert/Exceeds limits
- **Charts** (using Chart.js via weekly grid)
- **Quick action buttons** to navigate to other sections

### Customization

```html
<!-- To change primary color, modify CSS variable -->
<style>
:root {
    --success: #10b981;  /* Green */
    --warning: #f59e0b;  /* Amber */
    --alert: #ef4444;    /* Red */
}
</style>
```

---

## Admin Interface

The models are automatically registered with Django admin:

```python
# Access at: /admin/accounts/weightlog/
# Access at: /admin/accounts/habittrack/
```

Admin features:
- List view with filtering by date and user
- Search by username
- Inline editing
- Date range filtering

---

## Integration with Existing Features

### Meal History → Habit Tracking

When meal recommendations are generated, users can log habit adherence:

```python
# In user profile
profile.goal = 'loss'

# Generate meal plan
meal_plan = structured_meal_plan(profile, target_calories, user)

# Later, user logs how well they followed it
log_meal_habit(user, 'breakfast', completed=True, adherence_score=95)

# System tracks this for consistency metrics
```

### UserProfile Integration

The weight field in UserProfile:
```python
profile.weight = 80.0  # Current weight from profile

# Progress dashboard uses this as baseline
goal_weight = profile.weight * 0.90  # 10% reduction for loss goal
```

---

## Usage Examples

### Complete Progress Tracking Workflow

```python
from accounts.progress_utils import *
from django.contrib.auth.models import User

user = User.objects.get(username='john')

# 1. Log today's weight
log_weight(user, 78.5, "morning weight")

# 2. Log meal adherence
log_meal_habit(user, 'breakfast', completed=True, adherence_score=100)
log_meal_habit(user, 'lunch', completed=True, adherence_score=90)
log_meal_habit(user, 'dinner', completed=True, adherence_score=95)
log_meal_habit(user, 'snack', completed=False, adherence_score=0)

# 3. Check progress
weight_change = calculate_weight_change(user, 30)
consistency = get_eating_consistency(user, 30)
adherence = calculate_calorie_adherence(user, 30)

# 4. View dashboard
summary = get_user_progress_summary(user, 30)
goals = get_progress_goals(user)

print(f"Weight: {weight_change['current_weight']}kg (trend: {weight_change['trend']})")
print(f"Consistency: {consistency['completion_rate']}%")
print(f"Calorie adherence: {adherence['adherence_percent']}%")
```

---

## Database Queries

### Fast weight lookups
```python
# Get all weight logs for a user in date range
WeightLog.objects.filter(
    user=user,
    date__gte=start_date,
    date__lte=end_date
).order_by('date')
```

### Fast habit lookups
```python
# Get all meal logs for a user
HabitTrack.objects.filter(
    user=user,
    date=date
).order_by('meal_type')

# Get specific meal adherence
HabitTrack.objects.get(
    user=user,
    date=date,
    meal_type='breakfast'
)
```

---

## Performance Considerations

- **Indexes** on (user, date) for fast filtering
- **Unique constraints** prevent duplicate habits for same user/date/meal
- **Aggregate queries** use Django ORM for efficiency
- **30-day lookback** balances data completeness with performance

---

## Future Enhancements

1. **Photo-based weight tracking** - Upload photos for before/after
2. **Fitness metrics** - Track body measurements, workouts
3. **Goal adjustments** - Dynamic goal recalculation
4. **Streak badges** - Achievements for consistency milestones
5. **Trend predictions** - Estimate when goals will be reached
6. **Export reports** - PDF/CSV progress reports
7. **Notifications** - Alerts for streak breaks or goal achievement
8. **Comparison view** - Compare this month vs last month
9. **Habit templates** - Weekly goal patterns
10. **Social features** - Share progress with accountability partners

---

## Support & Troubleshooting

### Weight logs not showing
- Ensure logs are created with `WeightLog.objects.create()` or `log_weight()`
- Check database has the WeightLog table (migration applied)
- Verify date is not in the future

### Habit tracking not recording
- Ensure `log_meal_habit()` is called with user, meal_type, and other params
- Check that meal_type is one of: 'breakfast', 'lunch', 'dinner', 'snack'
- Unique constraint only allows one entry per user/date/meal_type

### Progress dashboard not loading
- Verify `progress_dashboard_view` is properly registered in URLs
- Check template file exists at `templates/progress_dashboard.html`
- Ensure user is authenticated (`@login_required` decorator)

---

## API Reference

### Weight Tracking
- `log_weight(user, weight, notes='')`
- `get_weight_logs(user, days_back=30)`
- `calculate_weight_change(user, days_back=30)`
- `get_goal_weight(user)`

### Calorie Adherence
- `calculate_calorie_adherence(user, days_back=7)`

### Habit Tracking
- `log_meal_habit(user, meal_type, completed, adherence_score, notes='')`
- `get_eating_consistency(user, days_back=30)`
- `calculate_consistency_streak(user)`
- `get_weekly_habit_summary(user)`

### Progress Summary
- `get_user_progress_summary(user, days_back=30)`
- `get_progress_goals(user)`

---

## Related Features

- **Meal Recommendations** - Recommended daily meals
- **Medical Conditions** - Health-based meal filtering
- **Allergy Tracking** - Allergen management
- **Sodium/Sugar Alerts** - Nutrient limits
- **User Profile** - User's fitness goals and preferences
