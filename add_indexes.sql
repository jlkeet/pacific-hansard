-- Add indexes to improve search performance for Pacific Hansard Database
-- Run this script in your MySQL database

USE pacific_hansard_db;

-- Index for speaker search (critical for speaker filtering)
CREATE INDEX idx_speaker ON pacific_hansard_db (speaker);
CREATE INDEX idx_speaker2 ON pacific_hansard_db (speaker2);

-- Index for date filtering and sorting
CREATE INDEX idx_date ON pacific_hansard_db (date);

-- Index for source filtering
CREATE INDEX idx_source ON pacific_hansard_db (source);

-- Composite index for common query pattern (source + date)
CREATE INDEX idx_source_date ON pacific_hansard_db (source, date);

-- Index for document type filtering
CREATE INDEX idx_document_type ON pacific_hansard_db (document_type);

-- Composite index for speaker search with source
CREATE INDEX idx_source_speaker ON pacific_hansard_db (source, speaker);

-- Full-text index for content search (if not using Solr)
-- Note: This requires MyISAM or InnoDB with FULLTEXT support
-- ALTER TABLE pacific_hansard_db ADD FULLTEXT idx_content (content);

-- Check existing indexes
SHOW INDEXES FROM pacific_hansard_db;