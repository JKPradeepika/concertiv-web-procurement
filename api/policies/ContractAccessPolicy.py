from typing import Any, Dict

from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.request import Request

from api.models.Contract import Contract
from api.models.User import User
from api.policies import get_access_policy_statements, restrict_queryset_if_necessary
from api.policies.CustomAccessPolicy import CustomAccessPolicy


class ContractAccessPolicy(CustomAccessPolicy):
    statements = get_access_policy_statements("user_works_for_employer")

    @classmethod
    def scope_queryset(cls, request: Request, queryset: QuerySet[Contract]) -> QuerySet[Contract]:
        return restrict_queryset_if_necessary(request, queryset, "business_deal__")

    def user_works_for_employer(
        self, request: Request, view: viewsets.ModelViewSet, action: str, **kwargs: Dict[str, Any]
    ) -> bool:
        contract: Contract = view.get_object()
        if isinstance(request.user, AnonymousUser):
            return False
        elif isinstance(request.user, User):
            return bool(
                contract.business_deal.buyer.employer.id == request.user.person.employer.id
                or contract.business_deal.supplier.employer.id == request.user.person.employer.id
            )