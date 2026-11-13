import os
import random
import unicodedata
from datetime import date, timedelta

import numpy as np
import pandas as pd

FIRST_M = ["José", "Juan", "Luis", "Carlos", "Miguel", "Jorge", "Alejandro", "Fernando", "Ricardo", "Eduardo"]
FIRST_F = ["María", "Guadalupe", "Ana", "Laura", "Patricia", "Gabriela", "Verónica", "Claudia", "Mónica", "Sofía"]
LAST = ["Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez", "Ramírez", "Cruz",
        "Flores", "Gómez", "Morales", "Vázquez", "Reyes", "Jiménez", "Torres", "Díaz", "Ruiz", "Mendoza"]
STATES = {"Ciudad de México": "DF", "Estado de México": "MC", "Jalisco": "JC", "Nuevo León": "NL", "Puebla": "PL",
          "Guanajuato": "GT", "Veracruz": "VZ", "Chihuahua": "CH", "Tamaulipas": "TS", "Yucatán": "YN"}
STATE_W = [.22, .16, .12, .11, .07, .07, .08, .06, .06, .05]
BANKS = ["002", "012", "014", "021", "072", "127", "137", "638"]
ANALYSTS = ["arodriguez", "mlopez", "jtorres", "pvazquez", "ecruz", "lmendoza"]
GRADES = {"A": (.015, .24), "B": (.03, .32), "C": (.055, .42), "D": (.09, .55), "E": (.14, .68)}

START = date(2024, 11, 1)
END = date(2026, 10, 31)
TX_START = pd.Timestamp("2025-11-01")
TX_END = pd.Timestamp("2026-10-31 23:59:59")
OUR_BANK = "999"

HOUR_P = np.array([1, 1, 1, 1, 1, 2, 4, 6, 8, 9, 9, 9, 9, 9, 9, 9, 9, 9, 8, 7, 6, 5, 3, 2], dtype=float)
HOUR_P /= HOUR_P.sum()


