-- Migration: Add project_path column to threads table
-- Description: Add Git repository root path to thread for Workspace integration

ALTER TABLE threads ADD COLUMN project_path TEXT;
