from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("laptimes", "0002_session_session_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="lap",
            name="sector1_time",
        ),
        migrations.RemoveField(
            model_name="lap",
            name="sector2_time",
        ),
        migrations.RemoveField(
            model_name="lap",
            name="sector3_time",
        ),
        migrations.AddField(
            model_name="lap",
            name="sectors",
            field=models.JSONField(default=list),
        ),
    ]
