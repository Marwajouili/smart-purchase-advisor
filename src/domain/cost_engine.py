"""
Moteur de coût déterministe.

Règle non négociable de l'architecture : ce module ne connaît rien au
LLM et n'est jamais appelé par le LLM autrement que comme une fonction
Python normale. Aucun nombre produit ici n'est recalculé ou reformulé
par le modèle de langage — le LLM ne fait que lire le résultat.

100% testable unitairement, 100% déterministe, sans appel réseau.
"""

from __future__ import annotations

from decimal import Decimal

from src.domain.models import (
    CostBreakdown,
    EvaluatedOption,
    PurchaseOption,
    TransportMode,
)


class InvalidPurchaseOptionError(ValueError):
    """Levée quand une option d'achat n'a pas les données requises pour être évaluée."""


def compute_cost_breakdown(option: PurchaseOption) -> CostBreakdown:
    """
    Calcule le coût total d'une option d'achat.

    total_cost = prix_produit + coût_transport(fare OU carburant+péage+parking)

    Lève InvalidPurchaseOptionError si les données nécessaires au calcul
    manquent (ex: mode CAR sans car_cost_params).
    """
    product_price = option.price.price
    route = option.route

    fuel_cost = Decimal("0")
    toll_cost = Decimal("0")
    parking_cost = Decimal("0")
    fare_cost = Decimal("0")

    if route.mode == TransportMode.CAR:
        if option.car_cost_params is None:
            raise InvalidPurchaseOptionError(
                "car_cost_params est requis pour une option avec route.mode == CAR"
            )
        params = option.car_cost_params
        fuel_cost = (
            Decimal(str(route.total_distance_km))
            / Decimal("100")
            * params.consumption_liters_per_100km
            * params.fuel_price_per_liter
        )
        toll_cost = params.toll_cost_eur
        parking_cost = params.parking_cost_eur

    elif route.mode == TransportMode.TRANSIT:
        fare_cost = route.fare_eur or Decimal("0")

    # WALK : aucun coût de transport, uniquement du temps.

    total_cost = product_price + fuel_cost + toll_cost + parking_cost + fare_cost

    return CostBreakdown(
        product_price_eur=product_price,
        transport_fare_eur=fare_cost,
        fuel_cost_eur=fuel_cost,
        toll_cost_eur=toll_cost,
        parking_cost_eur=parking_cost,
        total_cost_eur=total_cost,
        total_duration_minutes=route.total_duration_minutes,
    )


def evaluate_option(option: PurchaseOption) -> EvaluatedOption:
    """Évalue une option d'achat unique et retourne son détail de coût."""
    breakdown = compute_cost_breakdown(option)
    return EvaluatedOption(option=option, cost_breakdown=breakdown)


def rank_options(
    options: list[PurchaseOption],
    *,
    sort_by: str = "total_cost_eur",
) -> list[EvaluatedOption]:
    """
    Évalue et classe une liste d'options d'achat, du meilleur au moins bon
    résultat, selon `sort_by` ("total_cost_eur" ou "total_duration_minutes").

    Les erreurs d'évaluation individuelle ne font pas échouer tout le
    classement : une option invalide est simplement exclue (le
    log/observabilité de cette exclusion est de la responsabilité de
    l'appelant, pas de ce module).
    """
    if sort_by not in {"total_cost_eur", "total_duration_minutes"}:
        raise ValueError(f"sort_by invalide : {sort_by}")

    evaluated: list[EvaluatedOption] = []
    for option in options:
        try:
            evaluated.append(evaluate_option(option))
        except InvalidPurchaseOptionError:
            continue

    return sorted(
        evaluated,
        key=lambda e: getattr(e.cost_breakdown, sort_by),
    )
