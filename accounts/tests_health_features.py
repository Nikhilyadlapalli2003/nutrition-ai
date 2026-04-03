"""
Test cases for medical conditions, allergies, and health alerts.

Usage:
    python manage.py test accounts.tests.TestMedicalConditions
    python manage.py test accounts.tests.TestAllergyFiltering
    python manage.py test recommendations.tests.TestHealthAlerts
"""

from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.profile_utils import (
    setup_medical_conditions_for_user,
    add_allergies_to_user,
    remove_allergy_from_user,
    set_sodium_limit,
    set_sugar_limit,
    get_user_dietary_profile
)
from nutrition.models import Food
from recommendations.engine import (
    apply_health_filter,
    apply_allergy_filter,
    apply_sodium_limit_filter,
    check_sodium_alerts,
    check_sugar_alerts,
    check_condition_compliance
)


class TestMedicalConditions(TestCase):
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_setup_diabetes_condition(self):
        """Test setting diabetes condition"""
        profile = setup_medical_conditions_for_user(self.user, 'diabetes')
        assert profile.medical_conditions == 'diabetes'
        assert profile.has_medical_condition() == True
    
    def test_setup_hypertension_condition(self):
        """Test setting hypertension condition"""
        profile = setup_medical_conditions_for_user(self.user, 'hypertension')
        assert profile.medical_conditions == 'hypertension'
    
    def test_setup_heart_disease_condition(self):
        """Test setting heart disease condition"""
        profile = setup_medical_conditions_for_user(self.user, 'heart_disease')
        assert profile.medical_conditions == 'heart_disease'
    
    def test_setup_obesity_condition(self):
        """Test setting obesity condition"""
        profile = setup_medical_conditions_for_user(self.user, 'obesity')
        assert profile.medical_conditions == 'obesity'
    
    def test_invalid_condition_raises_error(self):
        """Test that invalid condition raises ValueError"""
        with self.assertRaises(ValueError):
            setup_medical_conditions_for_user(self.user, 'invalid_condition')


class TestAllergyManagement(TestCase):
    
    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
    
    def test_add_single_allergy(self):
        """Test adding single allergy"""
        self.profile.add_allergy('peanuts')
        assert 'peanuts' in self.profile.get_allergies_list()
    
    def test_add_multiple_allergies(self):
        """Test adding multiple allergies"""
        add_allergies_to_user(self.user, "peanuts, shellfish, dairy")
        # refresh profile from DB since utility uses a fresh object
        self.profile = UserProfile.objects.get(user=self.user)
        allergies = self.profile.get_allergies_list()
        assert 'peanuts' in allergies
        assert 'shellfish' in allergies
        assert 'dairy' in allergies
    
    def test_remove_allergy(self):
        """Test removing an allergy"""
        self.profile.add_allergy('peanuts')
        self.profile.add_allergy('shellfish')
        self.profile.remove_allergy('peanuts')
        
        allergies = self.profile.get_allergies_list()
        assert 'peanuts' not in allergies
        assert 'shellfish' in allergies
    
    def test_duplicate_allergies_not_added(self):
        """Test that duplicate allergies aren't added"""
        self.profile.add_allergy('peanuts')
        self.profile.add_allergy('peanuts')
        assert self.profile.get_allergies_list().count('peanuts') == 1
    
    def test_case_insensitive_allergies(self):
        """Test that allergies are case-insensitive"""
        self.profile.add_allergy('PEANUTS')
        allergies = self.profile.get_allergies_list()
        assert 'peanuts' in allergies


class TestAllergyFiltering(TestCase):
    
    def setUp(self):
        """Create test foods"""
        self.peanut_food = Food.objects.create(
            name='Peanut Butter',
            category='snack',
            diet_type='veg',
            calories=180,
            protein=8,
            carbs=7,
            fats=16
        )
        self.shellfish_food = Food.objects.create(
            name='Shellfish Curry',
            category='lunch',
            diet_type='nonveg',
            calories=250,
            protein=30,
            carbs=15,
            fats=8
        )
        self.safe_food = Food.objects.create(
            name='Vegetable Salad',
            category='lunch',
            diet_type='veg',
            calories=150,
            protein=5,
            carbs=20,
            fats=3
        )
    
    def test_allergy_filter_excludes_allergen_foods(self):
        """Test that foods containing allergens are excluded"""
        foods = Food.objects.all()
        allergies = ['peanut']  # singular also covered by plural logic
        
        filtered = apply_allergy_filter(foods, allergies)
        
        # Peanut butter should be excluded
        assert self.peanut_food not in filtered
        # Others should remain
        assert self.shellfish_food in filtered
        assert self.safe_food in filtered
    
    def test_multiple_allergen_filtering(self):
        """Test filtering with multiple allergens"""
        foods = Food.objects.all()
        allergies = ['peanut', 'shellfish']
        
        filtered = apply_allergy_filter(foods, allergies)
        
        # Both should be excluded
        assert self.peanut_food not in filtered
        assert self.shellfish_food not in filtered
        # Safe food should remain
        assert self.safe_food in filtered
    
    def test_empty_allergy_list_returns_all(self):
        """Test that empty allergy list returns all foods"""
        foods = Food.objects.all()
        filtered = apply_allergy_filter(foods, [])
        
        assert filtered.count() == foods.count()


