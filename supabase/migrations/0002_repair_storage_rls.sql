-- ====================================================================
-- SUPABASE MIGRATION: 0002_repair_storage_rls.sql
-- Project: DATA CENTRIC AGENTIC AI
-- Target: Repair storage.objects RLS policies for user-documents bucket
-- ====================================================================

-- 1. Ensure bucket exists and is PRIVATE
INSERT INTO storage.buckets (id, name, public)
VALUES ('user-documents', 'user-documents', false)
ON CONFLICT (id) DO UPDATE SET public = false;

-- 2. Drop any legacy/conflicting storage policies on storage.objects
DROP POLICY IF EXISTS "Users can upload own documents to private bucket" ON storage.objects;
DROP POLICY IF EXISTS "Users can read own documents from private bucket" ON storage.objects;
DROP POLICY IF EXISTS "Users can update own documents in private bucket" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own documents from private bucket" ON storage.objects;
DROP POLICY IF EXISTS "dcai_authenticated_upload_own_files" ON storage.objects;
DROP POLICY IF EXISTS "dcai_authenticated_read_own_files" ON storage.objects;
DROP POLICY IF EXISTS "dcai_authenticated_update_own_files" ON storage.objects;
DROP POLICY IF EXISTS "dcai_authenticated_delete_own_files" ON storage.objects;

-- 3. Dedicated Owner-Specific INSERT Policy for Authenticated Users
-- Uses (SELECT auth.uid()::text) to ensure clean evaluation in Supabase auth context
CREATE POLICY "dcai_authenticated_upload_own_files"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'user-documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- 4. Dedicated Owner-Specific SELECT Policy for Authenticated Users
CREATE POLICY "dcai_authenticated_read_own_files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'user-documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- 5. Dedicated Owner-Specific UPDATE Policy for Authenticated Users
CREATE POLICY "dcai_authenticated_update_own_files"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
    bucket_id = 'user-documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
)
WITH CHECK (
    bucket_id = 'user-documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);

-- 6. Dedicated Owner-Specific DELETE Policy for Authenticated Users
CREATE POLICY "dcai_authenticated_delete_own_files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'user-documents'
    AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
);
