-- Run once in the InsForge SQL editor for this application.

CREATE TABLE IF NOT EXISTS public.investigations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid NOT NULL UNIQUE,
  user_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  root_cause text,
  namespace text NOT NULL DEFAULT 'all',
  confidence integer CHECK (confidence BETWEEN 0 AND 100),
  status text NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'success', 'failed')),
  progress_step text,
  progress_state text
    CHECK (progress_state IN ('active', 'completed', 'failed')),
  error_message text
);

CREATE INDEX IF NOT EXISTS investigations_user_created_idx
  ON public.investigations (user_id, created_at DESC);

ALTER TABLE public.investigations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_read_own_investigations" ON public.investigations;
CREATE POLICY "users_read_own_investigations"
  ON public.investigations FOR SELECT TO authenticated
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS "users_create_own_investigations" ON public.investigations;
CREATE POLICY "users_create_own_investigations"
  ON public.investigations FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_update_own_investigations" ON public.investigations;
CREATE POLICY "users_update_own_investigations"
  ON public.investigations FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

INSERT INTO realtime.channels (pattern, description, enabled)
SELECT 'investigation:%', 'Per-user Kubernetes investigation progress', true
WHERE NOT EXISTS (
  SELECT 1 FROM realtime.channels WHERE pattern = 'investigation:%'
);

UPDATE realtime.channels
SET description = 'Per-user Kubernetes investigation progress', enabled = true
WHERE pattern = 'investigation:%';

ALTER TABLE realtime.channels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_subscribe_own_investigation_progress"
  ON realtime.channels;
CREATE POLICY "users_subscribe_own_investigation_progress"
  ON realtime.channels FOR SELECT TO authenticated
  USING (
    pattern = 'investigation:%'
    AND realtime.channel_name() = 'investigation:' || auth.uid()::text
  );

CREATE OR REPLACE FUNCTION public.publish_investigation_progress()
RETURNS trigger AS $$
BEGIN
  PERFORM realtime.publish(
    'investigation:' || NEW.user_id::text,
    'investigation_progress',
    jsonb_build_object(
      'requestId', NEW.request_id,
      'step', NEW.progress_step,
      'state', NEW.progress_state,
      'status', NEW.status
    )
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, realtime;

DROP TRIGGER IF EXISTS investigation_progress_realtime
  ON public.investigations;
CREATE TRIGGER investigation_progress_realtime
  AFTER INSERT OR UPDATE
  ON public.investigations
  FOR EACH ROW
  EXECUTE FUNCTION public.publish_investigation_progress();
