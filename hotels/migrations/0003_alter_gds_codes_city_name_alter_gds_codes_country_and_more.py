# Generated by Django 4.1.1 on 2022-09-30 07:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0002_alter_gds_codes_concertiv_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gds_codes',
            name='city_name',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='gds_codes',
            name='country',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='gds_codes',
            name='postal_code',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='gds_codes',
            name='state',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
