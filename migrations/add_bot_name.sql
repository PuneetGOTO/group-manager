-- 为discord_bot表添加bot_name字段
ALTER TABLE discord_bot ADD COLUMN IF NOT EXISTS bot_name VARCHAR(100);
