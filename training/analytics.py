"""
training/analytics.py

Pure computation functions for IronOS analytics.
No LLM calls, no Celery tasks — DB reads only.
"""

from datetime import date, timedelta

from django.db.models import Avg, Max, Q, Sum
from django.utils import timezone

from accounts.models import UserProfile
from training.models import (
    BodyCompositionEntry,
    BodyweightEntry,
    CardioSession,
    HeartRateEntry,
    NutritionTarget,
    SessionSet,
    Session,
)


# ---------------------------------------------------------------------------
# 1. estimate_1rm
# ---------------------------------------------------------------------------

def estimate_1rm(weight: float, reps: int, formula: str = 'epley') -> float:
    """
    Estimate 1-rep max from a given weight and rep count.

    Formulas:
      - 'epley'   : weight * (1 + reps / 30)  [returns weight directly if reps == 1]
      - 'brzycki' : weight * (36 / (37 - reps)) [raises ValueError if reps >= 37]
    """
    if formula == 'epley':
        if reps == 1:
            return round(float(weight), 2)
        return round(float(weight) * (1 + reps / 30), 2)

    elif formula == 'brzycki':
        if reps >= 37:
            raise ValueError(
                f"Brzycki formula is undefined for reps >= 37 (got {reps})."
            )
        return round(float(weight) * (36 / (37 - reps)), 2)

    else:
        raise ValueError(f"Unknown formula '{formula}'. Use 'epley' or 'brzycki'.")


# ---------------------------------------------------------------------------
# 2. weekly_volume_by_muscle
# ---------------------------------------------------------------------------

def weekly_volume_by_muscle(user, start_date: date, end_date: date) -> dict:
    """
    Return {muscle_name: total_volume} for working sets in [start_date, end_date].
    Volume = sum of weight * reps per set.
    Keyed by exercise.primary_muscle, sorted alphabetically.
    """
    sets = (
        SessionSet.objects
        .filter(
            session__user=user,
            session__date__gte=start_date,
            session__date__lte=end_date,
            set_type='working',
        )
        .select_related('exercise')
    )

    volume: dict[str, float] = {}
    for s in sets:
        muscle = s.exercise.primary_muscle
        volume[muscle] = volume.get(muscle, 0.0) + float(s.weight) * s.reps

    return dict(sorted(volume.items()))


# ---------------------------------------------------------------------------
# 3. lift_history
# ---------------------------------------------------------------------------

def lift_history(user, exercise, limit: int = 20) -> list:
    """
    Return the last `limit` sets for `exercise` (all set_types), most recent first.
    Each entry: {date, weight, reps, estimated_1rm, set_type}.
    """
    sets = (
        SessionSet.objects
        .filter(session__user=user, exercise=exercise)
        .select_related('session')
        .order_by('-session__date', '-session__created_at', '-set_index')
        [:limit]
    )

    result = []
    for s in sets:
        result.append({
            'date': s.session.date,
            'weight': float(s.weight),
            'reps': s.reps,
            'estimated_1rm': estimate_1rm(float(s.weight), s.reps, formula='epley'),
            'set_type': s.set_type,
        })
    return result


# ---------------------------------------------------------------------------
# 4. tdee
# ---------------------------------------------------------------------------

def tdee(user) -> float:
    """
    Estimate Total Daily Energy Expenditure using Mifflin-St Jeor + activity multiplier
    + cardio expenditure from the last 7 days.

    Raises ValueError if no UserProfile or no weight data.
    """
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        raise ValueError("User has no profile")

    # --- Weight (kg) ---
    bw_entry = BodyweightEntry.objects.filter(user=user).order_by('-date').first()
    if bw_entry is not None:
        weight_kg = float(bw_entry.weight)
    else:
        bc_entry = (
            BodyCompositionEntry.objects
            .filter(user=user, weight_kg__isnull=False)
            .order_by('-date')
            .first()
        )
        if bc_entry is None:
            raise ValueError("No weight data available")
        weight_kg = float(bc_entry.weight_kg)

    # --- Age ---
    today = date.today()
    dob = profile.date_of_birth
    if dob is not None:
        age = (today - dob).days // 365
    else:
        age = 30  # sensible fallback when DOB is unknown

    # --- Height ---
    height_cm = float(profile.height_cm) if profile.height_cm is not None else 170.0

    # --- BMR (Mifflin-St Jeor) ---
    bmr_male = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    bmr_female = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    sex = profile.sex
    if sex == 'male':
        bmr = bmr_male
    elif sex == 'female':
        bmr = bmr_female
    else:
        bmr = (bmr_male + bmr_female) / 2

    # --- Activity multiplier ---
    multipliers = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extremely_active': 1.9,
    }
    multiplier = multipliers.get(profile.activity_level, 1.2)
    maintenance = bmr * multiplier

    # --- Cardio expenditure (last 7 days, MET=6) ---
    seven_days_ago = today - timedelta(days=7)
    cardio_sessions = CardioSession.objects.filter(
        user=user,
        date__gte=seven_days_ago,
        date__lte=today,
    )
    total_cardio_calories = 0.0
    met = 6.0
    for cs in cardio_sessions:
        duration_hours = cs.duration_minutes / 60.0
        total_cardio_calories += met * weight_kg * duration_hours

    daily_cardio_avg = total_cardio_calories / 7.0

    return round(maintenance + daily_cardio_avg, 2)


