from decimal import Decimal

import pytest

from src.domain.cost_engine import (
    InvalidPurchaseOptionError,
    compute_cost_breakdown,
    evaluate_option,
    rank_options,
)
from src.domain.models import (
    CarCostParams,
    PriceInfo,
    Product,
    PurchaseOption,
    Route,
    Store,
    TransportMode,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_product(product_id: str = "p1") -> Product:
    return Product(id=product_id, name="Liquide vaisselle Paic", brand="Paic")


def make_store(store_id: str = "s1") -> Store:
    return Store(
        id=store_id,
        name="Carrefour Houilles",
        brand="Carrefour",
        latitude=48.9333,
        longitude=2.1833,
        address="1 rue de Paris, Houilles",
    )


def make_price(product_id: str = "p1", store_id: str = "s1", price: str = "2.50") -> PriceInfo:
    return PriceInfo(
        product_id=product_id,
        store_id=store_id,
        price=Decimal(price),
        is_simulated=True,
        last_updated="2026-09-01",
    )


def make_car_route(distance_km: float = 10.0, duration_minutes: float = 15.0) -> Route:
    return Route(
        origin_label="Domicile",
        destination_label="Carrefour Houilles",
        mode=TransportMode.CAR,
        total_duration_minutes=duration_minutes,
        total_distance_km=distance_km,
        provider="test-provider",
    )


def make_transit_route(
    duration_minutes: float = 25.0, fare_eur: str = "1.90", transfers: int = 1
) -> Route:
    return Route(
        origin_label="Domicile",
        destination_label="Carrefour Houilles",
        mode=TransportMode.TRANSIT,
        total_duration_minutes=duration_minutes,
        total_distance_km=6.0,
        transfers=transfers,
        fare_eur=Decimal(fare_eur),
        provider="test-provider",
    )


def make_walk_route(duration_minutes: float = 12.0) -> Route:
    return Route(
        origin_label="Domicile",
        destination_label="Carrefour Houilles",
        mode=TransportMode.WALK,
        total_duration_minutes=duration_minutes,
        total_distance_km=1.0,
        provider="test-provider",
    )


# ---------------------------------------------------------------------------
# compute_cost_breakdown — mode CAR
# ---------------------------------------------------------------------------


def test_car_cost_breakdown_computes_fuel_correctly():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(price="2.50"),
        route=make_car_route(distance_km=20.0),
        car_cost_params=CarCostParams(
            fuel_price_per_liter=Decimal("1.80"),
            consumption_liters_per_100km=Decimal("6.0"),
            toll_cost_eur=Decimal("0"),
            parking_cost_eur=Decimal("0"),
        ),
    )

    breakdown = compute_cost_breakdown(option)

    # 20km / 100 * 6L * 1.80€/L = 2.16€
    assert breakdown.fuel_cost_eur == Decimal("2.16")
    assert breakdown.product_price_eur == Decimal("2.50")
    assert breakdown.total_cost_eur == Decimal("4.66")


def test_car_cost_breakdown_includes_toll_and_parking():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(price="5.00"),
        route=make_car_route(distance_km=10.0),
        car_cost_params=CarCostParams(
            fuel_price_per_liter=Decimal("1.80"),
            consumption_liters_per_100km=Decimal("6.0"),
            toll_cost_eur=Decimal("3.50"),
            parking_cost_eur=Decimal("1.00"),
        ),
    )

    breakdown = compute_cost_breakdown(option)

    assert breakdown.toll_cost_eur == Decimal("3.50")
    assert breakdown.parking_cost_eur == Decimal("1.00")
    assert breakdown.total_cost_eur == Decimal("5.00") + breakdown.fuel_cost_eur + Decimal("4.50")


def test_car_option_without_car_cost_params_raises():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(),
        route=make_car_route(),
        car_cost_params=None,
    )

    with pytest.raises(InvalidPurchaseOptionError):
        compute_cost_breakdown(option)


# ---------------------------------------------------------------------------
# compute_cost_breakdown — mode TRANSIT
# ---------------------------------------------------------------------------


