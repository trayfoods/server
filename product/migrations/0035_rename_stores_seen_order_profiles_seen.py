# Generated by Django 3.2.23 on 2024-03-26 10:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0034_rename_vendors_seen_order_stores_seen'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='stores_seen',
            new_name='profiles_seen',
        ),
    ]
