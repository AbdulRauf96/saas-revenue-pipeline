"""One-off: what period lengths actually appear across all cached companies."""

from collections import Counter

from saas_revenue_pipeline.config import load_config
from saas_revenue_pipeline.parse import parse_file


def main() -> None:
    config = load_config()
    lengths: Counter[int] = Counter()
    grains: Counter[str] = Counter()

    for company in config.companies:
        path = config.raw_dir / f"CIK{company.cik}.json"
        if not path.exists():
            continue
        for fact in parse_file(path):
            if fact.period_type == "duration":
                lengths[fact.period_days] += 1
            grains[fact.grain] += 1

    print("grain buckets:")
    for grain, count in grains.most_common():
        print(f"  {grain:12} {count}")

    print("\nduration lengths (days), most common first:")
    for days, count in lengths.most_common(25):
        print(f"  {days:5} days  {count:5}")

    def in_a_bucket(d: int) -> bool:
        return (
            80 <= d <= 100
            or 170 <= d <= 195
            or 260 <= d <= 285
            or 350 <= d <= 380
        )    

    other = sorted(d for d in lengths if not (80 <= d <= 100 or 350 <= d <= 380))
    if other:
        print(f"\nfalling outside the buckets: {other}")


if __name__ == "__main__":
    main()