# ---------------------------------------------------------------------------
# 5. bodyweight_trend
# ---------------------------------------------------------------------------

def bodyweight_trend(user, days: int = 30) -> list:
    """
    Return daily bodyweight entries with a 7-day rolling average for the last `days` days.
    Each entry: {date, weight, rolling_avg}.
    rolling_avg is None if fewer than 7 data points precede this entry.
    Ordered oldest to newest.
    """
    today = date.today()
    cutoff = today - timedelta(days=days - 1)

    entries = list(
        BodyweightEntry.objects
        .filter(user=user, date__gte=cutoff, date__lte=today)
        .order_by('date')
        .values('date', 'weight')
    )

    result = []
    for i, entry in enumerate(entries):
        # Collect the previous 6 entries + current (up to 7)
        window = entries[max(0, i - 6): i + 1]
        if len(window) < 7:
            rolling_avg = None
        else:
            rolling_avg = round(
                sum(float(e['weight']) for e in window) / len(window), 4
            )
        result.append({
            'date': entry['date'],
            'weight': float(entry['weight']),
            'rolling_avg': rolling_avg,
        })

    return result


# ---------------------------------------------------------------------------
# 6. adherence
# ---------------------------------------------------------------------------

def adherence(user, start_date: date, end_date: date) -> dict:
    """
    Return {scheduled_days, completed_days, rate}.
    scheduled_days = total calendar days in range.
    completed_days = distinct dates with at least one Session.
    rate = completed / scheduled, rounded to 4 decimal places.
    """
    scheduled_days = (end_date - start_date).days + 1

    completed_days = (
        Session.objects
        .filter(user=user, date__gte=start_date, date__lte=end_date)
        .values('date')
        .distinct()
        .count()
    )

    rate = round(completed_days / scheduled_days, 4) if scheduled_days > 0 else 0.0

    return {
        'scheduled_days': scheduled_days,
        'completed_days': completed_days,
        'rate': rate,
    }


# ---------------------------------------------------------------------------
# 7. goal_progress
# ---------------------------------------------------------------------------

