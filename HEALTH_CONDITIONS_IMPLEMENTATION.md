# Medical Conditions, Allergies & Health Alerts System

This document explains the new features for medical condition filtering, allergy management, and sodium/sugar alerts in the Nutrition AI system.

## Overview

The system now includes three major features:
1. **Medical Condition Filtering** - Tailored recommendations based on health conditions
2. **Sodium & Sugar Alerts** - Warns users when meals exceed healthy limits
3. **Allergy Filtering** - Automatically excludes allergenic foods from recommendations

---

## Database Schema Changes

### UserProfile Model Extensions

The `UserProfile` model has been extended with the following new fields:

```python
medical_conditions = CharField(
    choices=['diabetes', 'hypertension', 'heart_disease', 'obesity', 'none'],
    default='none'
)
allergies = TextField()  # Comma-separated list of allergens
sodium_limit_mg = IntegerField(default=2300)  # Daily sodium limit
sugar_limit_g = IntegerField(default=50)  # Daily sugar limit
```

### Food Model Extensions

The `Food` model now includes:
```python
sugar = FloatField(default=0)  # Added sugar in grams
```

---

## Medical Condition Filtering

### Supported Conditions

1. **Diabetes** 
   - Filters foods with carbs < 40g and fiber > 2g
   - Penalizes carb-heavy meals in scoring

2. **Hypertension**
   - Filters foods with sodium < 500mg and fats < 15g
   - Promotes low-sodium food choices

3. **Heart Disease**
   - Filters foods with sodium < 400mg and fats < 10g
   - Strictest filtering for cardiovascular health

4. **Obesity**
   - Filters out extremely high-calorie (>500 kcal) or high-fat (>20 g) items
   - Warns when individual meals exceed 600 kcal or 25 g fat

### How Filtering Works

When a user selects a medical condition:

1. **In `engine.py`**: `apply_health_filter()` function filters foods based on condition
2. **In `structured_meal_plan()`**: The filter is applied to all food selections
3. **In recommendations view**: `check_condition_compliance()` validates meal plan matches condition requirements

### Example Usage

```python
from accounts.profile_utils import setup_medical_conditions_for_user

# Set user's medical condition
setup_medical_conditions_for_user(user, 'diabetes')
```

---

## Allergy Management

### Adding Allergies

Users can add allergies through their profile. Multiple allergens are supported.

```python
from accounts.profile_utils import add_allergies_to_user

# Add allergies
add_allergies_to_user(user, "peanuts, shellfish, dairy")

# Or add individually
profile = user.userprofile
profile.add_allergy("peanuts")
profile.add_allergy("shellfish")
```

### How Allergy Filtering Works

1. **In `engine.py`**: `apply_allergy_filter()` excludes foods containing allergen names
2. **In `structured_meal_plan()`**: Allergies are retrieved and applied to filter foods
3. **In template**: Displays which allergens are currently being filtered

### Food Matching

The system excludes foods where the allergen name appears in the food name (case-insensitive):
- Allergen: "peanuts" → Excludes: "Peanut Butter", "Peanut Sauce", etc.
- Allergen: "dairy" → Excludes: "Cheese", "Milk", "Yogurt", etc.

---

## Sodium & Sugar Alerts

### Sodium Alerts

The system checks daily sodium intake against user-defined limits:

```python
def check_sodium_alerts(meal_plan, profile):
    """
    Returns:
    {
        'total_sodium': float,
        'limit': int,
        'alert': bool,
        'percentage': float,
        'message': str
    }
    """
```

**Healthy Sodium Limits by Condition:**
- General adults: 2300 mg/day
- Hypertension/Heart disease: 1500-2000 mg/day
- Custom limits can be set per user

### Sugar Alerts

Similar to sodium:

```python
def check_sugar_alerts(meal_plan, profile):
    """
    Returns sugar consumption info relative to user's limit.
    Default limit: 50g/day
    """
```

### Alert Display in Template

Alerts appear at the top of recommendations with color coding:

- **Red Alert** (⚠️): Exceeds limit
- **Blue Info** (✅): Within limit
- **Yellow Warning** (⚠️): Approaching limit

---

## Implementation Details

### Engine Functions

#### `apply_health_filter(foods, medical_condition)`
Filters foods based on medical condition requirements.

**Parameters:**
- `foods`: QuerySet of Food objects
- `medical_condition`: 'diabetes', 'hypertension', 'heart_disease', or None

**Returns:** Filtered QuerySet

#### `apply_allergy_filter(foods, allergies_list)`
Excludes foods containing allergens.

**Parameters:**
- `foods`: QuerySet of Food objects
- `allergies_list`: List of allergen names (lowercase)

**Returns:** Filtered QuerySet

#### `apply_sodium_limit_filter(foods, sodium_limit_mg)`
Filters foods within sodium limits.

**Parameters:**
- `foods`: QuerySet of Food objects
- `sodium_limit_mg`: Maximum sodium per meal

**Returns:** Filtered QuerySet

#### `check_sodium_alerts(meal_plan, profile)`
Validates meal plan sodium compliance.

**Returns:** Dict with alert info

#### `check_sugar_alerts(meal_plan, profile)`
Validates meal plan sugar compliance.

**Returns:** Dict with alert info

#### `check_condition_compliance(meal_plan, profile)`
Verifies meal plan matches medical condition requirements.

**Returns:** Dict with compliance status and warnings

### Profile Utilities

---

## Profile Form Validation

To ensure users supply realistic health data, the profile page now validates both on the
client and server:

* **Age** must be an integer between **10 and 100**.
* **Height** must be a number between **100 cm and 220 cm**.
* **Weight** must be a number between **30 kg and 200 kg**.
* **Gender, activity level, dietary preference and goal are required** and cannot be left
  blank.
