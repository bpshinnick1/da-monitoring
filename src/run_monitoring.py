from monitoring_engine import MonitoringEngine

if __name__ == "__main__":
    print("=" * 60)
    print("DA MONITORING ENGINE — COVERHOLDER FLAG REPORT")
    print("=" * 60)

    engine = MonitoringEngine()
    flags = engine.run_all_checks()

    if flags.empty:
        print("\nNo flags raised. All coverholders within parameters.")
    else:
        # Summary by severity
        print(f"\nTotal flags raised: {len(flags)}")
        print(f"  High:   {len(flags[flags['severity'] == 'High'])}")
        print(f"  Medium: {len(flags[flags['severity'] == 'Medium'])}")
        print(f"  Low:    {len(flags[flags['severity'] == 'Low'])}")

        # Detail by coverholder
        print("\n" + "─" * 60)
        for _, row in flags.sort_values(
            ["severity", "coverholder_name"],
            key=lambda x: x.map({"High": 0, "Medium": 1, "Low": 2}) if x.name == "severity" else x
        ).iterrows():
            print(f"\n[{row['severity'].upper()}] {row['coverholder_name']}")
            print(f"  Type   : {row['flag_type']}")
            print(f"  Detail : {row['detail']}")
            if row['period']:
                print(f"  Period : {row['period']}")

        # Write to database
        engine.write_flags(flags)
        print("\n" + "─" * 60)
        print("Flags written to flags_log table.")

    print("\n" + "=" * 60)