# Generated by Django 5.2.3 on 2025-06-18 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('vendor', 'Vendor'), ('customer', 'Customer')], max_length=10),
        ),
    ]
