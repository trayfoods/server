# Generated by Django 4.2.5 on 2023-09-17 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0056_alter_transaction_transaction_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='gateway_transfer_id',
            field=models.CharField(blank=True, editable=False, max_length=50, null=True, unique=True),
        ),
    ]
