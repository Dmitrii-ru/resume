# Generated by Django 4.2 on 2023-08-08 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('verification_phone_api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(max_length=16, unique=True),
        ),
    ]