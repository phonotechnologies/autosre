-- V001: Create database and migration tracking table

CREATE DATABASE IF NOT EXISTS autosre;

CREATE TABLE IF NOT EXISTS autosre.schema_migrations
(
    version      UInt32,
    name         String,
    applied_at   DateTime DEFAULT now(),
    checksum     String DEFAULT ''
)
ENGINE = ReplacingMergeTree(applied_at)
ORDER BY (version);
