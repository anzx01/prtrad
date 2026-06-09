from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import uuid

from sqlalchemy import func, select

from db.models import Market, MarketClassificationResult, MarketReviewTask, TagRuleVersion
from services.tagging.classifier import MarketAutoClassificationService
from services.tagging.default_rules import build_default_rule_version_create_input
from services.tagging.contracts import TagRuleInput, TagRuleVersionCreateInput
from services.tagging.service import TaggingRuleService
import services.tagging.classifier as tagging_classifier_module
import services.tagging.service as tagging_service_module

UTC = ZoneInfo("UTC")


class _AuditStub:
    def safe_write_event(self, *args, **kwargs):
        return None


def _patch_session_scope(monkeypatch, SessionLocal):
    @contextmanager
    def managed_session_scope():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(tagging_service_module, "session_scope", managed_session_scope)
    monkeypatch.setattr(tagging_classifier_module, "session_scope", managed_session_scope)
    monkeypatch.setattr(tagging_service_module, "get_audit_log_service", lambda: _AuditStub())


def test_seed_default_rule_version_is_idempotent(test_db, monkeypatch):
    SessionLocal = test_db
    _patch_session_scope(monkeypatch, SessionLocal)

    service = TaggingRuleService()
    first = service.seed_default_rule_version(actor_id="tester")
    second = service.seed_default_rule_version(actor_id="tester")

    assert first["version_code"] == "tag_default_v2"
    assert first["status"] == "active"
    assert second["version_code"] == first["version_code"]

    rule_codes = {rule["rule_code"] for rule in first["rules"]}
    assert "CRYPTO_WHITE_BY_QUESTION" in rule_codes
    assert "SPORTS_BLACK_RULE" in rule_codes

    session = SessionLocal()
    try:
        version_count = session.scalar(select(func.count()).select_from(TagRuleVersion))
        assert version_count == 1
    finally:
        session.close()


def test_classifier_cancels_stale_review_tasks_after_new_rule_version(test_db, test_settings, monkeypatch):
    SessionLocal = test_db
    _patch_session_scope(monkeypatch, SessionLocal)

    service = TaggingRuleService()
    service.seed_default_dictionary(actor_id="tester")
    bootstrap = service.create_rule_version(
        TagRuleVersionCreateInput(
            version_code="bootstrap_review_queue_v1",
            change_reason="bootstrap review queue fallback",
            rules=[
                TagRuleInput(
                    rule_code="BOOTSTRAP_REVIEW_FALLBACK",
                    rule_name="Bootstrap review fallback",
                    rule_kind="keyword",
                    action_type="require_review",
                    priority=10,
                    match_scope=["question"],
                    match_operator="contains_any",
                    match_payload={"keywords": ["__bootstrap_no_match__"]},
                    effect_payload={"confidence": 0.50},
                )
            ],
        ),
        actor_id="tester",
        auto_activate=True,
    )

    now = datetime.now(UTC)
    market_id = uuid.uuid4()
    old_classification_id = uuid.uuid4()
    old_task_id = uuid.uuid4()

    session = SessionLocal()
    try:
        session.add(
            Market(
                id=market_id,
                market_id="btc-up-down-test",
                question="Bitcoin Up or Down - April 9, 9:45PM-10:00PM ET",
                category_raw="Up or Down",
                market_status="inactive_from_feed",
                creation_time=now - timedelta(days=2),
                open_time=now - timedelta(days=1),
                close_time=now + timedelta(hours=2),
                source_updated_at=now,
            )
        )
        session.add(
            MarketClassificationResult(
                id=old_classification_id,
                market_ref_id=market_id,
                rule_version=bootstrap["version_code"],
                source_fingerprint="bootstrap-fingerprint",
                classification_status="ReviewRequired",
                primary_category_code=None,
                admission_bucket_code="LIST_GREY",
                confidence=Decimal("0.60"),
                requires_review=True,
                conflict_count=0,
                failure_reason_code="TAG_NO_CATEGORY_MATCH",
                result_details={"source": "bootstrap"},
                classified_at=now - timedelta(minutes=10),
            )
        )
        session.add(
            MarketReviewTask(
                id=old_task_id,
                market_ref_id=market_id,
                classification_result_id=old_classification_id,
                queue_status="pending",
                review_reason_code="TAG_NO_CATEGORY_MATCH",
                priority="normal",
                review_payload={"source": "bootstrap"},
            )
        )
        session.commit()
    finally:
        session.close()

    default_version = service.seed_default_rule_version(actor_id="tester")
    test_settings.tagging_market_limit = 10
    classifier = MarketAutoClassificationService(test_settings)

    result = classifier.classify_markets(classified_at=now)
    assert result["created"] == 1
    assert result["Tagged"] == 1
    assert result["review_tasks_created"] == 0

    session = SessionLocal()
    try:
        old_task = session.get(MarketReviewTask, old_task_id)
        assert old_task is not None
        assert old_task.queue_status == "cancelled"
        assert old_task.review_payload["cancelled_reason"] == "superseded_by_reclassification"
        assert old_task.review_payload["superseded_rule_version"] == default_version["version_code"]

        unresolved_tasks = session.scalars(
            select(MarketReviewTask).where(
                MarketReviewTask.market_ref_id == market_id,
                MarketReviewTask.queue_status.in_(["pending", "open", "in_progress"]),
            )
        ).all()
        assert unresolved_tasks == []

        latest = session.scalar(
            select(MarketClassificationResult)
            .where(
                MarketClassificationResult.market_ref_id == market_id,
                MarketClassificationResult.rule_version == default_version["version_code"],
            )
        )
        assert latest is not None
        assert latest.classification_status == "Tagged"
        assert latest.admission_bucket_code == "LIST_WHITE"
        assert latest.primary_category_code == "CAT_CRYPTO_ASSET"
    finally:
        session.close()

