# Generated by Django 4.1.3 on 2023-01-24 23:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0022_subscription_reseller_supplier"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contract",
            name="autorenewal_duration_unit",
            field=models.SmallIntegerField(blank=True, choices=[(3, "Month(s)"), (4, "Year(s)")], default=4, null=True),
        ),
    ]