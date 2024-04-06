# Generated by Django 3.2.23 on 2024-04-06 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_store_store_average_preparation_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='_type',
            field=models.CharField(choices=[('credit', 'credit'), ('debit', 'debit'), ('transfer', 'transfer'), ('refund', 'refund')], max_length=20),
        ),
    ]
