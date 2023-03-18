# Generated by Django 3.2.18 on 2023-03-18 18:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('product', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='product_avaliable_in',
            field=models.ManyToManyField(blank=True, related_name='avaliable_in_store', to='users.Store'),
        ),
        migrations.AddField(
            model_name='item',
            name='product_category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_category', to='product.itemattribute'),
        ),
        migrations.AddField(
            model_name='item',
            name='product_creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.vendor'),
        ),
        migrations.AddField(
            model_name='item',
            name='product_images',
            field=models.ManyToManyField(blank=True, related_name='product_image', to='product.ItemImage'),
        ),
        migrations.AddField(
            model_name='item',
            name='product_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_type', to='product.itemattribute'),
        ),
    ]
