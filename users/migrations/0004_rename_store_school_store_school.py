# Generated by Django 3.2.23 on 2024-01-05 21:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_rename_store_campus_store_campus'),
    ]

    operations = [
        migrations.RenameField(
            model_name='store',
            old_name='store_school',
            new_name='school',
        ),
    ]
