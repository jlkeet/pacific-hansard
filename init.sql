-- This table seems to be unused, the actual table is pacific_hansard_db
-- Keeping for backwards compatibility
CREATE TABLE documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    date DATE,
    speaker VARCHAR(255),
    speaker2 VARCHAR(255),
    document_type VARCHAR(255),
    content TEXT
);

-- Create indexes on pacific_hansard_db table after it's created by pipelines
-- Note: These will be created after the table is populated
