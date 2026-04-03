from nutrition.models import FoodFeedback
from django.contrib.auth.models import User
from collections import defaultdict


def get_user_vector(user):
    """
    Create a dictionary of {food_id: score}
    """
    feedbacks = FoodFeedback.objects.filter(user=user)

    vector = {}
    for fb in feedbacks:
        vector[fb.food.id] = fb.score

    return vector


def cosine_similarity(vec1, vec2):
    """
    Manual cosine similarity
    """
    common_items = set(vec1.keys()) & set(vec2.keys())

    if not common_items:
        return 0

    dot_product = sum(vec1[i] * vec2[i] for i in common_items)

    magnitude1 = sum(v ** 2 for v in vec1.values()) ** 0.5
    magnitude2 = sum(v ** 2 for v in vec2.values()) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot_product / (magnitude1 * magnitude2)


def get_collaborative_recommendations(current_user):
    """
    Find foods liked by similar users
    """

    current_vector = get_user_vector(current_user)

    similarity_scores = {}

    for user in User.objects.exclude(id=current_user.id):
        other_vector = get_user_vector(user)
        similarity = cosine_similarity(current_vector, other_vector)

        if similarity > 0:
            similarity_scores[user] = similarity

    # Sort similar users
    similar_users = sorted(
        similarity_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    recommended_food_ids = set()

    for user, score in similar_users[:3]:  # Top 3 similar users
        liked_foods = FoodFeedback.objects.filter(
            user=user,
            score__gt=0
        )

        for fb in liked_foods:
            recommended_food_ids.add(fb.food.id)

    return recommended_food_ids