def goal_progress(goal) -> dict:
    """
    Return {baseline, current, target, percent_to_target, on_pace, projected_completion_date}.
    """
    today = date.today()
    user = goal.user
    baseline = float(goal.baseline_value)

    # --- Determine current & target by goal type ---
    if goal.goal_type == 'strength':
        # Latest estimated 1RM from most recent working set for the exercise
        latest_set = (
            SessionSet.objects
            .filter(
                session__user=user,
                exercise=goal.exercise,
                set_type='working',
            )
            .order_by('-session__date', '-set_index')
            .first()
        )
        if latest_set is not None:
            current = estimate_1rm(float(latest_set.weight), latest_set.reps, formula='epley')
        else:
            current = baseline

        if goal.target_mode == 'one_rm':
            target = float(goal.target_value) if goal.target_value is not None else baseline
        elif goal.target_mode == 'weight_for_reps':
            tw = float(goal.target_weight) if goal.target_weight is not None else baseline
            tr = goal.target_reps if goal.target_reps is not None else 1
            target = estimate_1rm(tw, tr, formula='epley')
        else:
            target = float(goal.target_value) if goal.target_value is not None else baseline

    elif goal.goal_type == 'bodyweight':
        bw_entry = BodyweightEntry.objects.filter(user=user).order_by('-date').first()
        current = float(bw_entry.weight) if bw_entry is not None else baseline
        target = float(goal.target_value) if goal.target_value is not None else baseline

    elif goal.goal_type == 'body_fat':
        bc_entry = (
            BodyCompositionEntry.objects
            .filter(user=user, body_fat_pct__isnull=False)
            .order_by('-date')
            .first()
        )
        current = float(bc_entry.body_fat_pct) if bc_entry is not None else baseline
        if goal.target_bodyfat is not None:
            target = float(goal.target_bodyfat)
        elif goal.target_value is not None:
            target = float(goal.target_value)
        else:
            target = baseline

    else:
        current = baseline
        target = float(goal.target_value) if goal.target_value is not None else baseline

    # --- Percent to target ---
    if target == baseline:
        percent_to_target = 0.0
    else:
        raw = (current - baseline) / (target - baseline) * 100
        percent_to_target = max(0.0, min(100.0, raw))

    percent_to_target = round(percent_to_target, 4)

    # --- On pace ---
    created_at_date = (
        goal.created_at.date()
        if hasattr(goal.created_at, 'date')
        else goal.created_at
    )
    days_elapsed = (today - created_at_date).days

    if goal.target_date is None:
        on_pace = True
    else:
        total_days = (goal.target_date - created_at_date).days
        if total_days <= 0:
            expected_progress = 100.0
        else:
            expected_progress = (days_elapsed / total_days) * 100
        on_pace = percent_to_target >= expected_progress

    # --- Projected completion date ---
    if percent_to_target >= 100:
        projected_completion_date = today
    elif percent_to_target <= 0 or days_elapsed == 0:
        projected_completion_date = None
    else:
        days_per_percent = days_elapsed / percent_to_target
        remaining = 100 - percent_to_target
        projected_completion_date = today + timedelta(days=days_per_percent * remaining)
        if hasattr(projected_completion_date, 'date'):
            projected_completion_date = projected_completion_date.date()

    return {
        'baseline': round(baseline, 4),
        'current': round(current, 4),
        'target': round(target, 4),
        'percent_to_target': percent_to_target,
        'on_pace': on_pace,
        'projected_completion_date': projected_completion_date,
    }


# ---------------------------------------------------------------------------
# 8. transition_nutrition
# ---------------------------------------------------------------------------

def transition_nutrition(old_target: NutritionTarget, new_goal_type: str) -> list:
    """
    Return a 3-week calorie glide-path list of {week, calorie_target, protein_g, notes}.
    """
    old_calories = float(old_target.calorie_target)
    protein_g = float(old_target.protein_g)
    old_tdee = float(old_target.tdee)

    goal_adjustments = {
        'fat_loss': -400,
        'lean_bulk': +200,
        'recomp': 0,
        'maintenance': 0,
        'general': 0,
    }
    adjustment = goal_adjustments.get(new_goal_type, 0)
    new_calories = old_tdee + adjustment

    step = (new_calories - old_calories) / 3

    notes_map = {
        'fat_loss': 'Caloric deficit for fat loss',
        'lean_bulk': 'Caloric surplus for lean muscle gain',
        'recomp': 'Maintenance calories for body recomposition',
        'maintenance': 'Maintenance calories',
        'general': 'General health maintenance calories',
    }
    notes_base = notes_map.get(new_goal_type, 'Transitioning calorie target')

    weeks = []
    for week in range(1, 4):
        cal = round(old_calories + step * week, 1)
        weeks.append({
            'week': week,
            'calorie_target': cal,
            'protein_g': protein_g,
            'notes': f"Week {week}: {notes_base} (transition step {week}/3)",
        })

    return weeks


# ---------------------------------------------------------------------------
# 9. zone_minutes_trend
# ---------------------------------------------------------------------------

