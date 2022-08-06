# Generated by Django 3.2.13 on 2022-08-06 19:59

from django.db import migrations, models
import product.models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0004_remove_item_has_qty'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemimage',
            name='item_image_webp',
            field=models.ImageField(blank=True, help_text='Upload Item Image In Webp Format.', null=True, upload_to=product.models.item_directory_path, verbose_name='Webp Item Image'),
        ),
        migrations.AlterField(
            model_name='itemimage',
            name='item_image',
            field=models.ImageField(help_text='Upload Item Image.', upload_to=product.models.item_directory_path, verbose_name='Item Image'),
        ),
    ]
