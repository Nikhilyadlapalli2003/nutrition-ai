# 🏗️ ML Architecture & Quick Reference

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      USER INTERACTION LAYER                     │
├────────────────────────────────────────────────────────────────┤
│  /recommendations/knn/          → Personalized meal plan view   │
│  /recommendations/alternatives/ → Food alternatives API JSON   │
│  /recommendations/preferences/  → Preference analytics view    │
│  /recommendations/api/knn-stats → User stats API JSON         │
└────────────────────────────────────────────────────────────────┘
                                  ↓↑
┌────────────────────────────────────────────────────────────────┐
│                      VIEW & ENDPOINT LAYER                      │
├────────────────────────────────────────────────────────────────┤
│  knn_views.py                                                   │
│  ├─ knn_recommendation_view()   → Full meal plan               │
│  ├─ get_alternatives_api()      → Similar foods JSON           │
│  ├─ preference_analytics_view() → User insights               │
│  └─ knn_stats_api()             → Stats JSON                  │
└────────────────────────────────────────────────────────────────┘
                                  ↓↑
┌────────────────────────────────────────────────────────────────┐
│                  RECOMMENDATION ENGINE LAYER                    │
├────────────────────────────────────────────────────────────────┤
│  engine.py                                                      │
│  ├─ get_best_meal_knn()       → Select meal by KNN            │
│  ├─ structured_meal_plan()    → Generate daily plan           │
│  ├─ get_knn_personalized_plan → Full personalized plan        │
│  └─ get_food_alternatives()   → Find similar foods           │
└────────────────────────────────────────────────────────────────┘
                                  ↓↑
┌────────────────────────────────────────────────────────────────┐
│                   MACHINE LEARNING LAYER                        │
├────────────────────────────────────────────────────────────────┤
│  ml_models.py                                                   │
│  ├─ Nutrients               → Vectorization                    │
│  │  ├─ get_normalized_vector()    → 8D vector                │
│  │  └─ create_target_vector()     → Ideal nutrition         │
│  ├─ KNNFoodRecommender      → Similarity engine              │
│  │  ├─ build_index()             → Build KNN tree           │
│  │  ├─ find_similar_foods()      → Find K neighbors         │
│  │  └─ recommend_by_target()     → Target-based recommend   │
│  ├─ UserPreferenceKNN       → Personalization               │
│  │  ├─ load_user_preferences()   → Get liked foods         │
│  │  ├─ get_recommendations_from_preferences()              │
│  │  └─ get_favorite_nutrient_profile()                    │
│  └─ KNNMealPlanner          → Meal planning                 │
│     ├─ generate_meal_plan()      → Full day's meals        │
│     └─ _score_candidates()       → Rank meals             │
└────────────────────────────────────────────────────────────────┘
                                  ↓↑
┌────────────────────────────────────────────────────────────────┐
│                    DATA & MODEL LAYER                           │
├────────────────────────────────────────────────────────────────┤
│  scikit-learn (KNN Model)                                       │
│  ├─ StandardScaler()        → Normalize vectors               │
│  └─ NearestNeighbors()      → KNN algorithm                   │
│                                                                 │
│  Django ORM (Data Access)                                       │
│  ├─ Food.objects.all()      → Get all foods                   │
│  ├─ FoodFeedback.objects    → User preferences               │
│  ├─ MealHistory.objects     → Track eaten meals              │
│  └─ UserProfile             → User nutritional profile        │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
USER REQUESTS MEAL PLAN
        ↓
LOAD USER PROFILE & PREFERENCES
        ↓
CALCULATE TARGET CALORIES (BMR/TDEE)
        ↓
FOR EACH MEAL TYPE (breakfast, lunch, dinner, snack):
    ├─ Calculate meal calorie target
    ├─ BUILD KNN INDEX from available foods
    │  └─ Convert all foods to nutritional vectors
    │  └─ Apply StandardScaler normalization
    │  └─ Create NearestNeighbors model
    │
    ├─ KNN FOOD SEARCH
    │  └─ Find K foods closest to calorie target
    │  └─ Get similarity scores (0-1)
    │
    ├─ PERSONALIZATION SCORING
    │  ├─ Get user's previously liked foods
    │  ├─ Boost score for similar recommendations
    │  └─ Apply user preference weights
    │
    └─ SELECT BEST MEAL
       └─ Return highest scored food
        
