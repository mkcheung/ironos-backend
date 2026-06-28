from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0003_goal_baseline_value_not_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bodycompositionentry',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='bodyweightentry',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='cardiosession',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='heartrateentry',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='nutritiontarget',
            name='date_effective',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='session',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='weeklyreport',
            name='week_start',
            field=models.DateField(db_index=True),
        ),
    ]