def zone_minutes_trend(user, weeks: int = 8) -> list:
    """
    Return weekly Z2 zone minutes over the last `weeks` weeks.
    Each entry: {week_start: date, z2_minutes: float, total_zone_minutes: float}.
    Ordered oldest to newest.
    """
    today = date.today()
    # Align to the most recent Monday
    days_since_monday = today.weekday()  # Monday == 0
    current_week_start = today - timedelta(days=days_since_monday)

    result = []
    for i in range(weeks - 1, -1, -1):
        week_start = current_week_start - timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)

        sessions = CardioSession.objects.filter(
            user=user,
            date__gte=week_start,
            date__lte=week_end,
        )

        z2_minutes = 0.0
        total_zone_minutes = 0.0

        for cs in sessions:
            zone_data = cs.zone_minutes or {}
            # z2 key — try both lowercase and uppercase
            z2 = float(zone_data.get('z2', zone_data.get('Z2', 0)) or 0)
            z2_minutes += z2
            # total across all zones
            for v in zone_data.values():
                total_zone_minutes += float(v or 0)

        result.append({
            'week_start': week_start,
            'z2_minutes': z2_minutes,
            'total_zone_minutes': total_zone_minutes,
        })

    return result


# ---------------------------------------------------------------------------
# 10. pace_at_heart_rate
# ---------------------------------------------------------------------------

def pace_at_heart_rate(user, target_hr: int, weeks: int = 12) -> float | None:
    """
    Return the mean avg_pace from CardioSessions in the last `weeks` weeks
    where avg_heart_rate is within ±10 bpm of target_hr.
    Returns None if no matching sessions found.
    """
    today = date.today()
    cutoff = today - timedelta(weeks=weeks)

    sessions = CardioSession.objects.filter(
        user=user,
        date__gte=cutoff,
        avg_heart_rate__isnull=False,
        avg_pace__isnull=False,
        avg_heart_rate__gte=target_hr - 10,
        avg_heart_rate__lte=target_hr + 10,
    )

    paces = [float(cs.avg_pace) for cs in sessions]
    if not paces:
        return None

    return round(sum(paces) / len(paces), 4)


# ---------------------------------------------------------------------------
# 11. resting_hr_trend
# ---------------------------------------------------------------------------

def resting_hr_trend(user, days: int = 30) -> list:
    """
    Return HeartRateEntry data for the last `days` days where resting_hr is not null.
    Each entry: {date, resting_hr, rolling_avg}.
    rolling_avg is None if fewer than 7 data points exist in the window.
    Ordered oldest to newest.
    """
    today = date.today()
    cutoff = today - timedelta(days=days - 1)

    entries = list(
        HeartRateEntry.objects
        .filter(user=user, date__gte=cutoff, date__lte=today, resting_hr__isnull=False)
        .order_by('date')
        .values('date', 'resting_hr')
    )

    result = []
    for i, entry in enumerate(entries):
        window = entries[max(0, i - 6): i + 1]
        if len(window) < 7:
            rolling_avg = None
        else:
            rolling_avg = round(
                sum(e['resting_hr'] for e in window) / len(window), 4
            )
        result.append({
            'date': entry['date'],
            'resting_hr': entry['resting_hr'],
            'rolling_avg': rolling_avg,
        })

    return result


# ---------------------------------------------------------------------------
# 12. vo2_max_estimate
# ---------------------------------------------------------------------------

def vo2_max_estimate(user) -> float | None:
    """
    Estimate VO2max using the Uth-Sørensen formula:
        VO2max ≈ 15 * (max_hr / resting_hr)

    Sources for max_hr  : HeartRateEntry.max_hr (latest non-null) → UserProfile.max_heart_rate
    Sources for resting_hr: HeartRateEntry.resting_hr (latest non-null) → UserProfile.resting_heart_rate

    Returns None if either value is unavailable.
    """
    # --- max_hr ---
    max_hr_entry = (
        HeartRateEntry.objects
        .filter(user=user, max_hr__isnull=False)
        .order_by('-date')
        .first()
    )
    max_hr = max_hr_entry.max_hr if max_hr_entry is not None else None

    if max_hr is None:
        try:
            profile = UserProfile.objects.get(user=user)
            max_hr = profile.max_heart_rate
        except UserProfile.DoesNotExist:
            pass

    # --- resting_hr ---
    resting_entry = (
        HeartRateEntry.objects
        .filter(user=user, resting_hr__isnull=False)
        .order_by('-date')
        .first()
    )
    resting_hr = resting_entry.resting_hr if resting_entry is not None else None

    if resting_hr is None:
        try:
            profile = UserProfile.objects.get(user=user)
            resting_hr = profile.resting_heart_rate
        except UserProfile.DoesNotExist:
            pass

    if max_hr is None or resting_hr is None or resting_hr == 0:
        return None

    return round(15 * (max_hr / resting_hr), 1)
