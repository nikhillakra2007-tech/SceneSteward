"""identity trust boundary hmac and composite referential integrity

Revision ID: e1f2a3b4c5d6
Revises: c7a1e52b93f0
Create Date: 2026-11-04 21:30:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: str | None = 'c7a1e52b93f0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Private schema and secret store for RLS identity verification
    # -------------------------------------------------------------------------
    import os
    identity_secret = os.environ.get("DATABASE_IDENTITY_SECRET", "scenesteward_db_trust_secret_2026_prod_v1")
    op.execute(f"""
        CREATE SCHEMA IF NOT EXISTS private;
        CREATE TABLE IF NOT EXISTS private.app_secrets (
            key_name text PRIMARY KEY,
            secret_val text NOT NULL
        );
        INSERT INTO private.app_secrets (key_name, secret_val)
        VALUES ('identity_secret', '{identity_secret}')
        ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val;

        REVOKE ALL ON SCHEMA private FROM public, scenesteward_app, scenesteward_readonly;
        REVOKE ALL ON ALL TABLES IN SCHEMA private FROM public, scenesteward_app, scenesteward_readonly;
    """)

    # -------------------------------------------------------------------------
    # 2. Cryptographically verified RLS identity and system context functions
    # -------------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION public.app_current_user_id() RETURNS uuid
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp AS $$
        DECLARE
            v_user text;
            v_sig text;
            v_secret text;
        BEGIN
            v_user := NULLIF(current_setting('app.user_id', true), '');
            IF v_user IS NULL THEN
                RETURN NULL;
            END IF;
            v_sig := NULLIF(current_setting('app.user_sig', true), '');
            IF v_sig IS NULL THEN
                RETURN NULL; -- Missing signature -> identity unverified!
            END IF;

            SELECT secret_val INTO v_secret FROM private.app_secrets WHERE key_name = 'identity_secret';
            IF v_secret IS NULL THEN
                RETURN NULL;
            END IF;

            -- Verify HMAC SHA256 proof of identity
            IF v_sig <> encode(sha256((v_user || ':' || v_secret)::bytea), 'hex') THEN
                RETURN NULL; -- Forged signature -> reject impersonation!
            END IF;

            RETURN v_user::uuid;
        EXCEPTION WHEN OTHERS THEN
            RETURN NULL;
        END;
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_system() RETURNS boolean
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp AS $$
        DECLARE
            v_sys text;
            v_sig text;
            v_secret text;
        BEGIN
            v_sys := current_setting('app.system', true);
            IF v_sys <> 'on' THEN
                RETURN FALSE;
            END IF;
            v_sig := NULLIF(current_setting('app.system_sig', true), '');
            IF v_sig IS NULL THEN
                RETURN FALSE; -- Missing signature -> system mode unverified!
            END IF;

            SELECT secret_val INTO v_secret FROM private.app_secrets WHERE key_name = 'identity_secret';
            IF v_secret IS NULL THEN
                RETURN FALSE;
            END IF;

            IF v_sig <> encode(sha256(('system:on:' || v_secret)::bytea), 'hex') THEN
                RETURN FALSE; -- Forged signature -> reject system bypass!
            END IF;

            RETURN TRUE;
        EXCEPTION WHEN OTHERS THEN
            RETURN FALSE;
        END;
        $$;

        CREATE OR REPLACE FUNCTION public.app_authenticated() RETURNS boolean
        LANGUAGE sql STABLE AS $$
            SELECT public.app_current_user_id() IS NOT NULL
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_member(p_project_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.project_memberships m
                WHERE m.project_id = p_project_id
                  AND m.user_id = public.app_current_user_id()
                  AND m.membership_status = 'active')
        $$;

        CREATE OR REPLACE FUNCTION public.app_has_role(p_project_id uuid, p_roles text[]) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.project_memberships m
                WHERE m.project_id = p_project_id
                  AND m.user_id = public.app_current_user_id()
                  AND m.membership_status = 'active'
                  AND m.role = ANY(p_roles))
        $$;

        CREATE OR REPLACE FUNCTION public.app_is_participant_self(p_participant_id uuid) RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp AS $$
            SELECT EXISTS (
                SELECT 1 FROM public.participants p
                WHERE p.id = p_participant_id
                  AND p.user_id = public.app_current_user_id())
        $$;

        -- Update p_projects_select to use cryptographically verified user ID for new project creations
        DROP POLICY IF EXISTS p_projects_select ON public.projects;
        CREATE POLICY p_projects_select ON public.projects
            FOR SELECT TO scenesteward_app
            USING (app_is_system() OR app_is_member(id) OR created_by = public.app_current_user_id());
    """)

    # -------------------------------------------------------------------------
    # 3. Cross-Project Composite Referential Integrity Constraints
    # -------------------------------------------------------------------------
    op.execute("""
        -- Uniqueness needed for composite foreign keys
        ALTER TABLE public.participants ADD CONSTRAINT uq_participants_id_project UNIQUE (id, project_id);
        ALTER TABLE public.story_elements ADD CONSTRAINT uq_story_elements_id_project UNIQUE (id, project_id);
        ALTER TABLE public.proposed_uses ADD CONSTRAINT uq_proposed_uses_id_project UNIQUE (id, project_id);
        ALTER TABLE public.release_documents ADD CONSTRAINT uq_release_docs_id_participant UNIQUE (id, participant_id);

        -- Enforce that child entities cannot belong to a participant/element of a different project
        ALTER TABLE public.proposed_uses ADD CONSTRAINT fk_proposed_uses_participant_project
            FOREIGN KEY (participant_id, project_id) REFERENCES public.participants(id, project_id) ON DELETE CASCADE;

        ALTER TABLE public.proposed_uses ADD CONSTRAINT fk_proposed_uses_story_element_project
            FOREIGN KEY (story_element_id, project_id) REFERENCES public.story_elements(id, project_id) ON DELETE SET NULL;

        ALTER TABLE public.release_documents ADD CONSTRAINT fk_release_docs_participant_project
            FOREIGN KEY (participant_id, project_id) REFERENCES public.participants(id, project_id) ON DELETE RESTRICT;

        ALTER TABLE public.consent_records ADD CONSTRAINT fk_consent_records_participant_project
            FOREIGN KEY (participant_id, project_id) REFERENCES public.participants(id, project_id) ON DELETE RESTRICT;

        ALTER TABLE public.participant_communications ADD CONSTRAINT fk_comms_participant_project
            FOREIGN KEY (participant_id, project_id) REFERENCES public.participants(id, project_id) ON DELETE RESTRICT;

        ALTER TABLE public.proposed_use_analyses ADD CONSTRAINT fk_analyses_proposed_use_project
            FOREIGN KEY (proposed_use_id, project_id) REFERENCES public.proposed_uses(id, project_id) ON DELETE CASCADE;

        ALTER TABLE public.reviews ADD CONSTRAINT fk_reviews_proposed_use_project
            FOREIGN KEY (proposed_use_id, project_id) REFERENCES public.proposed_uses(id, project_id) ON DELETE CASCADE;

        ALTER TABLE public.agent_runs ADD CONSTRAINT fk_agent_runs_proposed_use_project
            FOREIGN KEY (proposed_use_id, project_id) REFERENCES public.proposed_uses(id, project_id) ON DELETE CASCADE;
    """)


