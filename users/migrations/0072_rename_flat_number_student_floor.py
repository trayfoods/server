# Generated by Django 3.2.19 on 2023-11-15 20:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0071_hostel_campus'),
    ]

    operations = [
        migrations.RenameField(
            model_name='student',
            old_name='flat_number',
            new_name='floor',
        ),
    ]