def plain(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


def clabe_check(body):
    w = [3, 7, 1] * 6
    s = sum(int(d) * w[i] % 10 for i, d in enumerate(body))
    return str((10 - s % 10) % 10)


def make_clabe(rng, bank):
    body = f"{bank}{rng.randint(1, 999):03d}{rng.randint(0, 10**11 - 1):011d}"
    return body + clabe_check(body)


def person_ids(rng, first, last1, last2, birth, sex, state_code):
    f, l1, l2 = plain(first), plain(last1), plain(last2)
    vowel = next((c for c in l1[1:] if c in "AEIOU"), "X")
    cons = lambda s: next((c for c in s[1:] if c not in "AEIOU"), "X")
    base = l1[0] + vowel + l2[0] + f[0]
    ymd = birth.strftime("%y%m%d")
    alnum = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    rfc = base + ymd + "".join(rng.choice(alnum) for _ in range(3))
    tail = rng.choice("0123456789" if birth.year < 2000 else "ABCDEFGH") + str(rng.randint(0, 9))
    curp = base + ymd + sex + state_code + cons(l1) + cons(l2) + cons(f) + tail
    return rfc, curp


def month_ends(start, end):
    out, d = [], date(start.year, start.month, 1)
    while d <= end:
        nxt = date(d.year + d.month // 12, d.month % 12 + 1, 1)
        out.append(nxt - timedelta(days=1))
        d = nxt
    return out


def build_customers(rng, n):
    rows = []
    for i in range(1, n + 1):
        sex = rng.choice("HM")
        first = rng.choice(FIRST_M if sex == "H" else FIRST_F)
        l1, l2 = rng.choice(LAST), rng.choice(LAST)
        birth = date(1958, 1, 1) + timedelta(days=rng.randint(0, 365 * 46))
        state = rng.choices(list(STATES), STATE_W)[0]
        segment = rng.choices(["masivo", "preferente", "pyme"], [.7, .2, .1])[0]
        mu = {"masivo": 9.6, "preferente": 10.8, "pyme": 10.4}[segment]
        income = round(rng.lognormvariate(mu, .45), -2)
        rfc, curp = person_ids(rng, first, l1, l2, birth, sex, STATES[state])
        since = START - timedelta(days=rng.randint(0, 365 * 8))
        rows.append((f"C{i:06d}", f"{first} {l1} {l2}", rfc, curp, birth, sex, state, segment, income, since))
    cols = ["customer_id", "full_name", "rfc", "curp", "birth_date", "sex", "state", "segment",
            "monthly_income", "customer_since"]
    return pd.DataFrame(rows, columns=cols)


def build_accounts(rng, customers):
    rows = []
    for c in customers.itertuples():
        for _ in range(1 + (rng.random() < .2)):
            opened = c.customer_since + timedelta(days=rng.randint(0, 400))
            rows.append((f"A{len(rows) + 1:07d}", c.customer_id, make_clabe(rng, OUR_BANK),
                         rng.choice(["debito", "nomina"]), min(opened, START)))
    return pd.DataFrame(rows, columns=["account_id", "customer_id", "clabe", "product", "opened_at"])


def grade_for(rng, income):
    shift = 0 if income > 40000 else 1 if income > 15000 else 2
    return "ABCDE"[min(4, shift + rng.choices([0, 1, 2], [.5, .35, .15])[0])]


def build_loans(rng, customers):
    rows, span = [], (END - timedelta(days=60) - (START - timedelta(days=365))).days
    for c in customers.itertuples():
        n = rng.choices([0, 1, 2], [.3, .55, .15])[0]
        for _ in range(n):
            product = rng.choices(["tarjeta", "personal", "nomina"], [.55, .3, .15])[0]
            grade = grade_for(rng, c.monthly_income)
            if product == "tarjeta":
                amount, term = round(c.monthly_income * rng.uniform(.8, 3), -3), None
            else:
                amount, term = round(c.monthly_income * rng.uniform(2, 8), -3), rng.choice([12, 18, 24, 36, 48])
            orig = START - timedelta(days=365) + timedelta(days=rng.randint(0, span))
            rows.append((f"L{len(rows) + 1:07d}", c.customer_id, product, grade, amount, GRADES[grade][1], term, orig))
    cols = ["loan_id", "customer_id", "product", "risk_grade", "amount", "annual_rate", "term_months",
            "origination_date"]
    return pd.DataFrame(rows, columns=cols)


def stress(period, segment):
    return 2.0 if segment == "masivo" and date(2025, 12, 1) <= period <= date(2026, 4, 30) else 1.0


def build_loan_months(rng, loans, customers):
    seg = customers.set_index("customer_id").segment.to_dict()
    months = month_ends(START - timedelta(days=365), END)
    rows = []
    for ln in loans.itertuples():
        p_miss = GRADES[ln.risk_grade][0]
        r = ln.annual_rate / 12
        if ln.product == "tarjeta":
            balance = ln.amount * rng.uniform(.2, .7)
            installment = None
        else:
            balance = ln.amount
            installment = ln.amount * r / (1 - (1 + r) ** -ln.term_months)
        dpd, paid_n = 0, 0
        for m in months:
            if m < ln.origination_date:
                continue
            if ln.product == "tarjeta":
                balance = min(ln.amount, max(0, balance * rng.uniform(.85, 1.2)))
                due = round(max(balance * .05, 200 if balance > 0 else 0), 2)
            else:
                due = round(installment * (1 + dpd // 30), 2)
            missed = rng.random() < p_miss * stress(m, seg[ln.customer_id]) * (3 if dpd else 1)
            if dpd and not missed and rng.random() < .4:
                missed = True
            if missed:
                paid = round(due * rng.choice([0, 0, rng.uniform(.1, .5)]), 2)
                dpd += 30
            else:
                if ln.product != "tarjeta":
                    paid_n += 1 + dpd // 30
                    balance = max(0, ln.amount * (1 - paid_n / ln.term_months))
                paid, dpd = due, 0
            status = "castigado" if dpd >= 180 else "vencido" if dpd >= 90 else "vigente"
            if ln.product != "tarjeta" and balance == 0:
                status = "liquidado"
            if m >= START:
                rows.append((ln.loan_id, m, round(balance, 2), due, paid, dpd, status))
            if status in ("castigado", "liquidado"):
                break
    cols = ["loan_id", "period_end", "balance", "amount_due", "amount_paid", "days_past_due", "status"]
    return pd.DataFrame(rows, columns=cols)


def build_transfers(rng, nrng, accounts):
    counts = nrng.poisson(36, len(accounts))
    acc = np.repeat(accounts.account_id.values, counts)
    n = len(acc)
    day = nrng.integers(0, 365, n)
    channel = nrng.choice(["app", "web", "sucursal"], n, p=[.7, .2, .1])
    march = (day >= 120) & (day < 151)
    fraud = nrng.random(n) < np.where(march & (channel == "app"), .012, .0015)
    hour = nrng.choice(24, n, p=HOUR_P)
    hour = np.where(fraud & (nrng.random(n) < .5), nrng.integers(0, 5, n), hour)
    amount = np.minimum(nrng.lognormal(7.8, 1.0, n), 400000)
    amount = np.where(fraud, nrng.lognormal(9.8, .6, n), amount)
    new_benef = np.where(fraud, nrng.random(n) < .9, nrng.random(n) < .1)
    new_device = np.where(fraud, nrng.random(n) < .7, nrng.random(n) < .03)
    secs = nrng.integers(0, 3600, n)
    ts = TX_START + pd.to_timedelta(day, "D") + pd.to_timedelta(hour, "h") + pd.to_timedelta(secs, "s")
    df = pd.DataFrame({"account_id": acc, "ts": ts, "amount": amount.round(2), "channel": channel,
                       "new_beneficiary": new_benef, "new_device": new_device, "is_fraud": fraud})

    smurfs = []
    for a in rng.sample(list(accounts.account_id), 25):
        first_day = 30 * rng.randint(0, 11)
        for _ in range(rng.randint(4, 8)):
            t = TX_START + pd.Timedelta(days=first_day + rng.randint(0, 27), hours=rng.randint(9, 18),
                                        minutes=rng.randint(0, 59))
            smurfs.append((a, t, round(rng.uniform(40000, 49900), 2), rng.choice(["web", "sucursal"]),
                           True, False, False))
    df = pd.concat([df, pd.DataFrame(smurfs, columns=df.columns)], ignore_index=True)

    risky = ["127", "137", "638"]
    df["dest_bank"] = [rng.choice(risky) if f and rng.random() < .6 else rng.choice(BANKS) for f in df.is_fraud]
    df["dest_clabe"] = [make_clabe(rng, b) for b in df.dest_bank]
    df = df.sort_values("ts", ignore_index=True)
    df.insert(0, "transfer_id", [f"T{i:08d}" for i in range(1, len(df) + 1)])
    return df


def build_alerts(nrng, transfers, accounts, customers):
    income = transfers.account_id.map(accounts.set_index("account_id").customer_id).map(
        customers.set_index("customer_id").monthly_income)
    band = transfers.amount.between(40000, 49999.99)
    month = transfers.ts.dt.to_period("M")
    hits = transfers[band].groupby([transfers.account_id[band], month[band]]).transfer_id.transform("size")
    structuring = pd.Series(False, index=transfers.index)
    structuring[hits.index] = hits >= 3

    rules = np.select(
        [transfers.new_beneficiary & transfers.new_device,
         structuring,
         (transfers.ts.dt.hour < 6) & (transfers.amount >= 10000),
         transfers.amount > 3 * income,
         transfers.amount >= 50000],
        ["R02_BENEF_DISPOSITIVO_NUEVO", "R04_FRACCIONAMIENTO", "R03_NOCTURNO", "R05_MONTO_VS_INGRESO",
         "R01_MONTO_ALTO"],
        default="")
    a = transfers[rules != ""].copy()
    a["rule_code"] = rules[rules != ""]
    n = len(a)

    roll = nrng.random(n)
    resolution = np.select(
        [a.is_fraud,
         (a.rule_code == "R04_FRACCIONAMIENTO") & (roll < .6),
         a.rule_code.isin(["R01_MONTO_ALTO", "R05_MONTO_VS_INGRESO"]) & (roll < .03)],
        ["fraude_confirmado", "reporte_pld", "reporte_pld"],
        default="falso_positivo")
    created = a.ts + pd.to_timedelta(nrng.integers(1, 10, n), "m")
    hours = np.where(a.is_fraud, nrng.lognormal(1.2, .6, n), nrng.lognormal(2.5, .8, n))
    closed = created + pd.to_timedelta(hours, "h")
    is_open = (closed > TX_END).values
    recovered = np.where(resolution == "fraude_confirmado", a.amount * nrng.uniform(0, .6, n), 0).round(2)

    return pd.DataFrame({
        "alert_id": [f"AL{i:07d}" for i in range(1, n + 1)],
        "transfer_id": a.transfer_id.values,
        "rule_code": a.rule_code.values,
        "created_at": created.values,
        "analyst": nrng.choice(ANALYSTS, n, p=[.25, .2, .2, .15, .1, .1]),
        "status": np.where(is_open, "abierta", "cerrada"),
        "resolution": np.where(is_open, None, resolution),
        "closed_at": closed.where(~is_open).values,
        "recovered_amount": np.where(is_open, 0, recovered),
    })


def build_all(n_customers=5000, seed=42):
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    customers = build_customers(rng, n_customers)
    accounts = build_accounts(rng, customers)
    loans = build_loans(rng, customers)
    loan_months = build_loan_months(rng, loans, customers)
    transfers = build_transfers(rng, nrng, accounts)
    alerts = build_alerts(nrng, transfers, accounts, customers)
    return {
        "customers": customers,
        "accounts": accounts,
        "loans": loans,
        "loan_months": loan_months,
        "transfers": transfers.drop(columns="is_fraud"),
        "alerts": alerts,
    }


def write(out_dir, n_customers=5000, seed=42):
    tables = build_all(n_customers, seed)
    for name, df in tables.items():
        os.makedirs(f"{out_dir}/{name}", exist_ok=True)
        df.to_csv(f"{out_dir}/{name}/{name}.csv", index=False)
    return {name: len(df) for name, df in tables.items()}