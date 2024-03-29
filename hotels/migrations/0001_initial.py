# Generated by Django 4.1.1 on 2022-12-09 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Gdscodes',
            fields=[
                ('concertiv_id', models.IntegerField(primary_key=True, serialize=False)),
                ('chain_code', models.CharField(max_length=2)),
                ('chain_name', models.CharField(max_length=255)),
                ('property_name', models.CharField(max_length=255)),
                ('property_address', models.CharField(max_length=255)),
                ('city_name', models.CharField(max_length=50, null=True)),
                ('state', models.CharField(max_length=50, null=True)),
                ('postal_code', models.CharField(max_length=50, null=True)),
                ('country', models.CharField(max_length=50, null=True)),
            ],
        ),
    ]
