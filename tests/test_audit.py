from app.modules.audit import service as audit_service
from app.modules.secrets import service as secret_service
from app.modules.secrets.schemas import SecretCreate
from app.modules.simta import service as simta_service
from tests.helpers import seed_couple


async def test_secret_destroy_writes_audit(session):
    a, _, couple = await seed_couple(session)
    secret = await secret_service.publish(
        session, couple, a, SecretCreate(content="不想被看到")
    )

    await secret_service.destroy(session, couple, a, secret.id)

    logs = await audit_service.list_mine(session, a.id, 10, 0)
    assert any(
        log.action == "secret.destroy" and log.target_id == secret.id for log in logs
    )


async def test_audit_only_visible_to_actor(session):
    a, b, couple = await seed_couple(session)
    secret = await secret_service.publish(session, couple, a, SecretCreate(content="x"))
    await secret_service.destroy(session, couple, a, secret.id)

    assert await audit_service.list_mine(session, b.id, 10, 0) == []


async def test_consent_revoke_is_audited(session):
    _, b, couple = await seed_couple(session)

    await simta_service.set_consent(session, couple, b, False)

    logs = await audit_service.list_mine(session, b.id, 10, 0)
    assert logs[0].action == "simta.consent_revoke"
