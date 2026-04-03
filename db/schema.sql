CREATE TABLE IF NOT EXISTS stories (
  id TEXT PRIMARY KEY,
  category TEXT,
  title TEXT,
  body TEXT,
  status TEXT,  -- pending_tts | pending_video | pending_split | done | failed
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parts (
  id TEXT PRIMARY KEY,
  story_id TEXT REFERENCES stories(id) ON DELETE CASCADE,
  part_number INTEGER,
  file_path TEXT,
  status TEXT,  -- queued | uploading | posted | failed
  scheduled_at TIMESTAMPTZ,
  posted_at TIMESTAMPTZ,
  tiktok_video_id TEXT,
  youtube_video_id TEXT,
  retry_count INTEGER DEFAULT 0
);
