import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import date, timedelta
import os

fake = Faker('en_GB')
random.seed(42)
np.random.seed(42)

# ── Coverholder reference data ─────────────────────────────────────────────────

COVERHOLDERS = [
    {
        "coverholder_id": "CH001",
        "name": "Avonbridge Underwriting",
        "class_of_business": "Commercial Property",
        "territory": "UK-wide",
        "authority_limit": 2_000_000,
        "avg_premium": 4200,
        "avg_sum_insured": 850_000,
        "base_loss_ratio": 0.48,
        "postcodes": None,  # No restriction
    },
    {
        "coverholder_id": "CH002",
        "name": "Meridian Risk Solutions",
        "class_of_business": "EL/PL Liability",
        "territory": "UK-wide",
        "authority_limit": 1_500_000,
        "avg_premium": 3100,
        "avg_sum_insured": 500_000,
        "base_loss_ratio": 0.52,
        "postcodes": None,
    },
    {
        "coverholder_id": "CH003",
        "name": "Fortis Professional Risks",
        "class_of_business": "Professional Indemnity",
        "territory": "UK-wide",
        "authority_limit": 1_000_000,
        "avg_premium": 5500,
        "avg_sum_insured": 1_200_000,
        "base_loss_ratio": 0.50,
        "postcodes": None,
    },
    {
        "coverholder_id": "CH004",
        "name": "Southgate Property Partners",
        "class_of_business": "Commercial Property",
        "territory": "South East",
        "authority_limit": 500_000,
        "avg_premium": 1800,
        "avg_sum_insured": 400_000,
        "base_loss_ratio": 0.45,
        "postcodes": ["SE", "SW", "E", "EC", "WC", "W", "N", "NW",  # In-scope London
                      "BN", "CT", "ME", "TN", "RH", "GU", "KT", "SM",  # SE England
                      "SL", "RG", "OX", "HP", "AL", "SG", "CM", "SS"],
    },
    {
        "coverholder_id": "CH005",
        "name": "Ironclad Construction Risks",
        "class_of_business": "EL/PL Liability",
        "territory": "Construction sector",
        "authority_limit": 750_000,
        "avg_premium": 2600,
        "avg_sum_insured": 600_000,
        "base_loss_ratio": 0.55,
        "postcodes": None,
    },
]

# ── South East postcodes (in-scope for CH004) ──────────────────────────────────

SE_POSTCODES = ["SE1", "SE10", "SE15", "SW1", "SW6", "E1", "EC1", "BN1",
                "CT1", "ME1", "TN1", "RH1", "GU1", "KT1", "SM1", "SL1",
                "RG1", "OX1", "HP1", "AL1", "SG1", "CM1", "SS1", "BR1",
                "CR0", "DA1", "EN1", "HA1", "IG1", "KT2", "TW1", "UB1"]

# Out of scope postcodes — used for CH004 breaches
OUT_OF_SCOPE_POSTCODES = ["M1", "M2", "B1", "B2", "LS1", "LS2", "L1", "L2",
                           "S1", "S2", "NE1", "NE2", "BS1", "BS2", "CB1",
                           "OL1", "SK1", "WN1", "PR1"]

# ── Date helpers ───────────────────────────────────────────────────────────────

def months_between(start: date, end: date):
    """Yield the first day of each month between start and end."""
    current = start.replace(day=1)
    while current <= end:
        yield current
        # advance one month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

def month_end(d: date) -> date:
    """Return the last day of the month for a given date."""
    if d.month == 12:
        return d.replace(day=31)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)

PROJECT_START = date(2024, 1, 1)
PROJECT_END   = date(2025, 6, 30)

# ── Premium bordereaux generation ─────────────────────────────────────────────

def policies_per_month(ch: dict, month: date) -> int:
    """
    Controls how many policies each coverholder writes per month.
    CH002 ramps up in late 2025 to simulate authority limit pressure.
    """
    base = {
        "CH001": 18, "CH002": 14, "CH003": 10,
        "CH004": 12, "CH005": 9,
    }[ch["coverholder_id"]]

    # CH002: volume increases from month 13 (Jan 2025) onwards
    if ch["coverholder_id"] == "CH002" and month >= date(2025, 1, 1):
        base = int(base * 1.5)

    return max(1, int(np.random.normal(base, base * 0.15)))


