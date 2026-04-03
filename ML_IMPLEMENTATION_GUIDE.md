# 🤖 Machine Learning Integration - KNN Recommendation System

## Overview

This document describes the **K-Nearest Neighbors (KNN)** machine learning algorithm implementation for personalized nutrition recommendations in the Nutrition AI Django application.

---

## 🎯 Features Implemented

### 1. **KNN Food Similarity Detection**
- Converts food items to normalized nutritional vectors (8 dimensions)
- Finds similar foods based on macro/micronutrient profiles
- Uses Euclidean distance for similarity measurement
- Scales features for fair comparison

### 2. **Personalized Recommendation Engine**
- Learns from user feedback history (liked/disliked foods)
- Generates recommendations based on nutritional targets
- Combines KNN similarity with user preferences
- Supports dietary filters (vegan, keto, etc.)

### 3. **User Preference Learning**
- Extracts user's favorite macro nutrient ratios
- Identifies food categories user tends to like
- Recommends foods similar to previously liked items
- Adaptive recommendations based on feedback scores

### 4. **Meal Planning**
- Generates daily meal plans matching calorie targets
- Distributes calories: breakfast (25%), lunch (35%), dinner (30%), snack (10%)
- Applies health condition filters (diabetes, hypertension)
- Returns portion-normalized nutritional values

---

## 📂 File Structure

```
recommendations/
├── ml_models.py          # KNN implementation & utilities
├── engine.py             # Enhanced recommendation engine with KNN integration
├── knn_views.py          # KNN-based view functions
├── urls.py               # Routes for KNN endpoints
└── views.py              # Original hybrid recommendation views
```

---

## 🔧 Core Components

### A. Nutritional Vectorization (`ml_models.py`)

```python
class Nutrients:
    - get_normalized_vector(food)      # Convert food to 8D vector
    - create_target_vector(calories)   # Create ideal target vector
```

**Vector Format:** `[calories, protein, carbs, fats, fiber, calcium, sodium, vitamin_c]`

### B. KNN Food Recommender (`ml_models.py`)

```python
class KNNFoodRecommender:
    def __init__(n_neighbors=5)                    # Initialize with K value
    def build_index(foods_queryset)                # Build KNN index
    def find_similar_foods(query_food, k=5)        # Find similar foods
    def recommend_by_target(target_calories, k=5)  # Recommend by nutrition target
```

### C. User Preference KNN (`ml_models.py`)

```python
class UserPreferenceKNN:
    def __init__(user, min_feedback_score=3)                              # Initialize with user
    def load_user_preferences()                                           # Load liked foods
    def get_recommendations_from_preferences(all_foods, k=5)              # Recommend based on preferences
    def get_favorite_nutrient_profile()                                   # Extract macro ratios
```

### D. KNN Meal Planner (`ml_models.py`)

```python
class KNNMealPlanner:
    def __init__(user, profile, target_calories)        # Initialize planner
    def generate_meal_plan()                            # Generate daily plan
    def _score_candidates(candidates, preferences)      # Score and rank meals
```

---

## 🚀 Usage Examples

### 1. Using KNN-Based Recommendations (View)

```python
from recommendations.knn_views import knn_recommendation_view

# User visits /recommendations/knn/ endpoint
# System automatically generates KNN-based meal plan
```

### 2. Finding Similar Foods

```python
from recommendations.ml_models import KNNFoodRecommender
from nutrition.models import Food

# Find foods similar to Chicken Rice
chicken_rice = Food.objects.get(name="Chicken Rice")
knn = KNNFoodRecommender(n_neighbors=5)
knn.build_index(Food.objects.all())
similar = knn.find_similar_foods(chicken_rice, k=3)

for result in similar:
    print(f"{result['food'].name}: {result['similarity_score']:.2f}")
```

### 3. Learning User Preferences

```python
from recommendations.ml_models import UserPreferenceKNN

user_prefs = UserPreferenceKNN(request.user, min_feedback_score=3)
liked_foods = user_prefs.liked_foods
macro_preference = user_prefs.get_favorite_nutrient_profile()

print(f"Protein: {macro_preference['protein']*100:.1f}%")
print(f"Carbs: {macro_preference['carbs']*100:.1f}%")
print(f"Fats: {macro_preference['fats']*100:.1f}%")
```

### 4. Generating Personalized Meal Plan

```python
from recommendations.engine import get_knn_personalized_plan

meal_plan = get_knn_personalized_plan(
    user=request.user,
    profile=user_profile,
    target_calories=2000
)

for meal_type, food in meal_plan.items():
    print(f"{meal_type}: {food.name} ({food.calories} cal)")
```

### 5. Getting Food Alternatives

```python
from recommendations.engine import get_food_alternatives

alternatives = get_food_alternatives(food_obj, k=5)
for alt in alternatives:
    print(f"{alt['food'].name}: {alt['similarity_score']:.3f}")
```

---

## 📡 API Endpoints

### 1. KNN Recommendation View
**URL:** `/recommendations/knn/`
**Method:** GET
**Auth:** Required (login_required)
**Returns:** HTML page with KNN-based meal plan

### 2. Food Alternatives API
**URL:** `/recommendations/alternatives/<food_id>/`
**Method:** GET
**Returns:** JSON with similar foods
```json
{
    "success": true,
    "food": {"id": 1, "name": "Chicken", "calories": 165},
    "alternatives": [
        {"id": 2, "name": "Turkey", "similarity_score": 0.92, ...},
        {"id": 3, "name": "Fish", "similarity_score": 0.88, ...}
    ]
}
```