RETURN FULL MEAL PLAN
        ↓
PORTION NORMALIZE (adjust to target calories)
        ↓
SAVE TO MEAL HISTORY
        ↓
DISPLAY TO USER WITH ALTERNATIVES & ANALYTICS
```

---

## Quick Function Reference

### Vectorization
```python
# Convert food to 8D vector
from recommendations.ml_models import Nutrients
vec = Nutrients.get_normalized_vector(food)
# Returns: [cal, protein, carbs, fats, fiber, calcium, sodium, vit_c]
```

### Find Similar Foods
```python
from recommendations.ml_models import KNNFoodRecommender
knn = KNNFoodRecommender(n_neighbors=5)
knn.build_index(Food.objects.all())
similar = knn.find_similar_foods(chicken, k=3)
# Returns: [{"food": obj, "similarity_score": 0.92, ...}, ...]
```

### Generate Personalized Plan
```python
from recommendations.engine import get_knn_personalized_plan
plan = get_knn_personalized_plan(user, profile, 2000)
# Returns: {"breakfast": food, "lunch": food, "dinner": food, "snack": food}
```

### Learn User Preferences
```python
from recommendations.ml_models import UserPreferenceKNN
prefs = UserPreferenceKNN(user, min_feedback_score=3)
ratio = prefs.get_favorite_nutrient_profile()
# Returns: {"protein": 0.35, "carbs": 0.45, "fats": 0.20}
```

### Get API Results
```python
# Food Alternatives
GET /recommendations/alternatives/42/
# Returns JSON with similar foods

# User Stats
GET /recommendations/api/knn-stats/
# Returns JSON with user statistics
```

---

## Component Interaction Map

```
┌─────────────────────────┐
│   USER FEEDBACK         │
│  (FoodFeedback Model)   │
└────────────┬────────────┘
             │ (score >= 3)
             ↓
┌─────────────────────────────────┐
│   UserPreferenceKNN             │
│  - Loads liked foods            │
│  - Extracts macro preferences   │
│  - Scores recommendations       │
└────────────┬────────────────────┘
             │
             ├→ [Preferred Macros: 35% P, 45% C, 20% F]
             │
             ↓
┌────────────────────────────────────┐
│   KNNFoodRecommender               │
│  - Builds similarity index         │
│  - Finds K nearest neighbors       │
│  - Scores by distance + pref       │
└────────────┬─────────────────────┘
             │
             ├→ [Top 5 Similar Foods]
             │
             ↓
┌────────────────────────────────────┐
│   KNNMealPlanner                   │
│  - Combines KNN + preferences      │
│  - Generates daily meal plan       │
│  - Normalizes portions             │
└────────────┬─────────────────────┘
             │
             ├→ [Breakfast: Eggs, Lunch: Chicken, ...]
             │
             ↓
┌────────────────────────────────────┐
│   View/API Response                │
│  - HTML page or JSON API           │
│  - With alternatives & stats       │
└────────────────────────────────────┘
```

---

## Parameter Quick Reference

### Core Parameters
```python
# ml_models.py
n_neighbors=5           # KNN neighbors to consider
min_feedback_score=3    # Min score for preference learning
p=2                    # Distance metric (2=Euclidean, 1=Manhattan)

# engine.py
breakfast_pct=0.25     # 25% of daily calories
lunch_pct=0.35         # 35% of daily calories
dinner_pct=0.30        # 30% of daily calories
snack_pct=0.10         # 10% of daily calories
```

### Vector Dimensions
```python
[0] calories    # Daily energy target
[1] protein     # Grams - amino acids
[2] carbs       # Grams - energy source
[3] fats        # Grams - essential fatty acids
[4] fiber       # Grams - digestive health
[5] calcium     # mg - bone health
[6] sodium      # mg - electrolyte balance
[7] vitamin_c   # mg - immunity
```

### Scoring Weights
```python
final_score = (
    (knn_similarity * 0.7) +      # 70% based on nutritional match
    (user_preference * 0.3)        # 30% based on user likes
)
```

---

## Workflow Example: Step by Step

### Scenario: User requests personalized breakfast

```
1. USER NAVIGATES TO: /recommendations/knn/

