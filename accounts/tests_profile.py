from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import UserProfile


def create_user_and_login(client):
    user = User.objects.create_user(username="tester", password="pass1234")
    client.login(username="tester", password="pass1234")
    return user


class ProfileValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user_and_login(self.client)

    def test_valid_profile_submission(self):
        response = self.client.post(
            "/accounts/profile/",
            {
                "age": "25",
                "gender": "male",
                "height": "175",
                "weight": "70",
                "activity_level": "moderate",
                "health_condition": "none",
                "dietary_preference": "veg",
                "goal": "loss",
            },
            follow=True,
        )
        self.assertContains(response, "Profile saved successfully!")
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.age, 25)
        self.assertEqual(profile.gender, "male")
        self.assertEqual(profile.height, 175)
        self.assertEqual(profile.weight, 70)
        self.assertEqual(profile.activity_level, "moderate")
        self.assertEqual(profile.health_condition, "none")
        # health_condition and medical_conditions should remain synced
        self.assertEqual(profile.medical_conditions, "none")
        self.assertEqual(profile.dietary_preference, "veg")
        self.assertEqual(profile.goal, "loss")

    def test_get_profile_contains_condition_choices(self):
        """GET request should include condition choices in context"""
        response = self.client.get("/accounts/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('condition_choices', response.context)
        codes = [c for c,l in response.context['condition_choices']]
        # ensure 'diabetes' and 'obesity' present
        self.assertIn('diabetes', codes)
        self.assertIn('obesity', codes)

    def post_invalid(self, data):
        response = self.client.post("/accounts/profile/", data, follow=True)
        self.assertContains(response, "Enter Correctly")
        # ensure profile values did not update to invalid ones
        profile = UserProfile.objects.get(user=self.user)
        for key in ("age", "height", "weight"):
            if key in data:
                self.assertNotEqual(getattr(profile, key), data[key])
        return response

    def test_age_out_of_range(self):
        self.post_invalid({"age": "5", "gender": "male", "height": "150", "weight": "60",
                           "activity_level": "light", "dietary_preference": "veg", "goal": "loss"})
        self.post_invalid({"age": "150", "gender": "male", "height": "150", "weight": "60",
                           "activity_level": "light", "dietary_preference": "veg", "goal": "loss"})
        self.post_invalid({"age": "abc", "gender": "male", "height": "150", "weight": "60",
                           "activity_level": "light", "dietary_preference": "veg", "goal": "loss"})

    def test_height_out_of_range(self):
        self.post_invalid({"age": "30", "gender": "female", "height": "50", "weight": "60",
                           "activity_level": "active", "dietary_preference": "nonveg", "goal": "gain"})
        self.post_invalid({"age": "30", "gender": "female", "height": "300", "weight": "60",
                           "activity_level": "active", "dietary_preference": "nonveg", "goal": "gain"})
        self.post_invalid({"age": "30", "gender": "female", "height": "abc", "weight": "60",
                           "activity_level": "active", "dietary_preference": "nonveg", "goal": "gain"})

    def test_weight_out_of_range(self):
        self.post_invalid({"age": "30", "gender": "female", "height": "170", "weight": "10",
                           "activity_level": "active", "dietary_preference": "keto", "goal": "maintain"})
        self.post_invalid({"age": "30", "gender": "female", "height": "170", "weight": "500",
                           "activity_level": "active", "dietary_preference": "keto", "goal": "maintain"})
        self.post_invalid({"age": "30", "gender": "female", "height": "170", "weight": "abc",
                           "activity_level": "active", "dietary_preference": "keto", "goal": "maintain"})

    def test_required_fields_missing(self):
        self.post_invalid({"age": "30", "gender": "", "height": "170", "weight": "70",
                           "activity_level": "", "dietary_preference": "", "goal": "", "health_condition": ""})