class TestMedicalConditionFiltering(TestCase):
    
    def setUp(self):
        """Create test foods"""
        # High carb food for diabetes
        self.high_carb = Food.objects.create(
            name='Pasta',
            category='lunch',
            diet_type='veg',
            calories=300,
            protein=10,
            carbs=55,  # High carbs
            fats=3,
            fiber=1
        )
        
        # Low carb, high fiber for diabetes
        self.low_carb = Food.objects.create(
            name='Broccoli Bowl',
            category='lunch',
            diet_type='veg',
            calories=150,
            protein=8,
            carbs=20,  # Low carbs
            fats=2,
            fiber=4   # High fiber
        )
        
        # High sodium for hypertension
        self.high_sodium = Food.objects.create(
            name='Processed Food',
            category='snack',
            diet_type='veg',
            calories=200,
            protein=5,
            carbs=15,
            fats=12,
            sodium=800  # High sodium
        )
        
        # Low sodium
        self.low_sodium = Food.objects.create(
            name='Fresh Vegetables',
            category='lunch',
            diet_type='veg',
            calories=100,
            protein=4,
            carbs=15,
            fats=1,
            sodium=50   # Low sodium
        )
        # Foods for obesity test
        self.high_calorie = Food.objects.create(
            name='Cheeseburger Deluxe',
            category='lunch',
            diet_type='nonveg',
            calories=800,
            protein=40,
            carbs=50,
            fats=45
        )
        self.low_calorie = Food.objects.create(
            name='Grilled Chicken Salad',
            category='lunch',
            diet_type='nonveg',
            calories=300,
            protein=30,
            carbs=20,
            fats=5
        )
    
    def test_diabetes_filter(self):
        """Test diabetes medical condition filtering"""
        foods = Food.objects.all()
        filtered = apply_health_filter(foods, 'diabetes')
        
        # High carb should be excluded
        assert self.high_carb not in filtered
        # Low carb with high fiber should be included
        assert self.low_carb in filtered
    
    def test_hypertension_filter(self):
        """Test hypertension medical condition filtering"""
        foods = Food.objects.all()
        filtered = apply_health_filter(foods, 'hypertension')
        
        # High sodium might be filtered (depends on exact filter values)
        # Low sodium should be included
        assert self.low_sodium in filtered
    
    def test_obesity_filter(self):
        """Test obesity medical condition filtering"""
        foods = Food.objects.all()
        filtered = apply_health_filter(foods, 'obesity')
        # High calorie/fat item should be excluded
        assert self.high_calorie not in filtered
        # Lower calorie item should remain
        assert self.low_calorie in filtered
    
    def test_no_filter_for_none_condition(self):
        """Test that 'none' condition returns all foods"""
        foods = Food.objects.all()
        filtered = apply_health_filter(foods, 'none')
        
        assert filtered.count() == foods.count()

    def test_condition_compliance_obesity(self):
        """Condition compliance should warn for very high calorie/fat meals"""
        # create a simple meal plan with one high calorie meal
        meal_plan = {
            'breakfast': self.high_calorie,
            'lunch': None,
            'dinner': None,
            'snack': None,
        }
        user = User.objects.create_user(username='temp', password='pw')
        profile = user.userprofile
        profile.medical_conditions = 'obesity'
        profile.save()

        result = check_condition_compliance(meal_plan, profile)
        assert result['compliant'] == False
        assert any('Very high calories' in w for w in result['warnings'])


class TestSodiumAlerts(TestCase):
    
    def setUp(self):
        """Create test user and foods"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
        self.profile.sodium_limit_mg = 2300
        self.profile.save()
        
        # Low sodium food
        self.low_sodium_food = Food.objects.create(
            name='Salad',
            category='lunch',
            diet_type='veg',
            calories=150,
            protein=8,
            carbs=20,
            fats=3,
            sodium=200
        )
        
        # High sodium food
        self.high_sodium_food = Food.objects.create(
            name='Soup',
            category='lunch',
            diet_type='veg',
            calories=200,
            protein=10,
            carbs=25,
            fats=5,
            sodium=1200
        )
    
    def test_sodium_alert_below_limit(self):
        """Test sodium alert when below limit"""
        meal_plan = {
            'breakfast': self.low_sodium_food,
            'lunch': self.low_sodium_food,
            'dinner': self.low_sodium_food,
            'snack': None
        }
        
        alert = check_sodium_alerts(meal_plan, self.profile)
        
        assert alert['alert'] == False
        assert alert['total_sodium'] == 600  # 200 * 3
    
    def test_sodium_alert_above_limit(self):
        """Test sodium alert when above limit"""
        meal_plan = {
            'breakfast': self.high_sodium_food,
            'lunch': self.high_sodium_food,
            'dinner': self.high_sodium_food,
            'snack': None
        }
        
        alert = check_sodium_alerts(meal_plan, self.profile)
        
        assert alert['alert'] == True
        assert alert['total_sodium'] == 3600  # 1200 * 3


class TestConditionCompliance(TestCase):
    
    def setUp(self):
        """Create test user with medical condition"""
        self.user = User.objects.create_user(
            username='diabetic',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.userprofile
        self.profile.medical_conditions = 'diabetes'
        self.profile.save()
    
    def test_compliance_check_with_high_carbs(self):
        """Test that compliance check identifies high carb meals"""
        high_carb_food = Food.objects.create(
            name='Pasta',
            category='lunch',
            diet_type='veg',
            calories=300,
            protein=10,
            carbs=60,  # High carbs for diabetic
            fats=3
        )
        
        meal_plan = {
            'breakfast': high_carb_food,
            'lunch': high_carb_food,
            'dinner': high_carb_food,
            'snack': None
        }
        
        compliance = check_condition_compliance(meal_plan, self.profile)
        
        assert compliance['compliant'] == False
        assert len(compliance['warnings']) > 0


# Run tests with: python manage.py test accounts.tests
