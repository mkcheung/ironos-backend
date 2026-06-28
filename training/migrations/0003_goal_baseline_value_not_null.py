from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0002_cardiosession_notes'),
    ]

    operations = [
        migrations.RunSQL(
            "UPDATE training_goal SET baseline_value = 0 WHERE baseline_value IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='goal',
            name='baseline_value',
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
    ]
