# Generated by Django 3.2.23 on 2024-01-31 12:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0025_auto_20240128_2336'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemattribute',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='product.itemattribute'),
        ),
    ]
