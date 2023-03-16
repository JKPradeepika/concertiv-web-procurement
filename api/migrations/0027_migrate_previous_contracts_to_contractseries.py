# Generated by Django 4.1.3 on 2023-01-31 19:35

from typing import List, Optional, Tuple
from django.db import migrations


def create_contract_series(apps, schema_editor) -> None:
    db_alias = schema_editor.connection.alias
    Contract = apps.get_model("api", "Contract")
    ContractSeries = apps.get_model("api", "ContractSeries")

    def get_renewal_chain_and_contract_series(renewed_contract: Contract) -> Tuple[List[Contract], ContractSeries]:
        contract_series = renewed_contract.contract_series
        contract_list = [renewed_contract]
        current_contract = renewed_contract

        while current_contract.previous_contract:
            if current_contract.previous_contract in contract_list:
                current_contract.previous_contract = None
                current_contract.save()
                break

            current_contract = current_contract.previous_contract
            contract_series = current_contract.contract_series
            contract_list.append(current_contract)

        return (contract_list, contract_series)

    def update_all_contracts_in_chain_with_contract_series(
        contract_chain: List[Contract],
        contract_series: Optional[ContractSeries],
    ) -> None:
        if contract_series is None:
            contract_series = ContractSeries.objects.create()

        for contract in contract_chain:
            if contract.contract_series != contract_series:
                contract.contract_series = contract_series
                contract.save()

    renewed_contracts = Contract.objects.using(db_alias).filter(previous_contract_id__isnull=False).order_by("id")
    for rc in renewed_contracts:
        contract_chain, contract_series = get_renewal_chain_and_contract_series(rc)
        update_all_contracts_in_chain_with_contract_series(contract_chain, contract_series)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0026_contractseries"),
    ]

    operations = [
        migrations.RunPython(create_contract_series, migrations.RunPython.noop),
    ]