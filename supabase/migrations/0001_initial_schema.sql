-- ====================================================================
-- SUPABASE MIGRATION: 0001_initial_schema.sql
-- Project: DATA CENTRIC AGENTIC AI (Multi-User Cloud Migration)
-- Dimension: 384 (all-MiniLM-L6-v2 / local deterministic vector fallback)
-- ====================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. User Profiles Table (Mirrors auth.users)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,
    storage_used_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to automatically create a profile entry when a user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, display_name)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)))
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 3. Documents Table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    sha256_hash TEXT NOT NULL,
    current_version_number INT NOT NULL DEFAULT 1,
    current_version_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Document Versions Table
CREATE TABLE IF NOT EXISTS public.document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    storage_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    operation_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_document_version UNIQUE(document_id, version_number)
);

-- Foreign key update on documents.current_version_id
ALTER TABLE public.documents
    DROP CONSTRAINT IF EXISTS fk_documents_current_version;
ALTER TABLE public.documents
    ADD CONSTRAINT fk_documents_current_version
    FOREIGN KEY (current_version_id) REFERENCES public.document_versions(id) ON DELETE SET NULL;

-- 5. Modification Requests History Table
CREATE TABLE IF NOT EXISTS public.modification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    request_ciphertext TEXT NOT NULL,
    interpretation_ciphertext TEXT,
    planned_operation TEXT,
    execution_status TEXT NOT NULL,
    validation_status TEXT,
    summary_result TEXT,
    previous_version_number INT,
    new_version_number INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Document Chunks (pgvector Persistent RAG Table)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    version_number INT NOT NULL DEFAULT 1,
    chunk_index INT NOT NULL,
    chunk_ciphertext TEXT NOT NULL,
    source_metadata_ciphertext TEXT,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. High-Performance Indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_doc_versions_user_doc ON public.document_versions(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_mod_requests_user_doc ON public.modification_requests(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_user_doc ON public.document_chunks(user_id, document_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON public.document_chunks USING hnsw (embedding vector_cosine_ops);

-- ====================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Strict Isolation: auth.uid() = user_id on EVERY table
-- ====================================================================

-- Enable RLS on all tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.modification_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

-- User Profiles Policies
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- Documents Policies
CREATE POLICY "Users can select own documents"
    ON public.documents FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents"
    ON public.documents FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents"
    ON public.documents FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents"
    ON public.documents FOR DELETE
    USING (auth.uid() = user_id);

-- Document Versions Policies
CREATE POLICY "Users can select own document versions"
    ON public.document_versions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own document versions"
    ON public.document_versions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own document versions"
    ON public.document_versions FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own document versions"
    ON public.document_versions FOR DELETE
    USING (auth.uid() = user_id);

-- Modification Requests Policies
CREATE POLICY "Users can select own modification requests"
    ON public.modification_requests FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own modification requests"
    ON public.modification_requests FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Document Chunks Policies
CREATE POLICY "Users can select own document chunks"
    ON public.document_chunks FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own document chunks"
    ON public.document_chunks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own document chunks"
    ON public.document_chunks FOR DELETE
    USING (auth.uid() = user_id);

-- ====================================================================
-- RLS-COMPLIANT SECURE VECTOR SEARCH RPC FUNCTION
-- Matches chunks strictly belonging to auth.uid()
-- ====================================================================
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_threshold float,
    match_count int,
    filter_doc_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    version_number int,
    chunk_index int,
    chunk_ciphertext text,
    source_metadata_ciphertext text,
    similarity float
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.version_number,
        dc.chunk_index,
        dc.chunk_ciphertext,
        dc.source_metadata_ciphertext,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks dc
    WHERE dc.user_id = auth.uid()
      AND (filter_doc_id IS NULL OR dc.document_id = filter_doc_id)
      AND (1 - (dc.embedding <=> query_embedding)) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ====================================================================
-- STORAGE BUCKET CREATION & STORAGE RLS POLICIES
-- Private Bucket: user-documents
-- ====================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('user-documents', 'user-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Storage Policy: Users can only upload into their own folder (user_id/...)
CREATE POLICY "Users can upload own documents to private bucket"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'user-documents' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage Policy: Users can only read/download from their own folder
CREATE POLICY "Users can read own documents from private bucket"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'user-documents' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage Policy: Users can update/replace files in their own folder
CREATE POLICY "Users can update own documents in private bucket"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'user-documents' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage Policy: Users can delete files in their own folder
CREATE POLICY "Users can delete own documents from private bucket"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'user-documents' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

