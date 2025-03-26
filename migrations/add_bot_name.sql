-- 为discord_bot表添加bot_name和activated_by字段
ALTER TABLE discord_bot ADD COLUMN IF NOT EXISTS bot_name VARCHAR(100);
ALTER TABLE discord_bot ADD COLUMN IF NOT EXISTS activated_by INTEGER REFERENCES user(id);
