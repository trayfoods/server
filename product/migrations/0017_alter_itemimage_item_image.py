# Generated by Django 3.2 on 2022-06-06 03:02

from django.db import migrations, models
import product.models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0016_alter_itemimage_item_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemimage',
            name='item_image',
            field=models.ImageField(default=1, upload_to=product.models.item_directory_path),
            preserve_default=False,
        ),
    ]
