# Generated by Django 4.0.4 on 2022-08-18 08:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Airport',
            fields=[
                ('airport_code', models.CharField(max_length=6, primary_key=True, serialize=False)),
                ('airport_id', models.IntegerField()),
                ('airport_city', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Alliance',
            fields=[
                ('alliance_id', models.IntegerField(primary_key=True, serialize=False)),
                ('alliance_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Preference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=50)),
                ('prefered_airline', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Airline',
            fields=[
                ('carrier_code', models.CharField(max_length=4, primary_key=True, serialize=False)),
                ('carrier_id', models.IntegerField()),
                ('carrier_name', models.CharField(max_length=100)),
                ('carrier_alliance_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='air.alliance')),
            ],
        ),
    ]