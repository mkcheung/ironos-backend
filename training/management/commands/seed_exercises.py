import requests
from django.core.management.base import BaseCommand
from training.models import Exercise

WGER_API_URL = 'https://wger.de/api/v2/exercise/'
WGER_EXERCISE_INFO_URL = 'https://wger.de/api/v2/exerciseinfo/'

CATEGORY_MAP = {
    10: 'compound',   # Back
    11: 'compound',   # Legs
    12: 'compound',   # Chest
    13: 'compound',   # Shoulders
    14: 'isolation',  # Arms
    15: 'isolation',  # Calves
    8: 'compound',    # Core/Abs
    9: 'compound',    # Glutes
}


class Command(BaseCommand):
    help = 'Seed exercises from the Wger public API (idempotent).'

    def handle(self, *args, **options):
        if Exercise.objects.filter(is_custom=False).exists():
            self.stdout.write('Exercises already seeded, skipping.')
            return

        self.stdout.write('Seeding exercises from Wger API...')
        created = 0
        page = 1

        while True:
            try:
                response = requests.get(
                    WGER_EXERCISE_INFO_URL,
                    params={'language': 2, 'format': 'json', 'limit': 100, 'offset': (page - 1) * 100},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                self.stderr.write(f'Error fetching exercises: {e}')
                break

            results = data.get('results', [])
            if not results:
                break

            for item in results:
                wger_id = item.get('id')
                if not wger_id:
                    continue

                # Get English translation name
                name = None
                for translation in item.get('translations', []):
                    if translation.get('language') == 2:  # English
                        name = translation.get('name', '').strip()
                        break

                if not name:
                    continue

                # Category
                category_data = item.get('category', {})
                category_id = category_data.get('id') if category_data else None
                category = CATEGORY_MAP.get(category_id, 'isolation')

                # Primary muscle
                muscles = item.get('muscles', [])
                primary_muscle = muscles[0].get('name_en', 'general') if muscles else 'general'

                # Secondary muscles
                muscles_secondary = item.get('muscles_secondary', [])
                secondary_muscles = [m.get('name_en', '') for m in muscles_secondary if m.get('name_en')]

                # Equipment
                equipment_list = item.get('equipment', [])
                equipment = equipment_list[0].get('name', 'bodyweight') if equipment_list else 'bodyweight'

                Exercise.objects.get_or_create(
                    wger_id=wger_id,
                    defaults={
                        'name': name,
                        'primary_muscle': primary_muscle,
                        'secondary_muscles': secondary_muscles,
                        'category': category,
                        'equipment': equipment,
                        'is_custom': False,
                    }
                )
                created += 1

            if not data.get('next'):
                break
            page += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Seeded {created} exercises.'))
