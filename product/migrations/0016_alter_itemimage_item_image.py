# Generated by Django 3.2 on 2022-06-06 01:24

from django.db import migrations, models
import product.models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0015_alter_item_product_images'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemimage',
            name='item_image',
            field=models.ImageField(blank=True, null=True, upload_to=product.models.item_directory_path),
        ),
    ]
