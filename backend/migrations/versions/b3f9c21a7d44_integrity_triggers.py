"""integrity triggers — append-only audit trail, immutable confirmed consent"""
from alembic import op

revision = "b3f9c21a7d44"
down_revision = "65898c97090c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_events_block_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_events is append-only';
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation();

    CREATE TRIGGER trg_audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_block_mutation();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION consent_records_guard() RETURNS trigger AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'consent_records are append-only; create a new version instead';
        END IF;
        -- Once confirmed, the only permitted change is record_status -> 'superseded'
        -- (set automatically when a newer version is confirmed) and timestamps.
        IF OLD.participant_confirmation = 'confirmed' THEN
            IF NOT (
                NEW.record_status = 'superseded'
                AND NEW.participant_id = OLD.participant_id
                AND NEW.project_id = OLD.project_id
                AND NEW.version_number = OLD.version_number
                AND NEW.source_type = OLD.source_type
                AND NEW.source_document_id IS NOT DISTINCT FROM OLD.source_document_id
                AND NEW.explanation IS NOT DISTINCT FROM OLD.explanation
                AND NEW.recorded_by = OLD.recorded_by
                AND NEW.participant_confirmation = OLD.participant_confirmation
                AND NEW.confirmed_at IS NOT DISTINCT FROM OLD.confirmed_at
            ) THEN
                RAISE EXCEPTION 'confirmed consent records are immutable; create a new version';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_consent_records_guard
        BEFORE UPDATE OR DELETE ON consent_records
        FOR EACH ROW EXECUTE FUNCTION consent_records_guard();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION consent_choices_guard() RETURNS trigger AS $$
    DECLARE
        parent_confirmed boolean;
    BEGIN
        IF TG_OP = 'DELETE' THEN
            SELECT (r.participant_confirmation = 'confirmed') INTO parent_confirmed
            FROM consent_records r WHERE r.id = OLD.consent_record_id;
            IF parent_confirmed THEN
                RAISE EXCEPTION 'choices of a confirmed consent record are immutable';
            END IF;
            RETURN OLD;
        END IF;
        -- UPDATE: only confirmation bookkeeping (confirmed_by / confirmed_at) may
        -- change once the parent record is confirmed; everything else is frozen.
        SELECT (r.participant_confirmation = 'confirmed') INTO parent_confirmed
        FROM consent_records r WHERE r.id = OLD.consent_record_id;
        IF parent_confirmed THEN
            IF NOT (
                NEW.consent_record_id = OLD.consent_record_id
                AND NEW.category = OLD.category
                AND NEW.choice = OLD.choice
                AND NEW.explanation IS NOT DISTINCT FROM OLD.explanation
                AND NEW.evidence_reference IS NOT DISTINCT FROM OLD.evidence_reference
                AND NEW.source_type = OLD.source_type
                AND NEW.confidence_if_extracted IS NOT DISTINCT FROM OLD.confidence_if_extracted
            ) THEN
                RAISE EXCEPTION 'choices of a confirmed consent record are immutable; create a new version';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_consent_choices_guard
        BEFORE UPDATE OR DELETE ON consent_choices
        FOR EACH ROW EXECUTE FUNCTION consent_choices_guard();
    """)


def downgrade() -> None:
    # Dropping enforcement triggers weakens audit/consent integrity; allowed only
    # in disposable environments. Never run this against production.
    op.execute("""
    DROP TRIGGER IF EXISTS trg_consent_choices_guard ON consent_choices;
    DROP FUNCTION IF EXISTS consent_choices_guard();
    DROP TRIGGER IF EXISTS trg_consent_records_guard ON consent_records;
    DROP FUNCTION IF EXISTS consent_records_guard();
    DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events;
    DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events;
    DROP FUNCTION IF EXISTS audit_events_block_mutation();
    """)
