# Generated by Django 3.2.23 on 2024-02-04 10:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0026_itemattribute_parent'),
        ('users', '0022_alter_storeopenhours_day'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'pending'), ('accepted', 'accepted'), ('rejected', 'rejected'), ('out-for-delivery', 'out-for-delivery'), ('delivered', 'delivered')], default='pending', max_length=30)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('delivery_person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.deliveryperson')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='product.order')),
                ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.store')),
            ],
        ),
    ]
