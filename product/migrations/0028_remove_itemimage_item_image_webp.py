# Generated by Django 3.2.19 on 2023-11-29 02:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0027_remove_item_product_images'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='itemimage',
            name='item_image_webp',
        ),
    ]
