import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

DB_USER     = "postgres"
DB_PASSWORD = "postgres"
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "da_monitoring"

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


class MonitoringEngine:

    def __init__(self):
        self.run_date = datetime.now()
        self.flags = []

    def _query(self, sql: str) -> pd.DataFrame:
        with engine.connect() as conn:
            return pd.read_sql(text(sql), conn)

    # ── Check 1: Loss ratio deterioration ─────────────────────────────────────
    def check_loss_ratio_deterioration(self):
        df = self._query("SELECT * FROM vw_monthly_loss_ratios ORDER BY coverholder_id, bound_month")

        for ch_id, group in df.groupby("coverholder_id"):
            group = group.sort_values("bound_month").reset_index(drop=True)
            ch_name = group["coverholder_name"].iloc[0]

            # Latest rolling ratio
            latest = group.iloc[-1]
            latest_lr = latest["rolling_3m_loss_ratio"]

            if pd.isna(latest_lr):
                continue

            # Prior 3-month average (rows 4-6 from end)
            prior = group.iloc[-6:-3]["rolling_3m_loss_ratio"].mean()

            if latest_lr > 75:
                self._add_flag(
                    ch_id, ch_name,
                    flag_type="LOSS_RATIO_DETERIORATION",
                    severity="High",
                    detail=f"Rolling 3-month loss ratio at {latest_lr}% — exceeds 75% threshold. Immediate review recommended.",
                    period=latest["bound_month"]
                )
            elif latest_lr > 65:
                self._add_flag(
                    ch_id, ch_name,
                    flag_type="LOSS_RATIO_DETERIORATION",
                    severity="Medium",
                    detail=f"Rolling 3-month loss ratio at {latest_lr}% — approaching 75% escalation threshold.",
                    period=latest["bound_month"]
                )
            elif not pd.isna(prior) and (latest_lr - prior) > 15:
                self._add_flag(
                    ch_id, ch_name,
                    flag_type="LOSS_RATIO_DETERIORATION",
                    severity="Medium",
                    detail=f"Loss ratio increased {round(latest_lr - prior, 1)}pp over prior 3-month period ({round(prior,1)}% → {latest_lr}%).",
                    period=latest["bound_month"]
                )

    # ── Check 2: Authority limit utilisation ──────────────────────────────────
    def check_authority_utilisation(self):
        df = self._query("SELECT * FROM vw_authority_utilisation")

        for _, row in df.iterrows():
            if row["utilisation_status"] == "BREACH":
                self._add_flag(
                    row["coverholder_id"], row["coverholder_name"],
                    flag_type="AUTHORITY_LIMIT_BREACH",
                    severity="High",
                    detail=f"Cumulative premium £{row['cumulative_premium']:,.0f} represents {row['utilisation_pct']}% of £{row['authority_limit']:,.0f} authority limit for UY{row['underwriting_year']}. Binding must cease.",
                    period=str(row["underwriting_year"])
                )
            elif row["utilisation_status"] == "WARNING":
                self._add_flag(
                    row["coverholder_id"], row["coverholder_name"],
                    flag_type="AUTHORITY_LIMIT_WARNING",
                    severity="Medium",
                    detail=f"Cumulative premium at {row['utilisation_pct']}% of authority limit for UY{row['underwriting_year']}. Written notice recommended.",
                    period=str(row["underwriting_year"])
                )

    # ── Check 3: Geographic compliance ────────────────────────────────────────
    def check_geographic_compliance(self):
        df = self._query("SELECT * FROM vw_geographic_compliance WHERE is_breach = TRUE")

        if df.empty:
            return

        for ch_id, group in df.groupby("coverholder_id"):
            ch_name = group["coverholder_name"].iloc[0]
            count = len(group)
            postcodes = ", ".join(group["postcode"].unique()[:5])

            self._add_flag(
                ch_id, ch_name,
                flag_type="GEOGRAPHIC_SCOPE_BREACH",
                severity="High",
                detail=f"{count} policies bound outside permitted territory. Sample postcodes: {postcodes}. Potential unintended exposure — compliance review required.",
                period=None
            )

    # ── Check 4: Submission timeliness ────────────────────────────────────────
    def check_submission_timeliness(self):
        df = self._query("SELECT * FROM vw_submission_timeliness WHERE timeliness_status = 'LATE' ORDER BY coverholder_id, report_month")

        for ch_id, group in df.groupby("coverholder_id"):
            ch_name = group["coverholder_name"].iloc[0]
            total_late = len(group)
            avg_days = round(group["days_from_month_end"].mean(), 1)

            # Check for 3+ consecutive late months
            months = group["report_month"].tolist()
            consecutive = 1
            max_consecutive = 1
            for i in range(1, len(months)):
                if months[i] > months[i-1]:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 1

            severity = "High" if max_consecutive >= 3 else "Medium"

            self._add_flag(
                ch_id, ch_name,
                flag_type="LATE_BORDEREAUX_SUBMISSION",
                severity=severity,
                detail=f"{total_late} late submissions in period. Average {avg_days} days from month end vs 15-day SLA. Max consecutive late months: {max_consecutive}.",
                period=group["report_month"].iloc[-1]
            )

    # ── Flag helper ───────────────────────────────────────────────────────────
    def _add_flag(self, coverholder_id, coverholder_name, flag_type, severity, detail, period):
        self.flags.append({
            "run_date":        self.run_date,
            "coverholder_id":  coverholder_id,
            "coverholder_name": coverholder_name,
            "flag_type":       flag_type,
            "severity":        severity,
            "detail":          detail,
            "period":          period,
        })

    # ── Run all checks ────────────────────────────────────────────────────────
    def run_all_checks(self) -> pd.DataFrame:
        self.flags = []
        self.check_loss_ratio_deterioration()
        self.check_authority_utilisation()
        self.check_geographic_compliance()
        self.check_submission_timeliness()
        return pd.DataFrame(self.flags)

    # ── Write flags to database ───────────────────────────────────────────────
    def write_flags(self, flags_df: pd.DataFrame):
        if flags_df.empty:
            return
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM flags_log WHERE run_date::date = CURRENT_DATE"))
            conn.commit()
        flags_df.to_sql("flags_log", engine, if_exists="append", index=False)