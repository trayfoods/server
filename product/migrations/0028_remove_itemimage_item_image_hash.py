# Generated by Django 3.2.23 on 2024-02-05 23:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0027_alter_order_order_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='itemimage',
            name='item_image_hash',
        ),
    ]
