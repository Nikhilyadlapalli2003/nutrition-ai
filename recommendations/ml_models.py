"""
=====================================================
🤖 MACHINE LEARNING MODELS FOR NUTRITION AI
=====================================================
Module: ml_models.py
Purpose: Implement ML-based recommendation algorithms
- KNN: Food Similarity & Personalized Recommendations
- Random Forest: User Preference Classification
- SVM: Meal Health Classification & Filtering
- Nutritional Vector Comparison
- User Preference Learning
=====================================================
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from nutrition.models import Food, FoodFeedback, MealHistory
from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
from django.utils import timezone
import pickle
import os


# =====================================================
# 1️⃣ NUTRITIONAL VECTORIZATION
# =====================================================
class Nutrients:
    """Class to manage nutritional vectors for foods"""
    
    @staticmethod
    def get_normalized_vector(food):
        """
        Convert food to normalized nutritional vector
        Returns: [calories, protein, carbs, fats, fiber, calcium, sodium, vitamin_c]
        """
        calories = getattr(food, "adjusted_calories", food.calories)
        protein = getattr(food, "adjusted_protein", food.protein)
        carbs = getattr(food, "adjusted_carbs", food.carbs)
        fats = getattr(food, "adjusted_fats", food.fats)
        
        return np.array([
            calories,
            protein,
            carbs,
            fats,
            food.fiber,
            food.calcium,
            food.sodium,
            food.vitamin_c
        ], dtype=float)
    
    @staticmethod
    def create_target_vector(target_calories, macro_ratio=None):
        """
        Create ideal nutritional target vector
        macro_ratio: dict {'protein': 0.30, 'carbs': 0.40, 'fats': 0.30}
        """
        if macro_ratio is None:
            macro_ratio = {'protein': 0.30, 'carbs': 0.40, 'fats': 0.30}
        
        protein = (target_calories * macro_ratio['protein']) / 4
        carbs = (target_calories * macro_ratio['carbs']) / 4
        fats = (target_calories * macro_ratio['fats']) / 9
        
        return np.array([
            target_calories,
            protein,
            carbs,
            fats,
            10,  # avg fiber
            500,  # avg calcium
            2000,  # avg sodium
            50  # avg vitamin_c
        ], dtype=float)


# =====================================================
# 2️⃣ K-NEAREST NEIGHBORS FOOD SIMILARITY
# =====================================================
class KNNFoodRecommender:
    """K-Nearest Neighbors based food recommendation engine"""
    
    def __init__(self, n_neighbors=5):
        self.n_neighbors = n_neighbors
        self.knn_model = None
        self.scaler = StandardScaler()
        self.foods = None
        self.food_vectors = None
    
    def build_index(self, foods_queryset):
        """
        Build KNN index from food dataset
        stores normalized vectors for all foods
        """
        self.foods = list(foods_queryset)
        
        if not self.foods:
            raise ValueError("No foods provided for KNN index")
        
        # Create nutritional vectors for all foods
        self.food_vectors = np.array([
            Nutrients.get_normalized_vector(food) 
            for food in self.foods
        ])
        
        # Normalize vectors for fair distance comparison
        self.food_vectors_scaled = self.scaler.fit_transform(self.food_vectors)
        
        # Build KNN model
        self.knn_model = NearestNeighbors(
            n_neighbors=min(self.n_neighbors, len(self.foods)),
            algorithm='auto',
            p=2  # Euclidean distance
        )
        self.knn_model.fit(self.food_vectors_scaled)
    
    def find_similar_foods(self, query_food, k=5):
        """
        Find k most similar foods to query_food
        Returns: [(food, distance), ...]
        """
        if self.knn_model is None:
            raise ValueError("KNN index not built. Call build_index first")
        
        query_vector = Nutrients.get_normalized_vector(query_food)
        query_vector_scaled = self.scaler.transform([query_vector])
        
        distances, indices = self.knn_model.kneighbors(query_vector_scaled, n_neighbors=k)
        
        # Return foods with their similarity scores (1 / (1 + distance))
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            similarity_score = 1 / (1 + dist)  # Convert distance to similarity
            results.append({
                'food': self.foods[idx],
                'distance': float(dist),
                'similarity_score': float(similarity_score)
            })
        
        return results
    
    def recommend_by_target(self, target_calories, meal_type=None, diet_type=None, k=5):
        """
        Recommend foods closest to nutritional target
        """
        if self.knn_model is None:
            raise ValueError("KNN index not built. Call build_index first")
        
        target_vector = Nutrients.create_target_vector(target_calories)
        target_vector_scaled = self.scaler.transform([target_vector])
        
        distances, indices = self.knn_model.kneighbors(target_vector_scaled, n_neighbors=k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            food = self.foods[idx]
            
            # Apply filters
            if meal_type and food.category != meal_type:
                continue
            if diet_type and food.diet_type != diet_type:
                continue
            
            similarity_score = 1 / (1 + dist)
            results.append({
                'food': food,
                'distance': float(dist),
                'similarity_score': float(similarity_score)
            })
        
        return results[:k]


# =====================================================
# 3️⃣ USER PREFERENCE LEARNING (Feedback-Based KNN)
# =====================================================
class UserPreferenceKNN:
    """
    Learn user food preferences from feedback history
    and recommend similar foods they previously liked
    """
    
    def __init__(self, user, min_feedback_score=3, n_neighbors=5):
        self.user = user
        self.min_feedback_score = min_feedback_score
        self.n_neighbors = n_neighbors
        self.liked_foods = []
        self.load_user_preferences()
    
    def load_user_preferences(self):
        """Load foods the user previously liked (feedback_score >= threshold)"""
        feedbacks = FoodFeedback.objects.filter(
            user=self.user,
            score__gte=self.min_feedback_score
        ).select_related('food')
        
        self.liked_foods = [fb.food for fb in feedbacks]
    
    def get_recommendations_from_preferences(self, all_foods, k=5):
        """
        Recommend foods similar to user's liked foods
        Uses collaborative vectorization approach
        """
        if not self.liked_foods:
            # No preference history, return empty
            return []
        
        # Build KNN on all foods
        recommender = KNNFoodRecommender(n_neighbors=k)
        recommender.build_index(all_foods)
        
        # Find foods similar to each liked food
        similar_foods_map = {}
        for liked_food in self.liked_foods:
            similar = recommender.find_similar_foods(liked_food, k=k)
            for result in similar:
                food_id = result['food'].id
                if food_id not in similar_foods_map:
                    similar_foods_map[food_id] = {
                        'food': result['food'],
                        'score': result['similarity_score'],
                        'count': 0
                    }
                similar_foods_map[food_id]['count'] += 1
                similar_foods_map[food_id]['score'] += result['similarity_score']
        
        # Sort by aggregate score and frequency
        recommendations = sorted(
            similar_foods_map.values(),
            key=lambda x: (x['count'], x['score']),
            reverse=True
        )
        
        return [r['food'] for r in recommendations[:k]]
    
    def get_favorite_nutrient_profile(self):
        """
        Learn user's preferred macronutrient ratios from liked foods
        Returns: {'protein': ratio, 'carbs': ratio, 'fats': ratio}
        """
        if not self.liked_foods:
            return {'protein': 0.30, 'carbs': 0.40, 'fats': 0.30}
        
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fats = 0
        
        for food in self.liked_foods:
            total_calories += food.calories
            total_protein += food.protein
            total_carbs += food.carbs
            total_fats += food.fats
        
        if total_calories == 0:
            return {'protein': 0.30, 'carbs': 0.40, 'fats': 0.30}
        
        return {
            'protein': (total_protein * 4) / total_calories,
            'carbs': (total_carbs * 4) / total_calories,
            'fats': (total_fats * 9) / total_calories
        }


# =====================================================
# 4️⃣ PERSONALIZED MEAL PLAN GENERATOR (KNN-Based)
# =====================================================
class KNNMealPlanner:
    """
    Generate personalized meal plans using KNN recommendations
    combined with user preferences and nutritional targets
    """
    
    def __init__(self, user, profile, target_calories):
        self.user = user
        self.profile = profile
        self.target_calories = target_calories
        self.preference_knn = UserPreferenceKNN(user)
    
    def generate_meal_plan(self):
        """
        Generate meal plan for breakfast, lunch, dinner, snack
        Uses combination of KNN + user preferences
        """
        meal_plan = {}
        
        # Calorie distribution
        meal_calories = {
            'breakfast': self.target_calories * 0.25,
            'lunch': self.target_calories * 0.35,
            'dinner': self.target_calories * 0.30,
            'snack': self.target_calories * 0.10,
        }
        
        # Get all foods filtered by current dietary preference
        dietary_pref = self.profile.dietary_preference if hasattr(self.profile, 'dietary_preference') else None
        all_foods = Food.objects.all()
        if dietary_pref:
            all_foods = all_foods.filter(diet_type=dietary_pref)
        
        # Build KNN for target recommendations
        knn_recommender = KNNFoodRecommender(n_neighbors=5)
        if all_foods.exists():
            knn_recommender.build_index(all_foods)
        
        for meal_type, target_cal in meal_calories.items():
            if not all_foods.exists():
                meal_plan[meal_type] = None
                continue
                
            # Get KNN recommendations for calorie target
            candidates = knn_recommender.recommend_by_target(
                target_cal,
                meal_type=meal_type,
                diet_type=dietary_pref,
                k=10
            )
            
            # Get user preference recommendations
            pref_recommendations = self.preference_knn.get_recommendations_from_preferences(
                all_foods.filter(category=meal_type),
                k=10
            )
            
            # Score and rank candidates
            best_meal = self._score_candidates(candidates, pref_recommendations)
            meal_plan[meal_type] = best_meal
        
        return meal_plan
    
    def _score_candidates(self, knn_candidates, pref_candidates):
        """
        Score candidates combining KNN distance and user preference
        """
        if not knn_candidates:
            return knn_candidates[0]['food'] if knn_candidates else None
        
        # Score KNN candidates
        scored = []
        pref_ids = {f.id for f in pref_candidates}
        
        for candidate in knn_candidates:
            score = candidate['similarity_score']
            
            # Boost score if in user preferences
            if candidate['food'].id in pref_ids:
                score *= 1.5
            
            scored.append({
                'food': candidate['food'],
                'final_score': score
            })
        
        # Return highest scored food
        best = max(scored, key=lambda x: x['final_score'])
        return best['food']


# =====================================================
# 5️⃣ BATCH KNN SIMILARITY MATRIX
# =====================================================
def compute_food_similarity_matrix(foods_queryset=None):
    """
    Compute pairwise similarity matrix for all foods
    Useful for collaborative filtering and recommendations
    Returns: dict {food_id: [similar_foods]}
    """
    if foods_queryset is None:
        foods_queryset = Food.objects.all()
    
    foods = list(foods_queryset)
    if not foods:
        return {}
    
    # Build KNN index
    recommender = KNNFoodRecommender(n_neighbors=len(foods) - 1)
    recommender.build_index(foods_queryset)
    
    # For each food, find similar foods
    similarity_matrix = {}
    
    for food in foods:
        similar = recommender.find_similar_foods(food, k=min(5, len(foods)))
        similarity_matrix[food.id] = [
            {
                'food_id': result['food'].id,
                'food_name': result['food'].name,
                'similarity_score': result['similarity_score']
            }
            for result in similar
        ]
    
    return similarity_matrix


# =====================================================
# 6️⃣ VISUALIZATION & ANALYSIS UTILITIES
# =====================================================
def get_knn_recommendation_stats(user):
    """
    Get statistics about user's KNN recommendations
    for dashboard/analytics
    """
    pref_knn = UserPreferenceKNN(user)
    
    stats = {
        'liked_foods_count': len(pref_knn.liked_foods),
        'avg_feedback_score': FoodFeedback.objects.filter(user=user).aggregate(
            avg=models.Avg('score')
        )['avg'] or 0,
        'preferred_macro_ratio': pref_knn.get_favorite_nutrient_profile(),
        'recommendation_diversity': len(set(f.category for f in pref_knn.liked_foods))
    }
    
    return stats


# =====================================================
# 7️⃣ RANDOM FOREST NUTRITION PREDICTOR
# =====================================================
class RandomForestMealSuitability:
    """
    Random Forest classifier to predict meal suitability
    Models: Is this food suitable for this user? (Binary classification)
    Uses: User feedback history + nutritional features
    """
    
    def __init__(self, user, min_samples=10):
        self.user = user
        self.min_samples = min_samples
        self.model = None
        self.feature_names = [
            'calories', 'protein', 'carbs', 'fats', 
            'fiber', 'calcium', 'sodium', 'vitamin_c'
        ]
        self.scaler = StandardScaler()
        self.feature_vectors = None
    
    def prepare_training_data(self):
        """
        Prepare X (features) and y (labels) from user feedback
        Label: 1 if feedback_score > 2, else 0
        """
        feedbacks = FoodFeedback.objects.filter(user=self.user).select_related('food')
        
        if feedbacks.count() < self.min_samples:
            return None, None, None  # Not enough data
        
        X = []
        y = []
        food_ids = []
        
        for fb in feedbacks:
            vector = Nutrients.get_normalized_vector(fb.food)
            X.append(vector)
            # Binary label: suitable (1) if score > 2, else unsuitable (0)
            y.append(1 if fb.score > 2 else 0)
            food_ids.append(fb.food.id)
        
        return np.array(X), np.array(y), food_ids
    
    def train(self):
        """
        Train Random Forest model on user's feedback history
        Returns: True if training successful, False if insufficient data
        """
        X, y, _ = self.prepare_training_data()
        
        if X is None:
            return False  # Insufficient data
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,       # 100 decision trees
            max_depth=10,           # Limit tree depth
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1               # Use all CPU cores
        )
        
        self.model.fit(X_scaled, y)
        return True
    
    def predict_suitability(self, food, return_probability=False):
        """
        Predict if food is suitable for user
        Returns: suitability_score (0-1) or probability
        """
        if self.model is None:
            return None
        
        food_vector = Nutrients.get_normalized_vector(food)
        food_vector_scaled = self.scaler.transform([food_vector])
        
        prediction = self.model.predict(food_vector_scaled)[0]
        
        if return_probability:
            # Get probability of being suitable (class 1)
            proba = self.model.predict_proba(food_vector_scaled)[0]
            
            # Handle case where model was trained on single class
            if len(proba) == 1:
                # If only one class exists, probability is 1.0 for that class
                probability = float(proba[0]) if self.model.classes_[0] == 1 else 0.0
            else:
                # Normal case: get probability of class 1 (suitable)
                probability = float(proba[1])
            
            return probability
        
        return float(prediction)
    
    def rank_foods(self, foods_list, top_k=10):
        """
        Rank foods by predicted suitability for user
        Returns: [(food, suitability_score), ...]
        """
        if self.model is None:
            return []
        
        ranked = []
        for food in foods_list:
            score = self.predict_suitability(food, return_probability=True)
            if score is not None:
                ranked.append({
                    'food': food,
                    'suitability_score': score,
                    'prediction': 'Suitable' if score > 0.5 else 'Less Suitable'
                })
        
        # Sort by suitability score (descending)
        ranked = sorted(ranked, key=lambda x: x['suitability_score'], reverse=True)
        return ranked[:top_k]
    
    def get_feature_importance(self):
        """
        Get Random Forest feature importances
        Shows which nutritional factors matter most
        Returns: dict {feature_name: importance_score}
        """
        if self.model is None:
            return {}
        
        importances = self.model.feature_importances_
        return {
            name: float(imp) 
            for name, imp in zip(self.feature_names, importances)
        }


# =====================================================
# 8️⃣ RANDOM FOREST MEAL SCORING ENGINE
# =====================================================
class RandomForestMealEngine:
    """
    Complete meal recommendation engine using Random Forest
    Combines:
    - Suitability prediction
    - Feature importance analysis
    - Ranking by ML decision trees
    """
    
    def __init__(self, user, profile, target_calories):
        self.user = user
        self.profile = profile
        self.target_calories = target_calories
        self.rf_models = {}  # One model per meal type
    
    def train_all_models(self):
        """Train separate Random Forest for each meal category"""
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            rf = RandomForestMealSuitability(self.user)
            
            # Only train if sufficient feedback exists
            if rf.train():
                self.rf_models[meal_type] = rf
    
    def recommend_meal(self, meal_type, meal_target_calories):
        """
        Recommend best meal for given type using Random Forest
        """
        # Get candidate foods for this meal type
        candidates = Food.objects.filter(category=meal_type)
        
        if not candidates.exists():
            return None
        
        # Use RF model if available, otherwise return first food
        if meal_type not in self.rf_models:
            return candidates.first()
        
        rf_model = self.rf_models[meal_type]
        
        # Rank foods by suitability
        ranked = rf_model.rank_foods(candidates, top_k=10)
        
        if not ranked:
            return candidates.first()
        
        # Find best match matching calorie target
        best_food = ranked[0]['food']
        best_score = ranked[0]['suitability_score']
        
        for item in ranked:
            food = item['food']
            calories_diff = abs(food.calories - meal_target_calories)
            
            # Prefer foods closer to calorie target
            if calories_diff < abs(best_food.calories - meal_target_calories):
                best_food = food
                best_score = item['suitability_score']
        
        return best_food
    
    def generate_meal_plan(self):
        """Generate daily meal plan using Random Forest scoring"""
        meal_plan = {}
        
        meal_calories = {
            'breakfast': self.target_calories * 0.25,
            'lunch': self.target_calories * 0.35,
            'dinner': self.target_calories * 0.30,
            'snack': self.target_calories * 0.10,
        }
        
        for meal_type, target_cal in meal_calories.items():
            meal_plan[meal_type] = self.recommend_meal(meal_type, target_cal)
        
        return meal_plan
    
    def get_top_recommendations(self, meal_type, k=5):
        """Get top K recommended foods for meal type"""
        if meal_type not in self.rf_models:
            return []
        
        candidates = Food.objects.filter(category=meal_type)
        return self.rf_models[meal_type].rank_foods(candidates, top_k=k)
    
    def get_feature_insights(self):
        """
        Get feature importance insights for each meal type
        Shows what nutrition factors predict user preference
        """
        insights = {}
        
        for meal_type, rf_model in self.rf_models.items():
            importance = rf_model.get_feature_importance()
            insights[meal_type] = {
                'most_important': max(importance, key=importance.get),
                'importance_scores': importance
            }
        
        return insights


# =====================================================
# 9️⃣ RANDOM FOREST STATISTICS & ANALYSIS
# =====================================================
def get_rf_model_stats(user):
    """
    Get Random Forest model statistics and health info
    """
    stats = {}
    
    for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
        rf = RandomForestMealSuitability(user)
        if rf.train():
            feature_imp = rf.get_feature_importance()
            stats[meal_type] = {
                'model_trained': True,
                'top_feature': max(feature_imp, key=feature_imp.get),
                'top_importance': max(feature_imp.values()),
                'feature_importance': feature_imp
            }
        else:
            stats[meal_type] = {
                'model_trained': False,
                'reason': 'Insufficient feedback data'
            }
    
    return stats


def calculate_rf_accuracy_metrics(user):
    """
    Calculate accuracy metrics for Random Forest model
    (Requires sufficient test data)
    """
    rf = RandomForestMealSuitability(user, min_samples=20)
    X, y, _ = rf.prepare_training_data()
    
    if X is None:
        return None
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )
    
    # Train
    X_train_scaled = rf.scaler.fit_transform(X_train)
    X_test_scaled = rf.scaler.transform(X_test)
    
    rf.model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.model.fit(X_train_scaled, y_train)
    
    # Score
    train_accuracy = rf.model.score(X_train_scaled, y_train)
    test_accuracy = rf.model.score(X_test_scaled, y_test)
    
    return {
        'train_accuracy': float(train_accuracy),
        'test_accuracy': float(test_accuracy),
        'samples_used': len(y),
        'training_ratio': 0.7,
        'test_ratio': 0.3
    }


# =====================================================
# 10️⃣ SUPPORT VECTOR MACHINE MEAL CLASSIFIER
# =====================================================
class SVMMealClassifier:
    """
    Support Vector Machine classifier for meal health classification
    Classifies meals as healthy/suitable vs less suitable based on nutritional profile
    Uses SVM with RBF kernel for non-linear classification
    """

    def __init__(self, user, min_samples=10, kernel='rbf'):
        self.user = user
        self.min_samples = min_samples
        self.kernel = kernel
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'calories', 'protein', 'carbs', 'fats',
            'fiber', 'calcium', 'sodium', 'vitamin_c',
            'protein_ratio', 'carb_ratio', 'fat_ratio'  # Add macro ratios
        ]
        self.feature_vectors = None

    def prepare_training_data(self):
        """
        Prepare X (features) and y (labels) from user feedback
        Enhanced features include macro nutrient ratios
        Label: 1 if feedback_score >= 3 (healthy/suitable), else 0
        """
        feedbacks = FoodFeedback.objects.filter(user=self.user).select_related('food')

        if feedbacks.count() < self.min_samples:
            return None, None, None  # Not enough data

        X = []
        y = []
        food_ids = []

        for fb in feedbacks:
            # Basic nutritional features
            basic_vector = Nutrients.get_normalized_vector(fb.food)

            # Calculate macro ratios (as percentages of total calories)
            total_cal = fb.food.calories
            if total_cal > 0:
                protein_ratio = (fb.food.protein * 4) / total_cal
                carb_ratio = (fb.food.carbs * 4) / total_cal
                fat_ratio = (fb.food.fats * 9) / total_cal
            else:
                protein_ratio = carb_ratio = fat_ratio = 0

            # Enhanced feature vector
            enhanced_vector = np.append(basic_vector, [protein_ratio, carb_ratio, fat_ratio])

            X.append(enhanced_vector)
            # Binary label: healthy/suitable (1) if score >= 3, else less suitable (0)
            y.append(1 if fb.score >= 3 else 0)
            food_ids.append(fb.food.id)

        return np.array(X), np.array(y), food_ids

    def train(self):
        """
        Train SVM model on user's feedback history
        Returns: True if training successful, False if insufficient data
        """
        X, y, _ = self.prepare_training_data()

        if X is None:
            return False  # Insufficient data

        # Check if we have more than one class
        unique_classes = len(set(y))
        if unique_classes < 2:
            print(f"Warning: Only {unique_classes} class(es) in training data. SVM needs at least 2 classes.")
            return False  # Cannot train SVM with single class
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train SVM with RBF kernel (good for non-linear relationships)
        self.model = SVC(
            kernel=self.kernel,       # 'rbf', 'linear', 'poly', 'sigmoid'
            C=1.0,                    # Regularization parameter
            gamma='scale',            # Kernel coefficient
            probability=True,         # Enable probability estimates
            random_state=42,
            class_weight='balanced'   # Handle imbalanced classes
        )
        
        self.model.fit(X_scaled, y)
        return True

    def classify_meal_health(self, food, return_probability=False):
        """
        Classify if a meal/food is healthy/suitable for the user
        Returns: classification (0=less suitable, 1=healthy) or probability
        """
        if self.model is None:
            return None

        # Create enhanced feature vector
        basic_vector = Nutrients.get_normalized_vector(food)

        # Calculate macro ratios
        total_cal = food.calories
        if total_cal > 0:
            protein_ratio = (food.protein * 4) / total_cal
            carb_ratio = (food.carbs * 4) / total_cal
            fat_ratio = (food.fats * 9) / total_cal
        else:
            protein_ratio = carb_ratio = fat_ratio = 0

        enhanced_vector = np.append(basic_vector, [protein_ratio, carb_ratio, fat_ratio])
        enhanced_vector_scaled = self.scaler.transform([enhanced_vector])

        if return_probability:
            # Get probability of being healthy/suitable (class 1)
            proba = self.model.predict_proba(enhanced_vector_scaled)[0]

            # Handle single class case
            if len(proba) == 1:
                probability = float(proba[0]) if self.model.classes_[0] == 1 else 0.0
            else:
                probability = float(proba[1])

            return probability

        prediction = self.model.predict(enhanced_vector_scaled)[0]
        return int(prediction)

    def filter_healthy_meals(self, foods_list, threshold=0.6):
        """
        Filter foods to only include healthy/suitable ones
        Returns: list of foods that meet the health threshold
        """
        if self.model is None:
            return foods_list  # Return all if no model

        healthy_foods = []
        for food in foods_list:
            health_score = self.classify_meal_health(food, return_probability=True)
            if health_score is not None and health_score >= threshold:
                healthy_foods.append(food)

        return healthy_foods

    def rank_meals_by_health(self, foods_list, top_k=10):
        """
        Rank foods by health suitability score
        Returns: [(food, health_score), ...] sorted by health score
        """
        if self.model is None:
            return []

        ranked = []
        for food in foods_list:
            health_score = self.classify_meal_health(food, return_probability=True)
            if health_score is not None:
                ranked.append({
                    'food': food,
                    'health_score': health_score,
                    'classification': 'Healthy' if health_score >= 0.5 else 'Less Suitable'
                })

        # Sort by health score (descending)
        ranked = sorted(ranked, key=lambda x: x['health_score'], reverse=True)
        return ranked[:top_k]

    def get_support_vectors_info(self):
        """
        Get information about the support vectors
        Useful for understanding decision boundaries
        """
        if self.model is None:
            return {}

        return {
            'n_support_vectors': self.model.n_support_,
            'total_support_vectors': sum(self.model.n_support_),
            'support_vector_indices': self.model.support_,
            'dual_coefficients': self.model.dual_coef_,
        }


# =====================================================
# 11️⃣ SVM MEAL RECOMMENDATION ENGINE
# =====================================================
class SVMMealEngine:
    """
    Complete meal recommendation engine using SVM classification
    Combines health classification with nutritional filtering
    """

    def __init__(self, user, profile, target_calories, health_threshold=0.6):
        self.user = user
        self.profile = profile
        self.target_calories = target_calories
        self.health_threshold = health_threshold
        self.svm_models = {}  # One SVM per meal type

    def train_all_models(self):
        """Train separate SVM for each meal category"""
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            svm = SVMMealClassifier(self.user)

            # Only train if sufficient feedback exists
            if svm.train():
                self.svm_models[meal_type] = svm

    def recommend_healthy_meal(self, meal_type, meal_target_calories):
        """
        Recommend healthiest meal for given type using SVM
        """
        # Get candidate foods for this meal type
        candidates = Food.objects.filter(category=meal_type)

        if not candidates.exists():
            return None

        # Use SVM model if available, otherwise return first food
        if meal_type not in self.svm_models:
            return candidates.first()

        svm_model = self.svm_models[meal_type]

        # Rank foods by health score
        ranked = svm_model.rank_meals_by_health(candidates, top_k=10)

        if not ranked:
            return candidates.first()

        # Find best match that also meets calorie target
        best_food = ranked[0]['food']
        best_score = ranked[0]['health_score']

        for item in ranked:
            food = item['food']
            calories_diff = abs(food.calories - meal_target_calories)

            # Prefer foods closer to calorie target
            if calories_diff < abs(best_food.calories - meal_target_calories):
                best_food = food
                best_score = item['health_score']

        return best_food

    def generate_healthy_meal_plan(self):
        """Generate meal plan prioritizing healthy foods"""
        meal_plan = {}

        meal_calories = {
            'breakfast': self.target_calories * 0.25,
            'lunch': self.target_calories * 0.35,
            'dinner': self.target_calories * 0.30,
            'snack': self.target_calories * 0.10,
        }

        for meal_type, target_cal in meal_calories.items():
            meal_plan[meal_type] = self.recommend_healthy_meal(meal_type, target_cal)

        return meal_plan

    def get_healthy_recommendations(self, meal_type, k=5):
        """Get top K healthiest foods for meal type"""
        if meal_type not in self.svm_models:
            return []

        candidates = Food.objects.filter(category=meal_type)
        return self.svm_models[meal_type].rank_meals_by_health(candidates, top_k=k)

    def get_health_insights(self):
        """
        Get health classification insights for each meal type
        """
        insights = {}

        for meal_type, svm_model in self.svm_models.items():
            support_info = svm_model.get_support_vectors_info()
            insights[meal_type] = {
                'model_trained': True,
                'support_vectors': support_info.get('total_support_vectors', 0),
                'health_focused': True
            }
        else:
            insights[meal_type] = {
                'model_trained': False,
                'reason': 'Insufficient feedback data'
            }

        return insights


# =====================================================
# 12️⃣ SVM STATISTICS & ANALYSIS
# =====================================================
def get_svm_model_stats(user):
    """
    Get SVM model statistics and health classification info
    """
    stats = {}

    for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
        svm = SVMMealClassifier(user)
        if svm.train():
            support_info = svm.get_support_vectors_info()
            stats[meal_type] = {
                'model_trained': True,
                'kernel': svm.kernel,
                'support_vectors': support_info.get('total_support_vectors', 0),
                'feature_count': len(svm.feature_names)
            }
        else:
            stats[meal_type] = {
                'model_trained': False,
                'reason': 'Insufficient feedback data'
            }

    return stats


def calculate_svm_accuracy_metrics(user):
    """
    Calculate accuracy metrics for SVM model
    (Requires sufficient test data)
    """
    svm = SVMMealClassifier(user, min_samples=20)
    X, y, _ = svm.prepare_training_data()

    if X is None:
        return None

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    # Train
    X_train_scaled = svm.scaler.fit_transform(X_train)
    X_test_scaled = svm.scaler.transform(X_test)

    svm.model = SVC(kernel='rbf', C=1.0, gamma='scale', probability=True, random_state=42)
    svm.model.fit(X_train_scaled, y_train)

    # Score
    train_accuracy = svm.model.score(X_train_scaled, y_train)
    test_accuracy = svm.model.score(X_test_scaled, y_test)

    return {
        'train_accuracy': float(train_accuracy),
        'test_accuracy': float(test_accuracy),
        'samples_used': len(y),
        'training_ratio': 0.7,
        'test_ratio': 0.3,
        'kernel': 'rbf'
    }


# =====================================================
# 13️⃣ LINEAR REGRESSION MEAL PREDICTOR
# =====================================================
class LinearRegressionMealPredictor:
    """
    Linear Regression model for predicting meal suitability scores
    Predicts how well a meal fits user's nutritional needs and preferences
    Uses multiple linear regression for continuous suitability scoring
    """

    def __init__(self, user, min_samples=5):
        self.user = user
        self.min_samples = min_samples
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'calories', 'protein', 'carbs', 'fats',
            'fiber', 'calcium', 'sodium', 'vitamin_c',
            'protein_ratio', 'carb_ratio', 'fat_ratio'
        ]
        self.target_name = 'suitability_score'
        self.feature_importance = {}

    def prepare_training_data(self):
        """
        Prepare X (nutritional features) and y (suitability scores) from user feedback
        Suitability score is derived from feedback rating (1-5 scale)
        """
        feedbacks = FoodFeedback.objects.filter(user=self.user).select_related('food')

        if feedbacks.count() < self.min_samples:
            return None, None, None

        X = []
        y = []
        food_ids = []

        for fb in feedbacks:
            # Basic nutritional features
            basic_vector = Nutrients.get_normalized_vector(fb.food)

            # Calculate macro ratios
            total_cal = fb.food.calories
            if total_cal > 0:
                protein_ratio = (fb.food.protein * 4) / total_cal
                carb_ratio = (fb.food.carbs * 4) / total_cal
                fat_ratio = (fb.food.fats * 9) / total_cal
            else:
                protein_ratio = carb_ratio = fat_ratio = 0

            # Enhanced feature vector
            enhanced_vector = np.append(basic_vector, [protein_ratio, carb_ratio, fat_ratio])

            X.append(enhanced_vector)
            # Convert feedback score (1-5) to suitability score (0-1)
            suitability_score = (fb.score - 1) / 4.0  # Normalize to 0-1 range
            y.append(suitability_score)
            food_ids.append(fb.food.id)

        return np.array(X), np.array(y), food_ids

    def train(self):
        """
        Train Linear Regression model on user's feedback history
        Returns: True if training successful, False if insufficient data
        """
        X, y, _ = self.prepare_training_data()

        if X is None or len(X) < self.min_samples:
            return False

        # Normalize features
        X_scaled = self.scaler.fit_transform(X)

        # Train Linear Regression
        self.model = LinearRegression(
            fit_intercept=True
            # normalize parameter removed - use StandardScaler instead
        )

        self.model.fit(X_scaled, y)

        # Store feature importance (coefficients)
        self.feature_importance = {
            name: float(coef)
            for name, coef in zip(self.feature_names, self.model.coef_)
        }

        return True

    def predict_suitability(self, food):
        """
        Predict suitability score for a food (0-1 scale)
        Higher scores indicate better suitability for user
        """
        if self.model is None:
            return None

        # Create feature vector
        basic_vector = Nutrients.get_normalized_vector(food)

        # Calculate macro ratios
        total_cal = food.calories
        if total_cal > 0:
            protein_ratio = (food.protein * 4) / total_cal
            carb_ratio = (food.carbs * 4) / total_cal
            fat_ratio = (food.fats * 9) / total_cal
        else:
            protein_ratio = carb_ratio = fat_ratio = 0

        enhanced_vector = np.append(basic_vector, [protein_ratio, carb_ratio, fat_ratio])
        enhanced_vector_scaled = self.scaler.transform([enhanced_vector])

        # Predict suitability score
        prediction = self.model.predict(enhanced_vector_scaled)[0]

        # Clip to valid range (0-1)
        return float(np.clip(prediction, 0.0, 1.0))

    def rank_foods_by_suitability(self, foods_list, top_k=10):
        """
        Rank foods by predicted suitability score
        Returns: [(food, suitability_score), ...] sorted by score descending
        """
        if self.model is None:
            return []

        ranked = []
        for food in foods_list:
            score = self.predict_suitability(food)
            if score is not None:
                ranked.append({
                    'food': food,
                    'suitability_score': score,
                    'rating': 'Excellent' if score >= 0.8 else
                             'Good' if score >= 0.6 else
                             'Fair' if score >= 0.4 else 'Poor'
                })

        # Sort by suitability score (descending)
        ranked = sorted(ranked, key=lambda x: x['suitability_score'], reverse=True)
        return ranked[:top_k]

    def get_feature_importance(self):
        """
        Get feature importance (coefficients) from the linear model
        Shows which nutritional factors most influence suitability
        """
        return self.feature_importance

    def get_model_coefficients(self):
        """
        Get detailed model information
        """
        if self.model is None:
            return {}

        return {
            'coefficients': self.feature_importance,
            'intercept': float(self.model.intercept_),
            'n_features': len(self.feature_names),
            'r_squared': None  # Would need test data to calculate
        }


# =====================================================
# 14️⃣ LINEAR REGRESSION NUTRIENT ESTIMATOR
# =====================================================
class LinearRegressionNutrientEstimator:
    """
    Linear Regression model for estimating ideal nutrient distributions
    Predicts optimal macronutrient ratios and nutrient targets based on user profile
    """

    def __init__(self, user, min_samples=5):
        self.user = user
        self.min_samples = min_samples
        self.models = {}  # Separate models for each nutrient target
        self.scaler = StandardScaler()
        self.input_features = [
            'age', 'weight', 'height', 'activity_level',
            'goal', 'gender', 'current_calories'
        ]

    def prepare_training_data(self):
        """
        Prepare training data from user's meal history and profile
        Uses historical meal data to learn nutrient patterns
        """
        # Get user's meal history
        meal_history = MealHistory.objects.filter(user=self.user).select_related('food')

        if meal_history.count() < self.min_samples:
            return None

        # Get user profile for input features
        try:
            profile = UserProfile.objects.get(user=self.user)
        except UserProfile.DoesNotExist:
            return None

        # Aggregate nutritional data from meal history
        total_meals = meal_history.count()
        avg_calories = meal_history.aggregate(avg=models.Avg('calories'))['avg'] or 0
        avg_protein = meal_history.aggregate(avg=models.Avg('protein'))['avg'] or 0
        avg_carbs = meal_history.aggregate(avg=models.Avg('carbs'))['avg'] or 0
        avg_fats = meal_history.aggregate(avg=models.Avg('fats'))['avg'] or 0

        # Create input features vector
        input_vector = np.array([
            profile.age,
            profile.weight,
            profile.height,
            profile.activity_level,
            profile.goal,  # Could be encoded as numeric
            1 if profile.gender == 'M' else 0,  # Gender encoding
            avg_calories
        ])

        # Create target values (nutrient ratios)
        if avg_calories > 0:
            protein_ratio = (avg_protein * 4) / avg_calories
            carb_ratio = (avg_carbs * 4) / avg_calories
            fat_ratio = (avg_fats * 9) / avg_calories
        else:
            protein_ratio = carb_ratio = fat_ratio = 0

        targets = {
            'protein_ratio': protein_ratio,
            'carb_ratio': carb_ratio,
            'fat_ratio': fat_ratio,
            'protein_grams': avg_protein,
            'carb_grams': avg_carbs,
            'fat_grams': avg_fats
        }

        return input_vector.reshape(1, -1), targets

    def train(self):
        """
        Train separate linear regression models for each nutrient target
        Uses user's historical data to learn optimal nutrient distributions
        """
        X, targets = self.prepare_training_data()

        if X is None:
            return False

        # For demonstration, we'll use synthetic training data
        # In a real scenario, you'd need multiple users or time-series data
        # Here we'll create a simple model based on general nutritional guidelines

        # Normalize input features
        X_scaled = self.scaler.fit_transform(X)

        # Create models for each nutrient target
        nutrient_targets = {
            'protein_ratio': 0.25,  # 25% of calories from protein
            'carb_ratio': 0.50,     # 50% of calories from carbs
            'fat_ratio': 0.25,      # 25% of calories from fats
        }

        for target_name, default_value in nutrient_targets.items():
            model = LinearRegression(fit_intercept=True)
            # For single sample, we'll use the default value
            # In practice, you'd need more data points
            y = np.array([default_value])
            model.fit(X_scaled, y)
            self.models[target_name] = model

        return True

    def estimate_nutrient_distribution(self, profile, target_calories):
        """
        Estimate ideal nutrient distribution for user
        Returns: dict with recommended macro ratios and gram amounts
        """
        if not self.models:
            # Return default values if no trained models
            return self._get_default_distribution(target_calories)

        # Create input features
        input_vector = np.array([
            profile.age,
            profile.weight,
            profile.height,
            profile.activity_level,
            profile.goal,
            1 if profile.gender == 'M' else 0,
            target_calories
        ])

        input_scaled = self.scaler.transform([input_vector])

        # Predict ratios
        protein_ratio = self.models['protein_ratio'].predict(input_scaled)[0]
        carb_ratio = self.models['carb_ratio'].predict(input_scaled)[0]
        fat_ratio = self.models['fat_ratio'].predict(input_scaled)[0]

        # Normalize ratios to ensure they sum to 1
        total_ratio = protein_ratio + carb_ratio + fat_ratio
        if total_ratio > 0:
            protein_ratio /= total_ratio
            carb_ratio /= total_ratio
            fat_ratio /= total_ratio

        # Calculate gram amounts
        protein_grams = (target_calories * protein_ratio) / 4
        carb_grams = (target_calories * carb_ratio) / 4
        fat_grams = (target_calories * fat_ratio) / 9

        return {
            'protein_ratio': float(protein_ratio),
            'carb_ratio': float(carb_ratio),
            'fat_ratio': float(fat_ratio),
            'protein_grams': float(protein_grams),
            'carb_grams': float(carb_grams),
            'fat_grams': float(fat_grams),
            'total_calories': float(target_calories)
        }

    def _get_default_distribution(self, target_calories):
        """
        Return default nutrient distribution based on general guidelines
        """
        # Standard macronutrient distribution
        protein_ratio = 0.25
        carb_ratio = 0.50
        fat_ratio = 0.25

        return {
            'protein_ratio': protein_ratio,
            'carb_ratio': carb_ratio,
            'fat_ratio': fat_ratio,
            'protein_grams': (target_calories * protein_ratio) / 4,
            'carb_grams': (target_calories * carb_ratio) / 4,
            'fat_grams': (target_calories * fat_ratio) / 9,
            'total_calories': target_calories
        }

    def get_nutrient_recommendations(self, profile, target_calories):
        """
        Get comprehensive nutrient recommendations
        """
        distribution = self.estimate_nutrient_distribution(profile, target_calories)

        return {
            'macronutrient_ratios': {
                'protein': distribution['protein_ratio'],
                'carbohydrates': distribution['carb_ratio'],
                'fats': distribution['fat_ratio']
            },
            'daily_targets': {
                'protein_grams': distribution['protein_grams'],
                'carb_grams': distribution['carb_grams'],
                'fat_grams': distribution['fat_grams'],
                'calories': distribution['total_calories']
            },
            'meal_distribution': {
                'breakfast': {
                    'protein': distribution['protein_grams'] * 0.25,
                    'carbs': distribution['carb_grams'] * 0.25,
                    'fats': distribution['fat_grams'] * 0.25,
                    'calories': target_calories * 0.25
                },
                'lunch': {
                    'protein': distribution['protein_grams'] * 0.35,
                    'carbs': distribution['carb_grams'] * 0.35,
                    'fats': distribution['fat_grams'] * 0.35,
                    'calories': target_calories * 0.35
                },
                'dinner': {
                    'protein': distribution['protein_grams'] * 0.30,
                    'carbs': distribution['carb_grams'] * 0.30,
                    'fats': distribution['fat_grams'] * 0.30,
                    'calories': target_calories * 0.30
                },
                'snacks': {
                    'protein': distribution['protein_grams'] * 0.10,
                    'carbs': distribution['carb_grams'] * 0.10,
                    'fats': distribution['fat_grams'] * 0.10,
                    'calories': target_calories * 0.10
                }
            }
        }


# =====================================================
# 15️⃣ LINEAR REGRESSION MEAL PLANNING ENGINE
# =====================================================
class LinearRegressionMealPlanner:
    """
    Complete meal planning engine using Linear Regression predictions
    Combines suitability prediction with nutrient estimation
    """

    def __init__(self, user, profile, target_calories):
        self.user = user
        self.profile = profile
        self.target_calories = target_calories
        self.predictor = LinearRegressionMealPredictor(user)
        self.estimator = LinearRegressionNutrientEstimator(user)

    def train_models(self):
        """Train both predictor and estimator models"""
        predictor_trained = self.predictor.train()
        estimator_trained = self.estimator.train()

        return predictor_trained or estimator_trained  # At least one should work

    def generate_optimized_meal_plan(self):
        """
        Generate meal plan using Linear Regression optimization
        """
        # Get nutrient distribution recommendations
        nutrient_plan = self.estimator.get_nutrient_recommendations(
            self.profile, self.target_calories
        )

        meal_plan = {}

        # Generate meals for each type
        for meal_type, targets in nutrient_plan['meal_distribution'].items():
            meal_plan[meal_type] = self._select_best_meal_for_targets(
                meal_type, targets
            )

        return meal_plan, nutrient_plan

    def _select_best_meal_for_targets(self, meal_type, targets):
        """
        Select best meal for given nutritional targets
        """
        # Get candidate foods for this meal type
        candidates = Food.objects.filter(category=meal_type)

        if not candidates.exists():
            return None

        # Use predictor to rank foods by suitability
        if self.predictor.model is not None:
            ranked_foods = self.predictor.rank_foods_by_suitability(candidates, top_k=5)
            if ranked_foods:
                return ranked_foods[0]['food']

        # Fallback: select food closest to calorie target
        target_calories = targets['calories']
        best_food = None
        best_diff = float('inf')

        for food in candidates:
            cal_diff = abs(food.calories - target_calories)
            if cal_diff < best_diff:
                best_diff = cal_diff
                best_food = food

        return best_food

    def get_meal_suitability_scores(self, meal_type, limit=10):
        """
        Get suitability scores for foods in a meal category
        """
        foods = Food.objects.filter(category=meal_type)[:limit]

        if self.predictor.model is None:
            return []

        return self.predictor.rank_foods_by_suitability(foods, top_k=limit)

    def get_nutrient_insights(self):
        """
        Get insights about nutrient preferences and predictions
        """
        nutrient_plan = self.estimator.get_nutrient_recommendations(
            self.profile, self.target_calories
        )

        predictor_insights = {}
        if self.predictor.model is not None:
            predictor_insights = {
                'feature_importance': self.predictor.get_feature_importance(),
                'model_coefficients': self.predictor.get_model_coefficients()
            }

        return {
            'nutrient_distribution': nutrient_plan,
            'suitability_model': predictor_insights,
            'optimization_ready': self.predictor.model is not None
        }


# =====================================================
# 16️⃣ LINEAR REGRESSION STATISTICS & ANALYSIS
# =====================================================
def get_linear_regression_stats(user):
    """
    Get Linear Regression model statistics
    """
    stats = {}

    for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
        predictor = LinearRegressionMealPredictor(user)
        estimator = LinearRegressionNutrientEstimator(user)

        predictor_trained = predictor.train()
        estimator_trained = estimator.train()

        stats[meal_type] = {
            'predictor_trained': predictor_trained,
            'estimator_trained': estimator_trained,
            'feature_count': len(predictor.feature_names) if predictor_trained else 0,
        }

        if predictor_trained:
            stats[meal_type]['top_features'] = sorted(
                predictor.get_feature_importance().items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:3]

    return stats


def calculate_linear_regression_metrics(user):
    """
    Calculate Linear Regression performance metrics
    """
    predictor = LinearRegressionMealPredictor(user, min_samples=10)
    X, y, _ = predictor.prepare_training_data()

    if X is None or len(X) < 10:
        return None

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    # Train
    X_train_scaled = predictor.scaler.fit_transform(X_train)
    X_test_scaled = predictor.scaler.transform(X_test)

    predictor.model = LinearRegression()
    predictor.model.fit(X_train_scaled, y_train)

    # Predict
    y_pred = predictor.model.predict(X_test_scaled)

    # Calculate metrics
    from sklearn.metrics import mean_squared_error, r2_score

    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    return {
        'mean_squared_error': float(mse),
        'r_squared': float(r2),
        'samples_used': len(y),
        'test_size': len(y_test),
        'training_ratio': 0.7,
        'test_ratio': 0.3
    }
