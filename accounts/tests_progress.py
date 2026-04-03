"""
Tests for weight tracking, habit tracking, and goal progress features.

Usage:
    python manage.py test accounts.tests_progress
"""

from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile, WeightLog, HabitTrack
from accounts.progress_utils import (
    log_weight,
    get_weight_logs,
    calculate_weight_change,
    get_goal_weight,
    calculate_calorie_adherence,
    log_meal_habit,
    get_eating_consistency,
    get_user_progress_summary,
    get_progress_goals
)
from nutrition.models import MealHistory, Food
from datetime import datetime, timedelta


class TestWeightTracking(TestCase):
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
        self.profile.weight = 80
        self.profile.save()
    
    def test_log_weight(self):
        """Test logging weight entry"""
        log = log_weight(self.user, 79.5, "morning weight")
        
        assert log.weight == 79.5
        assert log.notes == "morning weight"
        assert log.user == self.user
    
    def test_get_weight_logs(self):
        """Test retrieving weight logs"""
        log_weight(self.user, 80, "")
        log_weight(self.user, 79.5, "")
        log_weight(self.user, 79, "")
        
        logs = get_weight_logs(self.user, 30)
        assert logs.count() == 3
    
    def test_calculate_weight_change(self):
        """Test weight change calculation"""
        log_weight(self.user, 80, "")
        log_weight(self.user, 79, "")
        
        change = calculate_weight_change(self.user, 30)
        
        assert change['start_weight'] == 80
        assert change['current_weight'] == 79
        assert change['weight_change'] == -1
        assert change['trend'] == 'Losing weight ↓'
    
    def test_get_goal_weight_loss(self):
        """Test goal weight for weight loss goal"""
        self.profile.goal = 'loss'
        self.profile.weight = 100
        self.profile.save()
        
        goal_info = get_goal_weight(self.user)
        
        assert goal_info['current_weight'] == 100
        assert goal_info['goal_weight'] == 90  # 10% reduction
    
    def test_get_goal_weight_gain(self):
        """Test goal weight for muscle gain goal"""
        self.profile.goal = 'gain'
        self.profile.weight = 70
        self.profile.save()
        
        goal_info = get_goal_weight(self.user)
        
        assert goal_info['current_weight'] == 70
        assert goal_info['goal_weight'] == 77  # 10% increase


class TestHabitTracking(TestCase):
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_log_meal_habit(self):
        """Test logging meal completion"""
        habit = log_meal_habit(
            self.user,
            'breakfast',
            completed=True,
            adherence_score=95,
            notes='Great breakfast'
        )
        
        assert habit.meal_type == 'breakfast'
        assert habit.completed == True
        assert habit.adherence_score == 95
    
    def test_log_meal_habit_update(self):
        """Test updating existing meal habit"""
        habit1 = log_meal_habit(
            self.user,
            'breakfast',
            completed=False,
            adherence_score=50
        )
        
        habit2 = log_meal_habit(
            self.user,
            'breakfast',
            completed=True,
            adherence_score=90
        )
        
        # Should update, not create new
        assert HabitTrack.objects.filter(
            user=self.user,
            date=datetime.now().date()
        ).count() == 1
        
        habit1.refresh_from_db()
        assert habit1.completed == True
        assert habit1.adherence_score == 90
    
    def test_get_eating_consistency(self):
        """Test eating consistency calculation"""
        today = datetime.now().date()
        
        # Log 4 meals for today
        log_meal_habit(self.user, 'breakfast', completed=True, adherence_score=100)
        log_meal_habit(self.user, 'lunch', completed=True, adherence_score=100)
        log_meal_habit(self.user, 'dinner', completed=True, adherence_score=90)
        log_meal_habit(self.user, 'snack', completed=False, adherence_score=50)
        
        consistency = get_eating_consistency(self.user, 30)
        
        assert consistency['total_meals_tracked'] == 4
        assert consistency['completed_meals'] == 3
        assert consistency['completion_rate'] == 75
        assert consistency['average_adherence_score'] == 85
    
    def test_consistency_streak(self):
        """Test consistency streak calculation"""
        from accounts.progress_utils import calculate_consistency_streak
        
        today = datetime.now().date()
        
        # Log perfect days (all 4 meals) for 3 days
        for day_offset in [0, -1, -2]:
            current_date = today + timedelta(days=day_offset)
            
            HabitTrack.objects.create(
                user=self.user,
                date=current_date,
                meal_type='breakfast',
                completed=True,
                adherence_score=100
            )
            HabitTrack.objects.create(
                user=self.user,
                date=current_date,
                meal_type='lunch',
                completed=True,
                adherence_score=100
            )
            HabitTrack.objects.create(
                user=self.user,
                date=current_date,
                meal_type='dinner',
                completed=True,
                adherence_score=100
            )
            HabitTrack.objects.create(
                user=self.user,
                date=current_date,
                meal_type='snack',
                completed=True,
                adherence_score=100
            )
        
        streak = calculate_consistency_streak(self.user)
        assert streak == 3


class TestCalorieAdherence(TestCase):
    
    def setUp(self):
        """Create test user and food"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
        self.profile.goal = 'maintain'
        self.profile.activity_level = 'moderate'
        self.profile.save()
        
        # Create a test food
        self.food = Food.objects.create(
            name='Test Meal',
            category='lunch',
            diet_type='veg',
            calories=500,
            protein=20,
            carbs=60,
            fats=15
        )
    
    def test_calculate_calorie_adherence(self):
        """Test calorie adherence calculation"""
        # Create meal history entries
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            MealHistory.objects.create(
                user=self.user,
                food=self.food,
                meal_type='lunch',
                date=date,
                calories=500,
                protein=20,
                carbs=60,
                fats=15
            )
        
        adherence = calculate_calorie_adherence(self.user, 7)
        
        assert adherence['days_tracked'] == 7
        assert adherence['average_calories'] > 0


class TestProgressSummary(TestCase):
    
    def setUp(self):
        """Create test user with complete profile"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
        self.profile.weight = 80
        self.profile.goal = 'loss'
        self.profile.activity_level = 'moderate'
        self.profile.save()
    
    def test_get_user_progress_summary(self):
        """Test getting complete progress summary"""
        # Add weight logs
        log_weight(self.user, 80, "")
        log_weight(self.user, 79, "")
        
        # Add meal habits
        log_meal_habit(self.user, 'breakfast', completed=True)
        
        summary = get_user_progress_summary(self.user, 30)
        
        assert 'weight' in summary
        assert 'goal_weight' in summary
        assert 'calorie_adherence' in summary
        assert 'eating_consistency' in summary
        assert summary['days_analyzed'] == 30
    
    def test_get_progress_goals(self):
        """Test getting progress goals"""
        # Add weight logs
        log_weight(self.user, 80, "")
        log_weight(self.user, 79, "")
        
        goals = get_progress_goals(self.user)
        
        assert goals['primary_goal'] == 'loss'
        assert 'targets' in goals
        assert 'weight_loss' in goals['targets']
        assert 'calorie_adherence' in goals['targets']


# Run tests with: python manage.py test accounts.tests_progress
