"""least privilege runtime role + row-level security (defense in depth)"""
from alembic import op

revision = "c7a1e52b93f0"
down_revision = "b3f9c21a7d44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. New tenant tenancy columns (backfilled) — required for RLS scoping
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE proposed_use_analyses ADD COLUMN project_id uuid;
        UPDATE proposed_use_analyses a
           SET project_id = u.project_id
          FROM proposed_uses u
         WHERE u.id = a.proposed_use_id;
        ALTER TABLE proposed_use_analyses ALTER COLUMN project_id SET NOT NULL;
        ALTER TABLE proposed_use_analyses
            ADD CONSTRAINT fk_analyses_project FOREIGN KEY (project_id)
            REFERENCES projects(id) ON DELETE CASCADE;
        CREATE INDEX ix_analyses_project ON proposed_use_analyses (project_id);
    """)
    op.execute("""
        ALTER TABLE integration_events ADD COLUMN project_id uuid;
        UPDATE integration_events
           SET project_id = NULLIF(payload_summary ->> 'mapped_project_id', '')::uuid
         WHERE payload_summary ? 'mapped_project_id';
        ALTER TABLE integration_events
            ADD CONSTRAINT fk_integration_events_project FOREIGN KEY (project_id)
            REFERENCES projects(id) ON DELETE SET NULL;
        CREATE INDEX ix_integration_project ON integration_events (project_id);
    """)

    # ------------------------------------------------------------------
    # 2. Roles (created without passwords; privileges only).
    #    Passwords are set out-of-band by the operator via scripts/db_roles.sql
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_app') THEN
                CREATE ROLE scenesteward_app NOLOGIN NOBYPASSRLS NOINHERIT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_readonly') THEN
                CREATE ROLE scenesteward_readonly NOLOGIN NOBYPASSRLS NOINHERIT;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO scenesteward_app, scenesteward_readonly', current_database());
        END $$;
        GRANT USAGE ON SCHEMA public TO scenesteward_app, scenesteward_readonly;
        REVOKE ALL ON SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenesteward_app;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO scenesteward_readonly;
        REVOKE ALL ON TABLE alembic_version FROM scenesteward_app, scenesteward_readonly;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scenesteward_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT ON TABLES TO scenesteward_readonly;
    """)

    # ------------------------------------------------------------------
    # 3. Helper functions (SECURITY DEFINER, owner bypasses RLS, used by policies)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION public.app_authenticated() RETURNS boolean
        LANGUAGE sql STABLE AS $$
            SELECT NULLIF(current_setting('app.user_id', true), '') IS NOT NULL
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_system() RETURNS boolean
        LANGUAGE sql STABLE AS $$
            SELECT current_setting('app.system', true) = 'on'
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_member(p_project_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.project_memberships m
                WHERE m.project_id = p_project_id
                  AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                  AND m.membership_status = 'active')
        $$;

        CREATE OR REPLACE FUNCTION public.app_has_role(p_project_id uuid, p_roles text[]) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.project_memberships m
                WHERE m.project_id = p_project_id
                  AND m.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                  AND m.membership_status = 'active'
                  AND m.role = ANY(p_roles))
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_participant_self(p_participant_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.participants p
                WHERE p.id = p_participant_id
                  AND p.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)
        $$;

        CREATE OR REPLACE FUNCTION public.app_participant_project(p_participant_id uuid) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT project_id FROM public.participants WHERE id = p_participant_id
        $$;

        CREATE OR REPLACE FUNCTION public.app_document_project(p_document_id uuid) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT project_id FROM public.release_documents WHERE id = p_document_id
        $$;

        CREATE OR REPLACE FUNCTION public.app_record_project(p_consent_record_id uuid) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT project_id FROM public.consent_records WHERE id = p_consent_record_id
        $$;

        CREATE OR REPLACE FUNCTION public.app_project_has_members(p_project_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
            SELECT EXISTS (SELECT 1 FROM public.project_memberships m WHERE m.project_id = p_project_id)
        $$;

        REVOKE ALL ON FUNCTION public.app_authenticated() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_is_system() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_is_member(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_has_role(uuid, text[]) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_is_participant_self(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_participant_project(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_document_project(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_record_project(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.app_project_has_members(uuid) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION public.app_authenticated() TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_is_system() TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_is_member(uuid) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_has_role(uuid, text[]) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_is_participant_self(uuid) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_participant_project(uuid) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_document_project(uuid) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_record_project(uuid) TO scenesteward_app, scenesteward_readonly;
        GRANT EXECUTE ON FUNCTION public.app_project_has_members(uuid) TO scenesteward_app, scenesteward_readonly;
    """)

    # ------------------------------------------------------------------
    # 4. Enable RLS on project-scoped tables
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
        ALTER TABLE project_memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE participant_contact_records ENABLE ROW LEVEL SECURITY;
        ALTER TABLE release_documents ENABLE ROW LEVEL SECURITY;
        ALTER TABLE release_document_pages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
        ALTER TABLE consent_choices ENABLE ROW LEVEL SECURITY;
        ALTER TABLE story_elements ENABLE ROW LEVEL SECURITY;
        ALTER TABLE proposed_uses ENABLE ROW LEVEL SECURITY;
        ALTER TABLE proposed_use_analyses ENABLE ROW LEVEL SECURITY;
        ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
        ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE participant_communications ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE integration_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE switch_room_links ENABLE ROW LEVEL SECURITY;
    """)

    # ------------------------------------------------------------------
    # 5. Policies — scenesteward_app (full role) and scenesteward_readonly (SELECT)
    # ------------------------------------------------------------------
    policies = [
        # projects
        ("p_projects_select", "projects", "SELECT", "app_is_member(id) OR created_by = NULLIF(current_setting('app.user_id', true), '')::uuid OR app_is_system()"),
        ("p_projects_insert", "projects", "INSERT", "app_authenticated() OR app_is_system()"),
        ("p_projects_update", "projects", "UPDATE", "app_has_role(id, '{project_owner,producer,director}') OR app_is_system()"),
        # memberships (project creator may insert the first row)
        ("p_memberships_select", "project_memberships", "SELECT",
         "app_is_member(project_id) OR user_id = NULLIF(current_setting('app.user_id', true), '')::uuid OR app_is_system()"),
        ("p_memberships_insert", "project_memberships", "INSERT",
         "app_has_role(project_id, '{project_owner}') OR app_is_system() OR (app_authenticated() AND NOT app_project_has_members(project_id))"),
        ("p_memberships_update", "project_memberships", "UPDATE",
         "app_has_role(project_id, '{project_owner}') OR app_is_system()"),
        # participants
        ("p_participants_select", "participants", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_participants_insert", "participants", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_participants_update", "participants", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # contact records — stricter scope
        ("p_contacts_select", "participant_contact_records", "SELECT",
         "app_has_role(app_participant_project(participant_id), '{project_owner,producer,participant_care_lead}') OR app_is_participant_self(participant_id) OR app_is_system()"),
        ("p_contacts_insert", "participant_contact_records", "INSERT",
         "app_has_role(app_participant_project(participant_id), '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_contacts_update", "participant_contact_records", "UPDATE",
         "app_has_role(app_participant_project(participant_id), '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # release documents
        ("p_docs_select", "release_documents", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_docs_insert", "release_documents", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_docs_update", "release_documents", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # extracted pages
        ("p_pages_select", "release_document_pages", "SELECT", "app_is_member(app_document_project(document_id)) OR app_is_system()"),
        ("p_pages_insert", "release_document_pages", "INSERT",
         "app_has_role(app_document_project(document_id), '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # consent
        ("p_consent_records_select", "consent_records", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_consent_records_insert", "consent_records", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_consent_records_update", "consent_records", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_consent_choices_select", "consent_choices", "SELECT",
         "app_is_member(app_record_project(consent_record_id)) OR app_is_system()"),
        ("p_consent_choices_insert", "consent_choices", "INSERT",
         "app_has_role(app_record_project(consent_record_id), '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_consent_choices_update", "consent_choices", "UPDATE",
         "app_has_role(app_record_project(consent_record_id), '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # story elements
        ("p_story_select", "story_elements", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_story_insert", "story_elements", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,director,editor}') OR app_is_system()"),
        ("p_story_update", "story_elements", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,director,editor}') OR app_is_system()"),
        # proposed uses + analyses
        ("p_uses_select", "proposed_uses", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_uses_insert", "proposed_uses", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,director,editor}') OR app_is_system()"),
        ("p_uses_update", "proposed_uses", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,director,editor}') OR app_is_system()"),
        ("p_analyses_select", "proposed_use_analyses", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_analyses_insert", "proposed_use_analyses", "INSERT", "app_is_system()"),
        # reviews
        ("p_reviews_select", "reviews", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_reviews_insert", "reviews", "INSERT", "app_is_system()"),
        ("p_reviews_update", "reviews", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # agent runs
        ("p_agent_runs_select", "agent_runs", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_agent_runs_insert", "agent_runs", "INSERT", "app_is_system()"),
        ("p_agent_runs_update", "agent_runs", "UPDATE", "app_is_system()"),
        # communications — restricted
        ("p_comms_select", "participant_communications", "SELECT",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_comms_insert", "participant_communications", "INSERT",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        ("p_comms_update", "participant_communications", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer,participant_care_lead}') OR app_is_system()"),
        # audit trail — insert for authenticated/system, no updates/deletes at all
        ("p_audit_select", "audit_events", "SELECT",
         "(project_id IS NOT NULL AND app_is_member(project_id)) OR (actor_type = 'user' AND actor_id = NULLIF(current_setting('app.user_id', true), '')) OR app_is_system()"),
        ("p_audit_insert", "audit_events", "INSERT", "app_authenticated() OR app_is_system()"),
        # integration events — restricted, project-scoped rows only visible to owner/producer
        ("p_integration_select", "integration_events", "SELECT",
         "(project_id IS NOT NULL AND app_has_role(project_id, '{project_owner,producer}')) OR app_is_system()"),
        ("p_integration_insert", "integration_events", "INSERT", "app_is_system()"),
        ("p_integration_update", "integration_events", "UPDATE", "app_is_system()"),
        # tasks
        ("p_tasks_select", "tasks", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_tasks_insert", "tasks", "INSERT", "app_is_member(project_id) OR app_is_system()"),
        ("p_tasks_update", "tasks", "UPDATE", "app_is_member(project_id) OR app_is_system()"),
        # switch room links
        ("p_switch_select", "switch_room_links", "SELECT", "app_is_member(project_id) OR app_is_system()"),
        ("p_switch_insert", "switch_room_links", "INSERT",
         "app_has_role(project_id, '{project_owner,producer}') OR app_is_system()"),
        ("p_switch_update", "switch_room_links", "UPDATE",
         "app_has_role(project_id, '{project_owner,producer}') OR app_is_system()"),
    ]
    for name, table, cmd, expr in policies:
        if cmd == "SELECT":
            op.execute(f"CREATE POLICY {name} ON {table} FOR SELECT TO scenesteward_app USING ({expr})")
            op.execute(f"CREATE POLICY {name}_ro ON {table} FOR SELECT TO scenesteward_readonly USING ({expr})")
        elif cmd == "INSERT":
            op.execute(f"CREATE POLICY {name} ON {table} FOR INSERT TO scenesteward_app WITH CHECK ({expr})")
        else:  # UPDATE: restrict visible rows AND the result of the write
            op.execute(f"CREATE POLICY {name} ON {table} FOR {cmd} TO scenesteward_app USING ({expr}) WITH CHECK ({expr})")


def downgrade() -> None:
    import sqlalchemy as sa
    # Disabling RLS is a controlled action: memberships are still enforced by
    # the application layer. Never run this on a live database.
    tables = [
        "projects", "project_memberships", "participants", "participant_contact_records",
        "release_documents", "release_document_pages", "consent_records", "consent_choices",
        "story_elements", "proposed_uses", "proposed_use_analyses", "reviews", "agent_runs",
        "participant_communications", "audit_events", "integration_events", "tasks",
        "switch_room_links",
    ]
    for table in tables:
        for policy in op.get_bind().execute(
            # policy names come from the catalog, never from user input
            sa.text(f"SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename='{table}'")
        ).fetchall():
            op.execute(f'DROP POLICY IF EXISTS "{policy[0]}" ON {table}')
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("""
        DROP FUNCTION IF EXISTS public.app_authenticated();
        DROP FUNCTION IF EXISTS public.app_is_system();
        DROP FUNCTION IF EXISTS public.app_is_member(uuid);
        DROP FUNCTION IF EXISTS public.app_has_role(uuid, text[]);
        DROP FUNCTION IF EXISTS public.app_is_participant_self(uuid);
        DROP FUNCTION IF EXISTS public.app_participant_project(uuid);
        DROP FUNCTION IF EXISTS public.app_document_project(uuid);
        DROP FUNCTION IF EXISTS public.app_record_project(uuid);
        DROP FUNCTION IF EXISTS public.app_project_has_members(uuid);
    """)
    # Columns are intentionally kept (may contain data); drop only constraints that break downgrades.
    op.execute("""
        ALTER TABLE integration_events DROP CONSTRAINT IF EXISTS fk_integration_events_project;
        ALTER TABLE integration_events DROP COLUMN IF EXISTS project_id;
        ALTER TABLE proposed_use_analyses DROP CONSTRAINT IF EXISTS fk_analyses_project;
        ALTER TABLE proposed_use_analyses DROP COLUMN IF EXISTS project_id;
    """)
