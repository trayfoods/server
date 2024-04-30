# Generated by Django 3.2.23 on 2024-04-28 22:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0037_alter_deliverynotification_unique_together'),
        ('product', '0046_alter_item_product_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('items', models.ManyToManyField(blank=True, related_name='menus', to='product.Item')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.store')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='menus', to='product.itemattribute')),
            ],
        ),
    ]
