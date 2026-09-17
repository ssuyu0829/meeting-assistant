-- 2026-09-17：補外鍵索引
--
-- 為什麼要手動跑：程式用 Base.metadata.create_all 建表，它只建「還不存在的表」，
-- 不會替既有的表補索引。所以線上 Supabase 要自己執行這段（開 SQL Editor 貼上）。
--
-- 只列真正缺的：group_members(group_id,user_id)、attendance(meeting_id,user_id)、
-- availability(meeting_id,user_id,date,hour_slot)、meeting_dates(meeting_id,date)
-- 這幾個 UNIQUE 約束已經自帶索引，前導欄位（group_id / meeting_id）的查詢用得到，不必重複建。

CREATE INDEX IF NOT EXISTS ix_group_members_user_id ON group_members (user_id);
CREATE INDEX IF NOT EXISTS ix_folders_group_id      ON folders (group_id);
CREATE INDEX IF NOT EXISTS ix_meetings_group_id     ON meetings (group_id);
CREATE INDEX IF NOT EXISTS ix_meetings_folder_id    ON meetings (folder_id);
CREATE INDEX IF NOT EXISTS ix_availability_user_id  ON availability (user_id);
CREATE INDEX IF NOT EXISTS ix_attendance_user_id    ON attendance (user_id);