* **Health condition is also required and chosen from a fixed list** (diabetes, hypertension,
  heart disease, obesity, none).  The profile page uses a dropdown populated directly from the
  dataset / model choices so users can't enter arbitrary text.

Client‑side `min`, `max` and `required` attributes have been added to the HTML inputs,
and the `profile_view` routine checks each value on submission.  If any field fails
validation the form is not saved and the user sees a generic error message:

```
Enter Correctly
```

The submitted values are retained in the form so the user can correct mistakes without
re‑entering other data.

These rules are covered by `accounts/tests_profile.py` in the test suite.

### Profile Utilities

The `accounts/profile_utils.py` module provides helper functions:

```python
# Setup medical conditions
setup_medical_conditions_for_user(user, 'diabetes')

# Manage allergies
add_allergies_to_user(user, "peanuts, shellfish")
remove_allergy_from_user(user, "peanuts")

# Set health limits
set_sodium_limit(user, 1500)  # mg per day
set_sugar_limit(user, 25)     # grams per day

# Get profile summary
get_user_dietary_profile(user)
```

---

## Template Display

### Alert Sections

The recommendations template now displays:

1. **Sodium Alert**
   - Shows total sodium vs daily limit
   - Visual indicator (red/blue)
   - Percentage of limit consumed

2. **Sugar Alert**
   - Similar to sodium alert
   - Yellow warning if approaching limit

3. **Medical Condition Compliance**
   - Displays specific guidelines for condition
   - Lists warnings for meals that don't comply
   - Shows checkmark if fully compliant

4. **Allergy Filter Status**
   - Lists active allergens
   - Indicates filtering is active

---

## Usage Examples

### Complete Setup for Diabetic User

```python
from accounts.models import UserProfile
from accounts.profile_utils import (
    setup_medical_conditions_for_user,
    add_allergies_to_user,
    set_sodium_limit,
    set_sugar_limit
)

user = User.objects.get(username='john')

# Setup medical condition
setup_medical_conditions_for_user(user, 'diabetes')

# Add allergies
add_allergies_to_user(user, "peanuts, shellfish")

# Set custom limits
set_sodium_limit(user, 2000)
set_sugar_limit(user, 30)

# Get profile summary
profile = get_user_dietary_profile(user)
print(f"Condition: {profile['medical_condition']}")
print(f"Allergies: {profile['allergies']}")
print(f"Sodium limit: {profile['sodium_limit_mg']}mg")
```

### In Views

```python
@login_required
def recommendation_view(request):
    profile = UserProfile.objects.get(user=request.user)
    meal_plan = structured_meal_plan(profile, target_calories, request.user)
    
    # Get alerts
    sodium_alert = check_sodium_alerts(meal_plan, profile)
    sugar_alert = check_sugar_alerts(meal_plan, profile)
    compliance = check_condition_compliance(meal_plan, profile)
    
    context = {
        'meal_plan': meal_plan,
        'sodium_alert': sodium_alert,
        'sugar_alert': sugar_alert,
        'condition_compliance': compliance,
    }
```

---

## Migration Guide

After implementing these features:

1. **Apply migrations:**
   ```bash
   python manage.py migrate accounts
   python manage.py migrate nutrition
   ```

2. **Update existing users:**
   - Set medical conditions manually via admin panel
   - Or use profile management interface

3. **Test the system:**
   - Create test user with diabetes
   - Add peanut allergy
   - Generate recommendations
   - Verify alerts display correctly

---

## Admin Interface Enhancements

The UserProfile admin form will automatically include:
- Medical condition dropdown
- Allergies text field
- Sodium limit input
- Sugar limit input

---

## Troubleshooting

### Alerts not showing
- Check that `context` includes `sodium_alert`, `sugar_alert`, `condition_compliance`
- Verify template has alert sections
- Check Food model has `sodium` and `sugar` fields

### Allergies not filtering
- Ensure allergen names are added correctly (comma-separated in text field)
- Food names must contain allergen string (case-insensitive)
- Check `get_allergies_list()` returns correct list

### Medical condition not filtering
- Verify medical_conditions field is set (not 'none')
- Check Food model has required micronutrient fields
- Ensure `apply_health_filter()` is called in meal plan generation

---

## Future Enhancements

1. **Ingredient-level allergy tracking** - Track allergens in ingredients, not just food names
2. **Allergy severity levels** - Distinguish between severe (exclude) and mild (warn)
3. **Custom food restrictions** - Per-user food exclusions
4. **Nutrition targets** - Set target ranges for specific nutrients
5. **Meal plan validation** - Pre-generate alerts before showing meals
6. **Allergy cross-contamination warnings** - Warn about foods that may contain traces

---

## API Reference

### UserProfile Model Methods

```python
profile.get_allergies_list()  # Returns list of allergens
profile.add_allergy(allergen)  # Add single allergen
profile.remove_allergy(allergen)  # Remove allergen
profile.has_medical_condition()  # Boolean check
profile.get_medical_condition_display_name()  # Human-readable condition
```

### Engine Functions

All located in `recommendations/engine.py`:
- `apply_health_filter(foods, medical_condition)`
- `apply_allergy_filter(foods, allergies_list)`
- `apply_sodium_limit_filter(foods, sodium_limit_mg)`
- `check_sodium_alerts(meal_plan, profile)`
- `check_sugar_alerts(meal_plan, profile)`
- `check_condition_compliance(meal_plan, profile)`
- `structured_meal_plan(profile, target_calories, user, use_knn=True)`

---

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the template display format
3. Verify database migrations were applied
4. Check browser console for JavaScript errors
