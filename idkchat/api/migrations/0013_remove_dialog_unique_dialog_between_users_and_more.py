# Generated by Django 4.2.1 on 2023-05-24 17:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0012_dialog_unique_dialog_between_users_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="dialog",
            name="unique_dialog_between_users",
        ),
        migrations.AddConstraint(
            model_name="dialog",
            constraint=models.UniqueConstraint(
                fields=("user_1", "user_2"), name="unique_dialog_between_users1"
            ),
        ),
        migrations.AddConstraint(
            model_name="dialog",
            constraint=models.UniqueConstraint(
                fields=("user_2", "user_1"), name="unique_dialog_between_users2"
            ),
        ),
    ]
