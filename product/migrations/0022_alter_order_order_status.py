# Generated by Django 3.2.19 on 2023-11-23 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0021_alter_order_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.CharField(choices=[('not-started', 'not-started'), ('processing', 'processing'), ('shipped', 'shipped'), ('delivered', 'delivered'), ('cancelled', 'cancelled')], default='not-started', max_length=20),
        ),
    ]
