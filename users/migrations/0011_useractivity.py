# Generated by Django 3.2.13 on 2022-12-21 01:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0008_alter_item_product_creator'),
        ('users', '0010_alter_gender_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=100)),
                ('timestamp', models.DateTimeField()),
                ('activity_type', models.CharField(choices=[('view', 'view'), ('click', 'click'), ('purchase', 'purchase'), ('add_to_item', 'add_to_item'), ('remove_from_order', 'remove_from_order'), ('add_to_order', 'add_to_order'), ('remove_from_item', 'remove_from_item')], max_length=20)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.item')),
            ],
        ),
    ]
