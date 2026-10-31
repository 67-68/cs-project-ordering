# Test Plan — Food Ordering System

Module under test: `filter_foods(foods, criteria)` in `food_model.py`.
All results below were produced by running the function against `data/foods.json`
(10 food records, 5 coupons).

---

## Test 1 — Filter food by allergen

| Field | Content |
|---|---|
| **Purpose** | To ensure the allergen filter removes every food containing a selected allergen, and leaves the list untouched when no allergen is selected. |
| **Test Data (normal)** | `criteria = {'food_component': ['milk'], 'distance_km': ['any']}` |
| **Expected outcome (normal)** | All foods without milk are returned; foods containing milk are excluded. |
| **Actual outcome (normal)** | 8 foods returned: Americano, Pour-over Yirgacheffe, Cold Brew, Oat Milk Latte, Peanut Butter Toast, Shrimp Wonton Noodles, Plain Water, Sparkling Water. Latte and Iced Matcha Latte excluded. |
| **Test Data (abnormal)** | `criteria = {'food_component': ['bogus'], 'distance_km': ['any']}` |
| **Expected outcome (abnormal)** | An error message identifying the unknown allergen. |
| **Actual outcome (abnormal)** | No error raised. All 10 foods returned because no record contains `bogus`, so nothing is excluded. |

## Test 2 — Filter food by distance radius

| Field | Content |
|---|---|
| **Purpose** | To ensure the distance filter acts as a radius rather than an exact match. |
| **Test Data (normal)** | `criteria = {'food_component': [], 'distance_km': ['2']}` |
| **Expected outcome (normal)** | All foods at 2 km or closer are returned. |
| **Actual outcome (normal)** | 6 foods returned: Americano (1 km), Latte (2 km), Cold Brew (1 km), Peanut Butter Toast (1 km), Plain Water (0 km), Sparkling Water (1 km). |
| **Test Data (abnormal)** | `criteria = {'food_component': [], 'distance_km': ['abc']}` |
| **Expected outcome (abnormal)** | An error message stating the distance value is invalid. |
| **Actual outcome (abnormal)** | Unhandled `ValueError: invalid literal for int() with base 10: 'abc'` raised at the `min(int(v) for v in wanted)` step. No error message shown. |

## Test 3 — Combined criteria (allergen + distance)

| Field | Content |
|---|---|
| **Purpose** | To ensure multiple criteria are applied together and each one narrows the result of the previous one. |
| **Test Data (normal)** | `criteria = {'food_component': ['milk'], 'distance_km': ['2']}` |
| **Expected outcome (normal)** | Foods that contain no milk **and** are within 2 km. |
| **Actual outcome (normal)** | 5 foods returned: Americano, Cold Brew, Peanut Butter Toast, Plain Water, Sparkling Water. |
| **Test Data (abnormal)** | `criteria = {'colour': ['red']}` |
| **Expected outcome (abnormal)** | An error message naming the unsupported criterion. |
| **Actual outcome (abnormal)** | No error raised. An empty list is returned; one `logging.error` line is written per food record. |

---

## Known gaps found by this plan

1. `distance_km` is converted with `int()` before any validation, so a non-numeric
   value raises `ValueError` instead of producing a message.
2. Unsupported criterion names and unknown allergen values fail silently
   (empty list / no filtering) rather than reporting an error to the caller.
3. `filter_foods` performs no user-facing output at all; the only error channel is `logging`. Any test expecting an on-screen message will not match.
