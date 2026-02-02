-- Migration: Add auto_start column to bot_instances
-- Run: sqlite3 data/secretary.db < scripts/migrations/add_auto_start.sql

ALTER TABLE bot_instances ADD COLUMN auto_start BOOLEAN DEFAULT 0;
