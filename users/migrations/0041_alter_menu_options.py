# Generated by Django 3.2.23 on 2024-04-30 10:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0040_alter_menu_position'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='menu',
            options={'ordering': ['position']},
        ),
    ]