def generate_postcode(ch: dict, force_breach: bool = False) -> str:
    """Return a realistic postcode, respecting territorial restrictions."""
    if ch["coverholder_id"] == "CH004":
        if force_breach:
            return random.choice(OUT_OF_SCOPE_POSTCODES) + " " + str(random.randint(1, 9)) + fake.lexify("??").upper()
        return random.choice(SE_POSTCODES) + " " + str(random.randint(1, 9)) + fake.lexify("??").upper()
    return fake.postcode()


def generate_premium_bordereaux() -> pd.DataFrame:
    records = []
    policy_counter = 1

    for month in months_between(PROJECT_START, PROJECT_END):
        for ch in COVERHOLDERS:
            n_policies = policies_per_month(ch, month)

            for i in range(n_policies):
                policy_ref = f"POL-{ch['coverholder_id']}-{policy_counter:05d}"
                policy_counter += 1

                # Inception date within the current month
                day = random.randint(1, 28)
                inception = month.replace(day=day)
                expiry = inception.replace(year=inception.year + 1)

                # Premium — normally distributed around the coverholder average
                premium = max(500, int(np.random.normal(ch["avg_premium"], ch["avg_premium"] * 0.3)))
                sum_insured = max(50_000, int(np.random.normal(ch["avg_sum_insured"], ch["avg_sum_insured"] * 0.25)))

                # Postcode — CH004 gets ~8% of policies outside territory
                if ch["coverholder_id"] == "CH004":
                    force_breach = random.random() < 0.08
                    postcode = generate_postcode(ch, force_breach=force_breach)
                else:
                    postcode = generate_postcode(ch)

                records.append({
                    "policy_ref":         policy_ref,
                    "coverholder_id":     ch["coverholder_id"],
                    "coverholder_name":   ch["name"],
                    "inception_date":     inception,
                    "expiry_date":        expiry,
                    "class_of_business":  ch["class_of_business"],
                    "insured_name":       fake.company(),
                    "postcode":           postcode,
                    "premium":            premium,
                    "sum_insured":        sum_insured,
                    "underwriting_year":  inception.year,
                    "bound_month":        month.strftime("%Y-%m"),
                })

    return pd.DataFrame(records)


# ── Claims bordereaux generation ───────────────────────────────────────────────

def get_loss_ratio(ch: dict, month: date) -> float:
    """
    Returns the target loss ratio for a coverholder in a given month.
    CH003 deteriorates from month 10 (Oct 2024) onwards.
    """
    base = ch["base_loss_ratio"]
    if ch["coverholder_id"] == "CH003":
        months_in = (month.year - PROJECT_START.year) * 12 + (month.month - PROJECT_START.month)
        if months_in >= 9:  # from Oct 2024
            deterioration = min(0.30, (months_in - 9) * 0.035)
            return base + deterioration
    return base + np.random.normal(0, 0.04)  # natural variance