def test_transit_cost_breakdown_uses_fare():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(price="2.50"),
        route=make_transit_route(fare_eur="1.90"),
    )

    breakdown = compute_cost_breakdown(option)

    assert breakdown.transport_fare_eur == Decimal("1.90")
    assert breakdown.fuel_cost_eur == Decimal("0")
    assert breakdown.total_cost_eur == Decimal("4.40")


def test_transit_route_without_fare_defaults_to_zero():
    route = make_transit_route()
    route = route.model_copy(update={"fare_eur": None})
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(price="2.50"),
        route=route,
    )

    breakdown = compute_cost_breakdown(option)

    assert breakdown.transport_fare_eur == Decimal("0")
    assert breakdown.total_cost_eur == Decimal("2.50")


# ---------------------------------------------------------------------------
# compute_cost_breakdown — mode WALK
# ---------------------------------------------------------------------------


def test_walk_option_has_no_transport_cost():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(price="2.50"),
        route=make_walk_route(),
    )

    breakdown = compute_cost_breakdown(option)

    assert breakdown.total_cost_eur == Decimal("2.50")
    assert breakdown.total_duration_minutes == 12.0


# ---------------------------------------------------------------------------
# evaluate_option
# ---------------------------------------------------------------------------


def test_evaluate_option_wraps_breakdown_with_original_option():
    option = PurchaseOption(
        product=make_product(),
        store=make_store(),
        price=make_price(),
        route=make_walk_route(),
    )

    evaluated = evaluate_option(option)

    assert evaluated.option == option
    assert evaluated.cost_breakdown.total_cost_eur == option.price.price


# ---------------------------------------------------------------------------
# rank_options
# ---------------------------------------------------------------------------


def test_rank_options_sorts_by_total_cost_ascending():
    cheap_option = PurchaseOption(
        product=make_product(),
        store=make_store("s1"),
        price=make_price(store_id="s1", price="2.00"),
        route=make_walk_route(),
    )
    expensive_option = PurchaseOption(
        product=make_product(),
        store=make_store("s2"),
        price=make_price(store_id="s2", price="4.00"),
        route=make_walk_route(),
    )

    ranked = rank_options([expensive_option, cheap_option])

    assert ranked[0].option.store.id == "s1"
    assert ranked[1].option.store.id == "s2"


def test_rank_options_sorts_by_duration_when_requested():
    slow_option = PurchaseOption(
        product=make_product(),
        store=make_store("s1"),
        price=make_price(store_id="s1", price="2.00"),
        route=make_walk_route(duration_minutes=40.0),
    )
    fast_option = PurchaseOption(
        product=make_product(),
        store=make_store("s2"),
        price=make_price(store_id="s2", price="2.00"),
        route=make_walk_route(duration_minutes=5.0),
    )

    ranked = rank_options([slow_option, fast_option], sort_by="total_duration_minutes")

    assert ranked[0].option.store.id == "s2"
    assert ranked[1].option.store.id == "s1"


def test_rank_options_excludes_invalid_options_instead_of_raising():
    valid_option = PurchaseOption(
        product=make_product(),
        store=make_store("s1"),
        price=make_price(store_id="s1"),
        route=make_walk_route(),
    )
    invalid_option = PurchaseOption(
        product=make_product(),
        store=make_store("s2"),
        price=make_price(store_id="s2"),
        route=make_car_route(),
        car_cost_params=None,  # invalide : CAR sans car_cost_params
    )

    ranked = rank_options([valid_option, invalid_option])

    assert len(ranked) == 1
    assert ranked[0].option.store.id == "s1"


def test_rank_options_rejects_unknown_sort_key():
    with pytest.raises(ValueError):
        rank_options([], sort_by="not_a_real_field")


def test_rank_options_handles_empty_list():
    assert rank_options([]) == []


# ---------------------------------------------------------------------------
# Validation des modèles (garde-fous au niveau des données)
# ---------------------------------------------------------------------------


def test_price_must_be_positive():
    with pytest.raises(Exception):  # pydantic.ValidationError
        make_price(price="0")


def test_price_rejects_unreasonable_amount():
    with pytest.raises(Exception):  # pydantic.ValidationError
        make_price(price="99999")