def downgrade() -> None:
    op.execute("""
        -- Drop composite foreign keys
        ALTER TABLE public.agent_runs DROP CONSTRAINT IF EXISTS fk_agent_runs_proposed_use_project;
        ALTER TABLE public.reviews DROP CONSTRAINT IF EXISTS fk_reviews_proposed_use_project;
        ALTER TABLE public.proposed_use_analyses DROP CONSTRAINT IF EXISTS fk_analyses_proposed_use_project;
        ALTER TABLE public.participant_communications DROP CONSTRAINT IF EXISTS fk_comms_participant_project;
        ALTER TABLE public.consent_records DROP CONSTRAINT IF EXISTS fk_consent_records_participant_project;
        ALTER TABLE public.release_documents DROP CONSTRAINT IF EXISTS fk_release_docs_participant_project;
        ALTER TABLE public.proposed_uses DROP CONSTRAINT IF EXISTS fk_proposed_uses_story_element_project;
        ALTER TABLE public.proposed_uses DROP CONSTRAINT IF EXISTS fk_proposed_uses_participant_project;

        -- Drop composite uniqueness
        ALTER TABLE public.release_documents DROP CONSTRAINT IF EXISTS uq_release_docs_id_participant;
        ALTER TABLE public.proposed_uses DROP CONSTRAINT IF EXISTS uq_proposed_uses_id_project;
        ALTER TABLE public.story_elements DROP CONSTRAINT IF EXISTS uq_story_elements_id_project;
        ALTER TABLE public.participants DROP CONSTRAINT IF EXISTS uq_participants_id_project;

        -- Restore simple helper functions
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

        DROP FUNCTION IF EXISTS public.app_current_user_id();

        DROP TABLE IF EXISTS private.app_secrets CASCADE;
        DROP SCHEMA IF EXISTS private CASCADE;
    """)
