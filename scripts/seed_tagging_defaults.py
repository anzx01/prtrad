from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "apps" / "api"
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

from services.tagging import get_market_auto_classification_service, get_tagging_rule_service
from services.tagging.default_rules import DEFAULT_RULE_VERSION_CODE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed default tagging dictionary and rule version.")
    parser.add_argument("--version-code", default=DEFAULT_RULE_VERSION_CODE)
    parser.add_argument("--no-activate", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--market-limit", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = get_tagging_rule_service()

    result = {
        "dictionary": service.seed_default_dictionary(actor_id="system", actor_type="system"),
        "rule_version": service.seed_default_rule_version(
            version_code=args.version_code,
            actor_id="system",
            actor_type="system",
            auto_activate=not args.no_activate,
        ),
    }

    if args.classify:
        classifier = get_market_auto_classification_service()
        result["classification"] = classifier.classify_markets(
            classified_at=datetime.now(UTC),
            market_limit=args.market_limit,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())