def test_seed_default_rule_version_restores_superseded_baseline(test_db, monkeypatch):
    SessionLocal = test_db
    _patch_session_scope(monkeypatch, SessionLocal)

    service = TaggingRuleService()
    baseline = service.seed_default_rule_version(actor_id="tester")
    experimental = service.create_rule_version(
        build_default_rule_version_create_input(version_code="tag_experiment_v2"),
        actor_id="tester",
        auto_activate=True,
    )
    assert experimental["status"] == "active"

    fixed_now = datetime(2026, 4, 9, 8, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(tagging_service_module, "_now_utc", lambda: fixed_now)

    restored = service.seed_default_rule_version(actor_id="tester")

    assert restored["status"] == "active"
    assert restored["release_kind"] == "rollback"
    assert restored["base_version_code"] == baseline["version_code"]
    assert restored["version_code"] == "tag_default_v2_restore_20260409_080000"

    session = SessionLocal()
    try:
        active_versions = session.scalars(
            select(TagRuleVersion).where(TagRuleVersion.status == "active")
        ).all()
        assert len(active_versions) == 1
        assert active_versions[0].version_code == restored["version_code"]
    finally:
        session.close()


def test_default_rules_auto_decide_common_market_shapes(test_db, test_settings, monkeypatch):
    SessionLocal = test_db
    _patch_session_scope(monkeypatch, SessionLocal)

    service = TaggingRuleService()
    service.seed_default_dictionary(actor_id="tester")
    default_version = service.seed_default_rule_version(actor_id="tester")

    now = datetime.now(UTC)
    markets = [
        Market(
            id=uuid.uuid4(),
            market_id="sports-ou-test",
            question="Ehime FC vs. Kataller Toyama: O/U 3.5",
            description="This market resolves based on the final score after regulation time.",
            category_raw=None,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(hours=6),
            source_updated_at=now,
        ),
        Market(
            id=uuid.uuid4(),
            market_id="esports-map-test",
            question="Valorant: All Gamers vs Bilibili Gaming - Map 2 Winner",
            description="This market refers to the Valorant match between All Gamers and Bilibili Gaming.",
            category_raw=None,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(hours=6),
            source_updated_at=now,
        ),
        Market(
            id=uuid.uuid4(),
            market_id="sports-win-test",
            question="Will AC Milan win on 2026-04-26?",
            description=(
                "In the upcoming game, scheduled for April 26, 2026. "
                "This market refers only to the outcome within the first 90 minutes of regular play plus stoppage time. "
                "The primary resolution source for this market is the official statistics of the event."
            ),
            category_raw=None,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(hours=6),
            source_updated_at=now,
        ),
        Market(
            id=uuid.uuid4(),
            market_id="crypto-up-down-test",
            question="XRP Up or Down - April 13, 6:45PM-6:50PM ET",
            description="This market resolves based on the XRP price at the end of the interval.",
            category_raw=None,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(hours=1),
            source_updated_at=now,
        ),
        Market(
            id=uuid.uuid4(),
            market_id="esports-special-shape-test",
            question="Game 2: Both Teams Destroy Inhibitors?",
            description="League of Legends match special prop market.",
            category_raw=None,
            market_status="active_accepting_orders",
            creation_time=now - timedelta(days=2),
            open_time=now - timedelta(days=1),
            close_time=now + timedelta(hours=6),
            source_updated_at=now,
        ),
    ]
    market_ids = [market.id for market in markets]

    session = SessionLocal()
    try:
        session.add_all(markets)
        session.commit()
    finally:
        session.close()

    test_settings.tagging_market_limit = 10
    classifier = MarketAutoClassificationService(test_settings)
    result = classifier.classify_markets(classified_at=now)

    assert result["created"] == 5
    assert result["Tagged"] == 1
    assert result["Blocked"] == 4
    assert result["ReviewRequired"] == 0
    assert result["review_tasks_created"] == 0

    session = SessionLocal()
    try:
        results = {
            classification.market_ref_id: classification
            for classification in session.scalars(
                select(MarketClassificationResult).where(
                    MarketClassificationResult.rule_version == default_version["version_code"]
                )
            ).all()
        }
        queued_tasks = session.scalars(select(MarketReviewTask)).all()
        assert queued_tasks == []

        crypto_result = results[market_ids[3]]
        assert crypto_result.classification_status == "Tagged"
        assert crypto_result.primary_category_code == "CAT_CRYPTO_ASSET"
        assert crypto_result.admission_bucket_code == "LIST_WHITE"
        assert crypto_result.requires_review is False

        for market_id in [market_ids[0], market_ids[1], market_ids[2], market_ids[4]]:
            sports_result = results[market_id]
            assert sports_result.classification_status == "Blocked"
            assert sports_result.primary_category_code == "CAT_SPORTS"
            assert sports_result.admission_bucket_code == "LIST_BLACK"
            assert sports_result.requires_review is False
    finally:
        session.close()


def test_classifier_auto_blocks_unknown_markets_without_manual_review(test_db, test_settings, monkeypatch):
    SessionLocal = test_db
    _patch_session_scope(monkeypatch, SessionLocal)

    service = TaggingRuleService()
    service.seed_default_dictionary(actor_id="tester")
    default_version = service.seed_default_rule_version(actor_id="tester")

    now = datetime.now(UTC)
    market_id = uuid.uuid4()

    session = SessionLocal()
    try:
        session.add(
            Market(
                id=market_id,
                market_id="unknown-shape-test",
                question="Will this experimental market format resolve before Friday?",
                description="No known default rule should match this question.",
                category_raw=None,
                market_status="active_accepting_orders",
                creation_time=now - timedelta(days=1),
                open_time=now - timedelta(hours=12),
                close_time=now + timedelta(hours=12),
                source_updated_at=now,
            )
        )
        session.commit()
    finally:
        session.close()

    test_settings.tagging_market_limit = 10
    classifier = MarketAutoClassificationService(test_settings)
    result = classifier.classify_markets(classified_at=now)

    assert result["created"] == 1
    assert result["Blocked"] == 1
    assert result["ReviewRequired"] == 0
    assert result["review_tasks_created"] == 0

    session = SessionLocal()
    try:
        latest = session.scalar(
            select(MarketClassificationResult).where(
                MarketClassificationResult.market_ref_id == market_id,
                MarketClassificationResult.rule_version == default_version["version_code"],
            )
        )
        assert latest is not None
        assert latest.classification_status == "Blocked"
        assert latest.primary_category_code is None
        assert latest.admission_bucket_code == "LIST_BLACK"
        assert latest.requires_review is False
        assert latest.failure_reason_code == "TAG_NO_CATEGORY_MATCH"
        assert session.scalars(select(MarketReviewTask)).all() == []
    finally:
        session.close()