### 3. Preference Analytics
**URL:** `/recommendations/preferences/`
**Method:** GET
**Auth:** Required
**Returns:** User preference analysis and recommendations

### 4. KNN Stats API
**URL:** `/recommendations/api/knn-stats/`
**Method:** GET
**Returns:** JSON with user's KNN statistics
```json
{
    "success": true,
    "liked_foods_count": 15,
    "preferred_macros": {
        "protein": 35.5,
        "carbs": 45.2,
        "fats": 19.3
    },
    "recommendation_model": "KNN"
}
```

---

## ⚙️ Configuration & Parameters

### KNN Model Parameters

```python
# In ml_models.py
n_neighbors = 5          # Number of neighbors to consider
algorithm = 'auto'       # Algorithm used: 'auto', 'ball_tree', 'kd_tree', 'brute'
p = 2                    # Distance metric: Euclidean (2) or Manhattan (1)
```

### Nutritional Vector Dimensions

1. **Calories** - Daily target
2. **Protein (g)** - Amino acids
3. **Carbs (g)** - Energy source
4. **Fats (g)** - Essential fatty acids
5. **Fiber (g)** - Digestive health
6. **Calcium (mg)** - Bone health
7. **Sodium (mg)** - Electrolyte balance
8. **Vitamin C (mg)** - Immunity

---

## 📊 Algorithm Details

### Distance Calculation (Euclidean)
```
distance = sqrt((f1-f2)² + (p1-p2)² + ... + (v1-v2)²)
similarity_score = 1 / (1 + distance)
```

### Scoring Function
```
final_score = (KNN_similarity * 0.7) + (user_preference_bonus * 0.3)
```

### Preference Learning
- Only considers foods with feedback_score ≥ 3
- Extracts macro ratios from liked foods
- Weights recommendations by frequency and similarity

---

## 🔄 Integration with Existing System

### Original Hybrid Approach (Still Available)
```python
structured_meal_plan(profile, target_calories, user, use_knn=False)
```

### With KNN Enhancement
```python
structured_meal_plan(profile, target_calories, user, use_knn=True)
```

**Both approaches:**
- Normalize meal portions to target calories
- Apply health condition filters
- Save meal history to database
- Calculate macro/micronutrient totals

---

## 📦 Dependencies

```
scikit-learn >= 0.24.0      # KNN & preprocessing
numpy >= 1.19.0             # Numerical operations
Django >= 3.2               # Web framework
```

**Verify installation:**
```bash
pip list | grep scikit-learn
```

---

## 🧪 Testing the Implementation

### Test KNN Food Similarity
```python
from recommendations.ml_models import KNNFoodRecommender
from nutrition.models import Food

foods = Food.objects.all()
knn = KNNFoodRecommender(n_neighbors=5)
knn.build_index(foods)

test_food = foods.first()
similar = knn.find_similar_foods(test_food, k=3)
assert len(similar) == 3
assert similar[0]['similarity_score'] <= 1.0
```

### Test User Preference Learning
```python
from recommendations.ml_models import UserPreferenceKNN

upref = UserPreferenceKNN(user)
macro = upref.get_favorite_nutrient_profile()
assert sum([macro['protein'], macro['carbs'], macro['fats']]) == pytest.approx(1.0)
```

### Test Meal Planning
```python
from recommendations.engine import get_knn_personalized_plan

plan = get_knn_personalized_plan(user, profile, 2000)
assert 'breakfast' in plan
assert 'lunch' in plan
assert 'dinner' in plan
assert 'snack' in plan
assert all(meal is not None for meal in plan.values())
```

---

## 🐛 Troubleshooting

### Issue: "KNN index not built"
**Solution:** Ensure `build_index()` is called before `find_similar_foods()`
```python
knn.build_index(foods_queryset)
similar = knn.find_similar_foods(food)
```

### Issue: "No foods provided for KNN index"
**Solution:** Provide non-empty queryset
```python
foods = Food.objects.filter(diet_type='veg')  # Ensure queryset is not empty
knn.build_index(foods)
```

### Issue: Recommendations identical to hybrid approach
**Solution:** Add user feedback to enable preference learning
```python
# User feedback is required for KNN personalization
FoodFeedback.objects.create(user=user, food=food, score=5)
```

---

## 🚀 Future Enhancements

### Option B – Random Forest Nutrition Predictor
- Predict meal suitability score using decision trees
- Rank meals by ML-predicted scores
- Feature importances reveal key nutrition factors

### Option C – Support Vector Machine (SVM)
- Classify meals as "healthy" vs "less suitable"
- Binary classification based on nutrition thresholds
- Improved spam/poor-nutrition filtering

### Option D – Linear Regression Model
- Predict ideal calorie distribution
- Estimate nutrient suitability scores
- Model user's energy needs vs activity level

---

## 📝 Version History

- **v1.0** (Current) - KNN Food Similarity & Personalization
  - ✅ KNN food similarity detection
  - ✅ User preference learning
  - ✅ Personalized meal planning
  - ✅ API endpoints for alternatives & stats
  
- **v1.1** (Planned) - Multi-Algorithm Support
  - Random Forest for meal scoring
  - SVM for healthy/unhealthy classification
  - Linear Regression for calorie prediction

---

## 📞 Support & Documentation

For detailed code documentation, see inline comments in:
- `recommendations/ml_models.py`
- `recommendations/engine.py`
- `recommendations/knn_views.py`

---

**Last Updated:** March 2026
**Algorithm:** K-Nearest Neighbors (sklearn implementation)
**Status:** ✅ Production Ready
