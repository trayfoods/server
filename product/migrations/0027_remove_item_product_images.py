# Generated by Django 3.2.19 on 2023-11-29 02:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0026_item_product_creator'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='product_images',
        ),
    ]
