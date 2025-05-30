# Generated by Django 3.2.23 on 2024-01-18 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_hostelfield_value_prefix'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hostelfield',
            name='loop_prefix',
            field=models.CharField(blank=True, help_text='e.g Room', max_length=10),
        ),
        migrations.AlterField(
            model_name='hostelfield',
            name='value_prefix',
            field=models.CharField(blank=True, help_text='Not required if loop_prefix is set', max_length=10, null=True),
        ),
    ]
