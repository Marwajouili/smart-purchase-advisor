"""
Modèles de domaine.

Ces modèles représentent le cœur métier du système, indépendamment de
tout provider externe (routing, prix, LLM). Aucun modèle ici ne connaît
l'existence d'une API externe : c'est le rôle de la couche `providers`
de produire ces objets à partir de données brutes.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class TransportMode(str, Enum):
    """Moyens de transport supportés."""

    CAR = "car"
    TRANSIT = "transit"
    WALK = "walk"


class Product(BaseModel):
    """Un produit recherché par l'utilisateur."""

    id: str
    name: str
    brand: str | None = None
    reference: str | None = None
    quantity: str | None = None  # ex: "500ml", "1kg"


class Store(BaseModel):
    """Un magasin physique."""

    id: str
    name: str
    brand: str
    latitude: float
    longitude: float
    address: str


class PriceInfo(BaseModel):
    """
    Prix d'un produit dans un magasin donné.

    `is_simulated` documente explicitement si le prix provient d'un
    relevé réel figé (MVP) ou d'une source live (V2+). Ne jamais
    masquer cette information : elle doit pouvoir être affichée à
    l'utilisateur final.
    """

    product_id: str
    store_id: str
    price: Decimal = Field(gt=0)
    currency: str = "EUR"
    is_simulated: bool
    last_updated: str  # ISO 8601 date — string volontairement, pas de logique de fraîcheur ici

    @field_validator("price")
    @classmethod
    def price_must_be_reasonable(cls, v: Decimal) -> Decimal:
        if v > Decimal("10000"):
            raise ValueError("Prix invraisemblable pour un produit de grande consommation")
        return v


class TravelLeg(BaseModel):
    """Un segment d'un trajet (ex: une ligne de bus, un tronçon à pied)."""

    mode: TransportMode
    duration_minutes: float = Field(ge=0)
    distance_km: float = Field(ge=0)
    line_name: str | None = None  # ex: "RER A", pertinent seulement pour TRANSIT


class Route(BaseModel):
    """
    Un trajet normalisé entre deux points, tel que retourné par un
    RoutingProvider quel qu'il soit (voiture, transit, etc.).

    C'est le contrat que toute implémentation de RoutingProvider doit
    respecter — voir src/providers/routing/base.py.
    """

    origin_label: str
    destination_label: str
    mode: TransportMode
    total_duration_minutes: float = Field(ge=0)
    total_distance_km: float = Field(ge=0)
    legs: list[TravelLeg] = Field(default_factory=list)
    transfers: int = Field(ge=0, default=0)
    fare_eur: Decimal | None = None  # coût du titre de transport, si transit
    provider: str  # nom du provider ayant produit ce trajet, pour traçabilité


class CarCostParams(BaseModel):
    """Paramètres de coût pour un trajet en voiture."""

    fuel_price_per_liter: Decimal = Field(gt=0)
    consumption_liters_per_100km: Decimal = Field(gt=0)
    toll_cost_eur: Decimal = Field(ge=0, default=Decimal("0"))
    parking_cost_eur: Decimal = Field(ge=0, default=Decimal("0"))


class PurchaseOption(BaseModel):
    """
    Une option d'achat complète : un produit, dans un magasin, avec le
    trajet nécessaire pour s'y rendre. C'est l'unité de comparaison du
    moteur de coût.
    """

    product: Product
    store: Store
    price: PriceInfo
    route: Route
    car_cost_params: CarCostParams | None = None  # requis seulement si route.mode == CAR


class CostBreakdown(BaseModel):
    """Détail du coût total d'une option d'achat, pour transparence."""

    product_price_eur: Decimal
    transport_fare_eur: Decimal = Decimal("0")
    fuel_cost_eur: Decimal = Decimal("0")
    toll_cost_eur: Decimal = Decimal("0")
    parking_cost_eur: Decimal = Decimal("0")
    total_cost_eur: Decimal
    total_duration_minutes: float


class EvaluatedOption(BaseModel):
    """Une option d'achat après évaluation par le moteur de coût."""

    option: PurchaseOption
    cost_breakdown: CostBreakdown
