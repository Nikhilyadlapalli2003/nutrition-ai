def calculate_bmr(profile):

    if not profile.age or not profile.weight or not profile.height:
        return 0

    if profile.gender == "male":
        bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) + 5
    else:
        bmr = (10 * profile.weight) + (6.25 * profile.height) - (5 * profile.age) - 161

    return round(bmr, 2)


def calculate_tdee(bmr, activity_level):

    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
    }

    multiplier = activity_multipliers.get(activity_level, 1.2)
    return round(bmr * multiplier, 2)


def adjust_calories_by_goal(tdee, goal):

    if goal == "loss":
        return round(tdee - 500, 2)
    elif goal == "gain":
        return round(tdee + 300, 2)

    return round(tdee, 2)


def calculate_macros(calories):

    protein_cal = calories * 0.30
    carbs_cal = calories * 0.40
    fats_cal = calories * 0.30

    protein_g = protein_cal / 4
    carbs_g = carbs_cal / 4
    fats_g = fats_cal / 9

    return {
        "protein": round(protein_g, 2),
        "carbs": round(carbs_g, 2),
        "fats": round(fats_g, 2),
    }