def generate_claims_bordereaux(premium_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    claim_counter = 1

    for month in months_between(PROJECT_START, PROJECT_END):
        month_str = month.strftime("%Y-%m")

        for ch in COVERHOLDERS:
            ch_policies = premium_df[
                (premium_df["coverholder_id"] == ch["coverholder_id"]) &
                (premium_df["bound_month"] == month_str)
            ]

            if ch_policies.empty:
                continue

            total_premium = ch_policies["premium"].sum()
            target_lr = get_loss_ratio(ch, month)
            target_incurred = total_premium * target_lr

            # Decide how many claims to generate to hit target incurred
            avg_claim_size = ch["avg_premium"] * 2.5
            n_claims = max(0, int(target_incurred / avg_claim_size))

            for _ in range(n_claims):
                # Pick a random policy from this month's batch
                policy = ch_policies.sample(1).iloc[0]

                date_of_loss = policy["inception_date"] + timedelta(days=random.randint(1, 180))
                date_reported = date_of_loss + timedelta(days=random.randint(1, 45))

                reserve = max(500, int(np.random.normal(avg_claim_size, avg_claim_size * 0.4)))
                paid = int(reserve * random.uniform(0, 0.85)) if random.random() < 0.6 else 0
                status = "Closed" if paid >= reserve * 0.9 else ("Open" if paid == 0 else "Settled")

                claim_ref = f"CLM-{ch['coverholder_id']}-{claim_counter:05d}"
                claim_counter += 1

                records.append({
                    "claim_ref":          claim_ref,
                    "policy_ref":         policy["policy_ref"],
                    "coverholder_id":     ch["coverholder_id"],
                    "coverholder_name":   ch["name"],
                    "class_of_business":  ch["class_of_business"],
                    "date_of_loss":       date_of_loss,
                    "date_reported":      date_reported,
                    "reserve_amount":     reserve,
                    "paid_amount":        paid,
                    "incurred":           reserve + paid,
                    "claim_status":       status,
                    "report_month":       month_str,
                })

    return pd.DataFrame(records)


# ── Submission timeliness generation ──────────────────────────────────────────

def generate_submissions() -> pd.DataFrame:
    records = []

    for month in months_between(PROJECT_START, PROJECT_END):
        me = month_end(month)

        for ch in COVERHOLDERS:
            # CH005 is persistently late — avg 22 days, with runs of 3+ consecutive late months
            if ch["coverholder_id"] == "CH005":
                days_late = int(np.random.normal(22, 5))
            else:
                days_late = int(np.random.normal(10, 3))

            days_late = max(3, days_late)  # floor at 3 days
            submission_date = me + timedelta(days=days_late)
            on_time = days_late <= 15

            records.append({
                "coverholder_id":   ch["coverholder_id"],
                "coverholder_name": ch["name"],
                "report_month":     month.strftime("%Y-%m"),
                "month_end_date":   me,
                "submission_date":  submission_date,
                "days_from_month_end": days_late,
                "on_time":          on_time,
            })

    return pd.DataFrame(records)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "generated")
    os.makedirs(out_dir, exist_ok=True)

    print("Generating premium bordereaux...")
    premium_df = generate_premium_bordereaux()
    premium_df.to_csv(os.path.join(out_dir, "premium_bordereaux.csv"), index=False)
    print(f"  → {len(premium_df):,} policy records written")

    print("Generating claims bordereaux...")
    claims_df = generate_claims_bordereaux(premium_df)
    claims_df.to_csv(os.path.join(out_dir, "claims_bordereaux.csv"), index=False)
    print(f"  → {len(claims_df):,} claim records written")

    print("Generating submission timeliness data...")
    submissions_df = generate_submissions()
    submissions_df.to_csv(os.path.join(out_dir, "monthly_submissions.csv"), index=False)
    print(f"  → {len(submissions_df):,} submission records written")

    print("\nDone. Files saved to data/generated/")

    # Quick sanity check
    print("\n── Sanity check ──────────────────────────────────────────────────")
    print("\nPremium by coverholder (total):")
    print(premium_df.groupby("coverholder_name")["premium"].sum().apply(lambda x: f"£{x:,.0f}"))

    print("\nCH003 loss ratios by month (should deteriorate from Oct 2024):")
    ch3_claims = claims_df[claims_df["coverholder_id"] == "CH003"].groupby("report_month")["incurred"].sum()
    ch3_premium = premium_df[premium_df["coverholder_id"] == "CH003"].groupby("bound_month")["premium"].sum()
    ch3_lr = (ch3_claims / ch3_premium).dropna()
    print(ch3_lr.apply(lambda x: f"{x:.1%}"))

    print("\nCH004 out-of-scope postcode count:")
    se_prefixes = tuple(["SE", "SW", "E1", "EC", "WC", "W1", "N1", "NW",
                          "BN", "CT", "ME", "TN", "RH", "GU", "KT", "SM",
                          "SL", "RG", "OX", "HP", "AL", "SG", "CM", "SS",
                          "BR", "CR", "DA", "EN", "HA", "IG", "TW", "UB"])
    ch4 = premium_df[premium_df["coverholder_id"] == "CH004"]
    breaches = ch4[~ch4["postcode"].str.startswith(se_prefixes)]
    print(f"  {len(breaches)} policies outside South East territory")