2. SYSTEM LOADS USER DATA:
   - Profile: Goal='loss', Dietary='veg', Activity='moderate'
   - Breakfast target: 2000 * 0.25 = 500 calories

3. BUILD KNN INDEX:
   - Convert 500+ foods to vectors
   - Normalize with StandardScaler
   - Build scikit-learn KNN model
   - Ready for similarity search

4. FIND SIMILAR FOODS:
   - Target vector: [500, 62.5, 200, 55.5, ...]
   - KNN finds 5 closest foods by distance
   - Results: Oatmeal (similarity 0.95), Eggs (0.92), ...

5. PERSONALIZE WITH USER PREFS:
   - User likes: Eggs, Whole Wheat Toast, Fruits
   - Boost score if food is similar to liked items
   - Eggs toast gets multiplier: 0.92 * 1.5 = 1.38

6. SELECT BEST MEAL:
   - Rank by final score
   - Winner: "Eggs with Whole Wheat Toast" (0.95 match)

7. PORTION NORMALIZE:
   - Food has 600 cal, need 500
   - Scale all nutrients: multiply by 500/600
   - Adjusted: [500, 26, 40, 18, ...]

8. DISPLAY TO USER:
   - Show: "Eggs with Whole Wheat Toast"
   - Display adjusted values
   - Show alternatives: "Toast with Peanut Butter" (0.88 match)
   - Show macro ratios from user preferences
```

---

## Common Use Cases

### Use Case 1: "Find meals like the ones I like"
```python
prefs = UserPreferenceKNN(user)
recommendations = prefs.get_recommendations_from_preferences(all_foods, k=10)
```

### Use Case 2: "What can I eat for 400 calories?"
```python
recommendations = knn.recommend_by_target(400, meal_type='lunch', k=5)
```

### Use Case 3: "What's similar to chicken breast?"
```python
chicken = Food.objects.get(name="Chicken Breast")
alternatives = get_food_alternatives(chicken, k=5)
```

### Use Case 4: "Generate my meal plan for today"
```python
meal_plan = get_knn_personalized_plan(user, profile, 2000)
```

### Use Case 5: "Show my food preferences"
```python
prefs = UserPreferenceKNN(user)
macros = prefs.get_favorite_nutrient_profile()
```

---

## Error Handling

### Error: "ValueError: No foods provided"
```python
# WRONG: Empty queryset
knn.build_index(Food.objects.filter(name="NonExistent"))

# CORRECT: Non-empty queryset
knn.build_index(Food.objects.filter(category="breakfast"))
```

### Error: "Cannot find similar foods"
```python
# WRONG: No feedback data
user_prefs = UserPreferenceKNN(user)  # user has no likes

# CORRECT: Add some feedback first
FoodFeedback.objects.create(user=user, food=food, score=4)
user_prefs = UserPreferenceKNN(user, min_feedback_score=3)
```

### Error: "KNN index not built"
```python
# WRONG: Missing build step
similar = knn.find_similar_foods(food)  # ← Error!

# CORRECT: Build first
knn.build_index(foods)
similar = knn.find_similar_foods(food)  # ← Works!
```

---

## Performance Tips

1. **Build index once**: Cache KNN index for multiple queries
2. **Filter first**: Reduce food set before KNN (diet type, category)
3. **Use appropriate K**: Higher K = slower but more diverse results
4. **Collect feedback**: More user feedback = better recommendations

---

## Testing Checklist

- [ ] Can build KNN index without errors
- [ ] Can find similar foods with similarity scores
- [ ] Can generate meal plans matching calorie targets
- [ ] User preferences load correctly from feedback
- [ ] API endpoints return valid JSON
- [ ] Views render with actual meal data
- [ ] Portion normalization works correctly
- [ ] Fallback to hybrid when KNN fails

---

**Last Updated:** March 2026  
**Version:** 1.0 - KNN Implementation  
**Status:** ✅ Production Ready
