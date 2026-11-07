import pytest
from app.models.audit import AuditEvent
from app.models.enums import AuditAction, AuditResult
from app.services.audit_service import AuditService, GENESIS_HASH


def test_audit_event_hash_chaining(db_session):
    # Log 3 events
    e1 = AuditService.log_event(
        db=db_session,
        action=AuditAction.USER_LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        actor_id=1,
        details={"ip": "127.0.0.1"}
    )
    assert e1.previous_hash == GENESIS_HASH
    assert len(e1.current_hash) == 64

    e2 = AuditService.log_event(
        db=db_session,
        action=AuditAction.DOCUMENT_READ,
        result=AuditResult.SUCCESS,
        actor_id=1,
        document_id=10,
        details={"action": "view"}
    )
    assert e2.previous_hash == e1.current_hash
    assert len(e2.current_hash) == 64

    e3 = AuditService.log_event(
        db=db_session,
        action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
        result=AuditResult.DENIED,
        actor_id=2,
        document_id=10,
        details={"reason": "forbidden"}
    )
    assert e3.previous_hash == e2.current_hash

    # Verify untampered integrity
    verification = AuditService.verify_chain_integrity(db_session)
    assert verification["valid"] is True
    assert verification["total_events"] == 3


def test_tamper_detection_on_modified_details(db_session):
    # Log 2 events
    AuditService.log_event(
        db=db_session,
        action=AuditAction.USER_LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        actor_id=1
    )
    AuditService.log_event(
        db=db_session,
        action=AuditAction.DOCUMENT_UPLOAD,
        result=AuditResult.SUCCESS,
        actor_id=1,
        document_id=5
    )

    # Tamper with the first event's details
    first_event = db_session.query(AuditEvent).filter(AuditEvent.id == 1).first()
    first_event.details = '{"malicious": "injected_data"}'
    db_session.commit()

    # Integrity check must detect the tampering
    verification = AuditService.verify_chain_integrity(db_session)
    assert verification["valid"] is False
    assert verification["tampered_event_id"] == 1
    assert "Tampering detected" in verification["reason"]
