import pandas as pd

from src.generator import build_all, clabe_check

TABLES = {"customers", "accounts", "loans", "loan_months", "transfers", "alerts"}


def test_clabe_check_digit():
    assert clabe_check("03218000011835971") == "9"


def test_tables_and_keys():
    t = build_all(n_customers=300, seed=7)
    assert set(t) == TABLES
    assert t["customers"].customer_id.is_unique
    assert t["transfers"].transfer_id.is_unique
    assert t["accounts"].clabe.str.len().eq(18).all()
    assert t["transfers"].account_id.isin(t["accounts"].account_id).all()
    assert t["alerts"].transfer_id.isin(t["transfers"].transfer_id).all()
    assert "is_fraud" not in t["transfers"].columns


def test_alert_resolutions():
    a = build_all(n_customers=300, seed=7)["alerts"]
    closed = a[a.status == "cerrada"]
    assert closed.resolution.isin(["fraude_confirmado", "falso_positivo", "reporte_pld"]).all()
    assert a[a.status == "abierta"].resolution.isna().all()


def test_march_fraud_spike():
    a = build_all(n_customers=2000, seed=42)["alerts"]
    fraud = a[a.resolution == "fraude_confirmado"]
    by_month = fraud.created_at.dt.to_period("M").value_counts()
    march = by_month[pd.Period("2026-03")]
    assert march > 2 * by_month.drop(pd.Period("2026-03")).median()