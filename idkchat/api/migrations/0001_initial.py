# Generated by Django 4.2.1 on 2023-05-22 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("login", models.TextField(max_length=32, unique=True)),
                ("password", models.TextField(max_length=1024)),
                ("avatar", models.TextField(max_length=4096)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Session",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="api.user"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
