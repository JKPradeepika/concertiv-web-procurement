# Generated by Django 4.1.3 on 2023-01-25 23:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0023_alter_contract_autorenewal_duration_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="discount_type",
            field=models.SmallIntegerField(choices=[(1, "Fixed"), (2, "Percentage")], null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="tmc_supplier",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tmc_supplier", to="api.supplier"
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="reseller_supplier",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reseller_supplier",
                to="api.supplier",
            ),
        ),
        migrations.CreateModel(
            name="SubscriptionPOSGeography",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("geography", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="api.geography")),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pos_geographies",
                        to="api.subscription",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Subscription POS Geographies",
                "db_table": "subscription_pos_geographies",
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionposgeography",
            constraint=models.UniqueConstraint(
                fields=("geography", "subscription"), name="unique_pos_geography_per_subscription"
            ),
        ),
    ]