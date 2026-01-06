


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE TYPE "public"."hardness_level_enum" AS ENUM (
    'easy',
    'medium',
    'hard'
);


ALTER TYPE "public"."hardness_level_enum" OWNER TO "postgres";


CREATE TYPE "public"."product_type_enum" AS ENUM (
    'qgen',
    'ai_tutor'
);


ALTER TYPE "public"."product_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."question_type_enum" AS ENUM (
    'mcq4',
    'msq4',
    'short_answer',
    'true_or_false',
    'fill_in_the_blanks',
    'long_answer'
);


ALTER TYPE "public"."question_type_enum" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."block_email_if_google_exists"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
declare
  already_has_google boolean;
begin
  -- Only check for email/password signups
  if new.raw_app_meta_data->>'provider' = 'email' then

    select exists (
      select 1
      from auth.users u
      where u.email = new.email
        and u.raw_app_meta_data->'providers' ? 'google'
    )
    into already_has_google;

    if already_has_google then
      -- Reject the email signup if the email is already used by Google
      raise exception
        'EMAIL_ALREADY_USED_WITH_GOOGLE'
        using
          errcode = 'P0001',
          hint = 'USE_GOOGLE_LOGIN';
    end if;
  end if;

  return new;
end;
$$;


ALTER FUNCTION "public"."block_email_if_google_exists"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."block_email_signup_if_google_exists"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
declare
  google_exists boolean;
begin
  -- only block EMAIL signups
  if new.app_metadata->>'provider' = 'email' then

    select exists (
      select 1
      from auth.users u
      where u.email = new.email
        and u.app_metadata->'providers' ? 'google'
    )
    into google_exists;

    if google_exists then
      raise exception
        'EMAIL_ALREADY_USED_WITH_GOOGLE'
        using
          errcode = 'P0001',
          hint = 'USE_GOOGLE_LOGIN';
    end if;

  end if;

  return new;
end;
$$;


ALTER FUNCTION "public"."block_email_signup_if_google_exists"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_default_qgen_section_on_draft_create"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
begin
  insert into public.qgen_draft_sections (
    qgen_draft_id,
    position_in_draft,
    section_name
  )
  values (
    new.id,
    0,
    'Section A'
  )
  on conflict do nothing;

  return new;
end;
$$;


ALTER FUNCTION "public"."create_default_qgen_section_on_draft_create"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_qgen_draft_on_activity"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
declare
  v_org record;
  v_user record;

  v_institute_name text;
  v_logo_url text;
begin
  -- Only for qgen activities
  if new.product_type <> 'qgen' then
    return new;
  end if;

  -- Fetch user
  select *
  into v_user
  from public.users
  where id = new.user_id;

  -- Fetch org if exists
  if v_user.org_id is not null then
    select *
    into v_org
    from public.orgs
    where id = v_user.org_id;
  end if;

  /*
    Institute name priority:
    1. org.header_line
    2. user_entered_school_name
    3. dummy fallback
  */
  v_institute_name :=
    coalesce(
      v_org.header_line,
      v_user.user_entered_school_name,
      'Example Institute'
    );

  /*
    Logo priority:
    1. org.logo_url
    2. user avatar (optional, if you want)
    3. null (frontend can show placeholder)
  */
  v_logo_url :=
    coalesce(
      v_org.logo_url,
      v_user.avatar_url,
      null
    );

  -- Create qgen draft
  insert into public.qgen_drafts (
    activity_id,
    institute_name,
    logo_url,
    paper_title
  )
  values (
    new.id,
    v_institute_name,
    v_logo_url,
    new.name
  )
  on conflict (activity_id) do nothing;

  return new;
end;
$$;


ALTER FUNCTION "public"."create_qgen_draft_on_activity"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_auth_user_created"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO public.users (
    id,
    email,
    phone_num,
    user_type,
    name,
    avatar_url
  )
  VALUES (
    NEW.id,
    NEW.email,
    NEW.phone,
    'private_user',
    NEW.raw_user_meta_data ->> 'name',
    NEW.raw_user_meta_data ->> 'avatar_url'
  )
  ON CONFLICT (id) DO NOTHING;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_auth_user_created"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."sync_last_active"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
begin
  update public.users
  set last_active_at = new.last_sign_in_at
  where id = new.id;

  return new;
end;
$$;


ALTER FUNCTION "public"."sync_last_active"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."activities" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "product_type" "public"."product_type_enum" NOT NULL
);


ALTER TABLE "public"."activities" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."bank_questions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "subject_id" "uuid" NOT NULL,
    "reference" "text",
    "question_text" "text" NOT NULL,
    "answer_text" "text" NOT NULL,
    "figure" "text",
    "marks" smallint,
    "explanation" "text",
    "option1" "text",
    "option2" "text",
    "option3" "text",
    "option4" "text",
    "correct_mcq_option" smallint,
    "msq_option1_answer" boolean,
    "msq_option2_answer" boolean,
    "msq_option3_answer" boolean,
    "msq_option4_answer" boolean,
    "question_type" "public"."question_type_enum" NOT NULL,
    "hardness_level" "public"."hardness_level_enum"
);


ALTER TABLE "public"."bank_questions" OWNER TO "postgres";


COMMENT ON TABLE "public"."bank_questions" IS 'The question Bank (includes the solved example, pyqs, etc.)';



CREATE TABLE IF NOT EXISTS "public"."bank_questions_concepts_maps" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "concept_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "bank_question_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL
);


ALTER TABLE "public"."bank_questions_concepts_maps" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."boards" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."boards" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chapters" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "subject_id" "uuid" NOT NULL,
    "position" integer,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "chapters_position_check" CHECK (("position" >= 0))
);


ALTER TABLE "public"."chapters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."classes" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "board_id" "uuid" NOT NULL,
    "position" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "classes_position_check" CHECK (("position" >= 0))
);


ALTER TABLE "public"."classes" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."concepts" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "topic_id" "uuid" NOT NULL,
    "page_number" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "concepts_page_num_check" CHECK (("page_number" > 0))
);


ALTER TABLE "public"."concepts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."gen_artifacts" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "source_url" "text" NOT NULL,
    "activity_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."gen_artifacts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."gen_questions" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "activity_id" "uuid" NOT NULL,
    "is_in_draft" boolean DEFAULT false NOT NULL,
    "marks" smallint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "answer_text" "text",
    "question_text" "text",
    "explanation" "text",
    "option1" "text",
    "option2" "text",
    "option3" "text",
    "option4" "text",
    "correct_mcq_option" smallint,
    "msq_option1_answer" boolean,
    "msq_option2_answer" boolean,
    "msq_option3_answer" boolean,
    "msq_option4_answer" boolean,
    "qgen_draft_section_id" "uuid",
    "position_in_section" smallint,
    "is_page_break_below" boolean DEFAULT false NOT NULL,
    "question_type" "public"."question_type_enum" NOT NULL,
    "hardness_level" "public"."hardness_level_enum" NOT NULL,
    CONSTRAINT "gen_questions_correct_mcq_option_check" CHECK (("correct_mcq_option" = ANY (ARRAY[1, 2, 3, 4]))),
    CONSTRAINT "gen_questions_marks_check" CHECK (("marks" >= 0)),
    CONSTRAINT "gen_questions_position_in_section_check" CHECK (("position_in_section" >= 0))
);


ALTER TABLE "public"."gen_questions" OWNER TO "postgres";


COMMENT ON COLUMN "public"."gen_questions"."answer_text" IS 'Answer for the Generated question. Not For MCQs and MSQs';



COMMENT ON COLUMN "public"."gen_questions"."question_text" IS 'Actual Question';



COMMENT ON COLUMN "public"."gen_questions"."explanation" IS 'explanation for the question and answer';



COMMENT ON COLUMN "public"."gen_questions"."option1" IS 'For MCQ or MSQs';



COMMENT ON COLUMN "public"."gen_questions"."option2" IS 'For MCQs or MSQs';



COMMENT ON COLUMN "public"."gen_questions"."option3" IS 'For MCQs or MSQs';



COMMENT ON COLUMN "public"."gen_questions"."option4" IS 'For MCQs or MSQs';



COMMENT ON COLUMN "public"."gen_questions"."correct_mcq_option" IS 'can be 1 or 2 or 3 or 4';



COMMENT ON COLUMN "public"."gen_questions"."msq_option1_answer" IS 'Describes if the option is correct or incorrect';



COMMENT ON COLUMN "public"."gen_questions"."msq_option2_answer" IS 'Describes if the option is correct or incorrect';



COMMENT ON COLUMN "public"."gen_questions"."msq_option3_answer" IS 'Describes if the option is correct or incorrect';



COMMENT ON COLUMN "public"."gen_questions"."msq_option4_answer" IS 'Describes if the option is correct or incorrect';



COMMENT ON COLUMN "public"."gen_questions"."qgen_draft_section_id" IS 'The id of the section to which this question belongs to if, this is in draft';



COMMENT ON COLUMN "public"."gen_questions"."position_in_section" IS 'Position of the question in the section in the draft, if this question belongs to a draft';



COMMENT ON COLUMN "public"."gen_questions"."is_page_break_below" IS 'If the question is in a draft, then this variable will tell if to add a page break after this question in the pdf being generated';



CREATE TABLE IF NOT EXISTS "public"."gen_questions_concepts_maps" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "gen_question_id" "uuid" NOT NULL,
    "concept_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."gen_questions_concepts_maps" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."orgs" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "email" "text" NOT NULL,
    "logo_url" "text",
    "org_type" "text",
    "phone_num" "text" NOT NULL,
    "address" "text",
    "header_line" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "board" "uuid",
    CONSTRAINT "orgs_org_type_check" CHECK (("org_type" = ANY (ARRAY['institution'::"text", 'school'::"text", 'tuition'::"text"])))
);


ALTER TABLE "public"."orgs" OWNER TO "postgres";


COMMENT ON COLUMN "public"."orgs"."board" IS 'To which board the organisation belongs to';



CREATE TABLE IF NOT EXISTS "public"."qgen_draft_instructions_users_maps" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "instruction_text" "text",
    "user_id" "uuid" DEFAULT "gen_random_uuid"()
);


ALTER TABLE "public"."qgen_draft_instructions_users_maps" OWNER TO "postgres";


COMMENT ON TABLE "public"."qgen_draft_instructions_users_maps" IS 'Stores instructions for paper as a relation with teacher / user/';



CREATE TABLE IF NOT EXISTS "public"."qgen_draft_sections" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "qgen_draft_id" "uuid" DEFAULT "gen_random_uuid"(),
    "section_name" "text",
    "position_in_draft" smallint DEFAULT '1'::smallint NOT NULL,
    CONSTRAINT "qgen_draft_sections_position_in_draft_check" CHECK (("position_in_draft" >= 0))
);


ALTER TABLE "public"."qgen_draft_sections" OWNER TO "postgres";


COMMENT ON TABLE "public"."qgen_draft_sections" IS 'Sections in the draft  of the paper to be generated';



COMMENT ON COLUMN "public"."qgen_draft_sections"."position_in_draft" IS 'The position of the section in the draft of the paper to be generated as PDF';



CREATE TABLE IF NOT EXISTS "public"."qgen_drafts" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "activity_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "paper_datetime" timestamp without time zone,
    "paper_duration" time without time zone,
    "maximum_marks" smallint,
    "institute_name" "text",
    "paper_title" "text",
    "paper_subtitle" "text",
    "logo_url" "text"
);


ALTER TABLE "public"."qgen_drafts" OWNER TO "postgres";


COMMENT ON COLUMN "public"."qgen_drafts"."paper_datetime" IS 'The Date and time of examination to be shown on the generated PDF';



COMMENT ON COLUMN "public"."qgen_drafts"."paper_duration" IS 'Duration of the paper to be shown on the generated PDF';



COMMENT ON COLUMN "public"."qgen_drafts"."maximum_marks" IS 'Maximum / Total Marks to be shown on the generated paper PDF';



COMMENT ON COLUMN "public"."qgen_drafts"."institute_name" IS 'Institute / School Name to be shown on the top of the generated pdf of the paper';



COMMENT ON COLUMN "public"."qgen_drafts"."paper_title" IS 'Title of the Paper to be shown in the generated PDF';



COMMENT ON COLUMN "public"."qgen_drafts"."paper_subtitle" IS 'Subtitle of the paper to be shown in the generated pdf';



COMMENT ON COLUMN "public"."qgen_drafts"."logo_url" IS 'URL of the logo to be shown on the generated question paper pdf';



CREATE TABLE IF NOT EXISTS "public"."subjects" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "class_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."subjects" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."topics" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "chapter_id" "uuid" NOT NULL,
    "position" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "topics_position_check" CHECK (("position" >= 0))
);


ALTER TABLE "public"."topics" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" NOT NULL,
    "user_type" "text" NOT NULL,
    "email" "text",
    "phone_num" "text",
    "credits" integer DEFAULT 100 NOT NULL,
    "avatar_url" "text",
    "org_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "name" "text",
    "account_status" "text" DEFAULT 'active'::"text" NOT NULL,
    "last_active_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "user_entered_school_name" "text",
    "user_entered_school-address" "text",
    "user_entered_school_board" "text",
    CONSTRAINT "users_account_status_check" CHECK (("account_status" = ANY (ARRAY['active'::"text", 'inactive'::"text", 'disabled'::"text"]))),
    CONSTRAINT "users_check" CHECK ((("email" IS NOT NULL) OR ("phone_num" IS NOT NULL))),
    CONSTRAINT "users_name_check" CHECK (("length"("name") <= 50)),
    CONSTRAINT "users_user_type_check" CHECK (("user_type" = ANY (ARRAY['admin'::"text", 'teacher'::"text", 'student'::"text", 'principal'::"text", 'private_user'::"text"])))
);


ALTER TABLE "public"."users" OWNER TO "postgres";


COMMENT ON COLUMN "public"."users"."name" IS 'The Full Name of The User';



COMMENT ON COLUMN "public"."users"."account_status" IS 'Is account active or disabled or inactive or deactivated etc.';



COMMENT ON COLUMN "public"."users"."last_active_at" IS 'To track user Churn';



COMMENT ON COLUMN "public"."users"."user_entered_school_name" IS 'The School Name which the User have Entered, for direct login users, not associated with organisation initially';



COMMENT ON COLUMN "public"."users"."user_entered_school-address" IS 'The School Address which user manually enters, for thus who are not associated with any organisation';



COMMENT ON COLUMN "public"."users"."user_entered_school_board" IS 'The Board which user enters manually, for thus users who are not part of any organisation, and doing a signup via website directly.';



ALTER TABLE ONLY "public"."activities"
    ADD CONSTRAINT "activities_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bank_questions_concepts_maps"
    ADD CONSTRAINT "bank_questions_concepts_maps_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bank_questions"
    ADD CONSTRAINT "bank_questions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."boards"
    ADD CONSTRAINT "boards_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."boards"
    ADD CONSTRAINT "boards_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_subject_id_name_key" UNIQUE ("subject_id", "name");



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_subject_id_position_key" UNIQUE ("subject_id", "position");



ALTER TABLE ONLY "public"."classes"
    ADD CONSTRAINT "classes_board_id_name_key" UNIQUE ("board_id", "name");



ALTER TABLE ONLY "public"."classes"
    ADD CONSTRAINT "classes_board_id_position_key" UNIQUE ("board_id", "position");



ALTER TABLE ONLY "public"."classes"
    ADD CONSTRAINT "classes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."concepts"
    ADD CONSTRAINT "concepts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."concepts"
    ADD CONSTRAINT "concepts_topic_id_name_key" UNIQUE ("topic_id", "name");



ALTER TABLE ONLY "public"."gen_artifacts"
    ADD CONSTRAINT "gen_artifacts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."gen_questions_concepts_maps"
    ADD CONSTRAINT "gen_questions_concepts_maps_gen_question_id_concept_id_key" UNIQUE ("gen_question_id", "concept_id");



ALTER TABLE ONLY "public"."gen_questions_concepts_maps"
    ADD CONSTRAINT "gen_questions_concepts_maps_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."gen_questions"
    ADD CONSTRAINT "gen_questions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orgs"
    ADD CONSTRAINT "orgs_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."orgs"
    ADD CONSTRAINT "orgs_phone_num_key" UNIQUE ("phone_num");



ALTER TABLE ONLY "public"."orgs"
    ADD CONSTRAINT "orgs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."qgen_draft_instructions_users_maps"
    ADD CONSTRAINT "qgen_draft_instructions_maps_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."qgen_draft_sections"
    ADD CONSTRAINT "qgen_draft_sections_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."qgen_draft_sections"
    ADD CONSTRAINT "qgen_draft_sections_position_in_draft_key" UNIQUE ("position_in_draft");



ALTER TABLE ONLY "public"."qgen_drafts"
    ADD CONSTRAINT "qgen_drafts_activity_id_key" UNIQUE ("activity_id");



ALTER TABLE ONLY "public"."qgen_drafts"
    ADD CONSTRAINT "qgen_drafts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subjects"
    ADD CONSTRAINT "subjects_class_id_name_key" UNIQUE ("class_id", "name");



ALTER TABLE ONLY "public"."subjects"
    ADD CONSTRAINT "subjects_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."topics"
    ADD CONSTRAINT "topics_chapter_id_name_key" UNIQUE ("chapter_id", "name");



ALTER TABLE ONLY "public"."topics"
    ADD CONSTRAINT "topics_chapter_id_position_key" UNIQUE ("chapter_id", "position");



ALTER TABLE ONLY "public"."topics"
    ADD CONSTRAINT "topics_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_phone_num_key" UNIQUE ("phone_num");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_activities_user_id" ON "public"."activities" USING "btree" ("user_id");



CREATE INDEX "idx_chapters_subject_id" ON "public"."chapters" USING "btree" ("subject_id");



CREATE INDEX "idx_classes_board_id" ON "public"."classes" USING "btree" ("board_id");



CREATE INDEX "idx_concepts_topic_id" ON "public"."concepts" USING "btree" ("topic_id");



CREATE INDEX "idx_gen_artifacts_activity_id" ON "public"."gen_artifacts" USING "btree" ("activity_id");



CREATE INDEX "idx_gen_questions_activity_draft" ON "public"."gen_questions" USING "btree" ("activity_id", "is_in_draft");



CREATE INDEX "idx_gen_questions_concepts_maps_concept_id" ON "public"."gen_questions_concepts_maps" USING "btree" ("concept_id");



CREATE INDEX "idx_gen_questions_concepts_maps_gen_question_id" ON "public"."gen_questions_concepts_maps" USING "btree" ("gen_question_id");



CREATE INDEX "idx_qgen_drafts_activity_id" ON "public"."qgen_drafts" USING "btree" ("activity_id");



CREATE INDEX "idx_subjects_class_id" ON "public"."subjects" USING "btree" ("class_id");



CREATE INDEX "idx_topics_chapter_id" ON "public"."topics" USING "btree" ("chapter_id");



CREATE INDEX "idx_users_org_id" ON "public"."users" USING "btree" ("org_id");



CREATE UNIQUE INDEX "users_email_lower_idx" ON "public"."users" USING "btree" ("lower"("email")) WHERE ("email" IS NOT NULL);



CREATE OR REPLACE TRIGGER "trg_create_default_qgen_section" AFTER INSERT ON "public"."qgen_drafts" FOR EACH ROW EXECUTE FUNCTION "public"."create_default_qgen_section_on_draft_create"();



CREATE OR REPLACE TRIGGER "trg_create_qgen_draft" AFTER INSERT ON "public"."activities" FOR EACH ROW EXECUTE FUNCTION "public"."create_qgen_draft_on_activity"();



ALTER TABLE ONLY "public"."activities"
    ADD CONSTRAINT "activities_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bank_questions_concepts_maps"
    ADD CONSTRAINT "bank_questions_concepts_maps_bank_question_id_fkey" FOREIGN KEY ("bank_question_id") REFERENCES "public"."bank_questions"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bank_questions_concepts_maps"
    ADD CONSTRAINT "bank_questions_concepts_maps_concept_id_fkey" FOREIGN KEY ("concept_id") REFERENCES "public"."concepts"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bank_questions"
    ADD CONSTRAINT "bank_questions_subject_id_fkey" FOREIGN KEY ("subject_id") REFERENCES "public"."subjects"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_subject_id_fkey" FOREIGN KEY ("subject_id") REFERENCES "public"."subjects"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."classes"
    ADD CONSTRAINT "classes_board_id_fkey" FOREIGN KEY ("board_id") REFERENCES "public"."boards"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."concepts"
    ADD CONSTRAINT "concepts_topic_id_fkey" FOREIGN KEY ("topic_id") REFERENCES "public"."topics"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gen_artifacts"
    ADD CONSTRAINT "gen_artifacts_activity_id_fkey" FOREIGN KEY ("activity_id") REFERENCES "public"."activities"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gen_questions"
    ADD CONSTRAINT "gen_questions_activity_id_fkey" FOREIGN KEY ("activity_id") REFERENCES "public"."activities"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gen_questions_concepts_maps"
    ADD CONSTRAINT "gen_questions_concepts_maps_concept_id_fkey" FOREIGN KEY ("concept_id") REFERENCES "public"."concepts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gen_questions_concepts_maps"
    ADD CONSTRAINT "gen_questions_concepts_maps_gen_question_id_fkey" FOREIGN KEY ("gen_question_id") REFERENCES "public"."gen_questions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."gen_questions"
    ADD CONSTRAINT "gen_questions_qgen_draft_section_id_fkey" FOREIGN KEY ("qgen_draft_section_id") REFERENCES "public"."qgen_draft_sections"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."orgs"
    ADD CONSTRAINT "orgs_board_fkey" FOREIGN KEY ("board") REFERENCES "public"."boards"("id");



ALTER TABLE ONLY "public"."qgen_draft_instructions_users_maps"
    ADD CONSTRAINT "qgen_draft_instructions_maps_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."qgen_draft_sections"
    ADD CONSTRAINT "qgen_draft_sections_qgen_draft_id_fkey" FOREIGN KEY ("qgen_draft_id") REFERENCES "public"."qgen_drafts"("id") ON UPDATE CASCADE ON DELETE CASCADE;



ALTER TABLE ONLY "public"."qgen_drafts"
    ADD CONSTRAINT "qgen_drafts_activity_id_fkey" FOREIGN KEY ("activity_id") REFERENCES "public"."activities"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."subjects"
    ADD CONSTRAINT "subjects_class_id_fkey" FOREIGN KEY ("class_id") REFERENCES "public"."classes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."topics"
    ADD CONSTRAINT "topics_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "public"."orgs"("id") ON DELETE SET NULL;



CREATE POLICY "activities_owner_all" ON "public"."activities" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "gen_questions_owner_all" ON "public"."gen_questions" USING ((EXISTS ( SELECT 1
   FROM "public"."activities" "a"
  WHERE (("a"."id" = "gen_questions"."activity_id") AND ("a"."user_id" = "auth"."uid"()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."activities" "a"
  WHERE (("a"."id" = "gen_questions"."activity_id") AND ("a"."user_id" = "auth"."uid"())))));



CREATE POLICY "qgen_drafts_owner_all" ON "public"."qgen_drafts" USING ((EXISTS ( SELECT 1
   FROM "public"."activities" "a"
  WHERE (("a"."id" = "qgen_drafts"."activity_id") AND ("a"."user_id" = "auth"."uid"()))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."activities" "a"
  WHERE (("a"."id" = "qgen_drafts"."activity_id") AND ("a"."user_id" = "auth"."uid"())))));



CREATE POLICY "users_self_read" ON "public"."users" FOR SELECT USING (("id" = "auth"."uid"()));



CREATE POLICY "users_self_update" ON "public"."users" FOR UPDATE USING (("id" = "auth"."uid"()));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";






ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."gen_questions";



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."block_email_if_google_exists"() TO "anon";
GRANT ALL ON FUNCTION "public"."block_email_if_google_exists"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."block_email_if_google_exists"() TO "service_role";



GRANT ALL ON FUNCTION "public"."block_email_signup_if_google_exists"() TO "anon";
GRANT ALL ON FUNCTION "public"."block_email_signup_if_google_exists"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."block_email_signup_if_google_exists"() TO "service_role";



GRANT ALL ON FUNCTION "public"."create_default_qgen_section_on_draft_create"() TO "anon";
GRANT ALL ON FUNCTION "public"."create_default_qgen_section_on_draft_create"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_default_qgen_section_on_draft_create"() TO "service_role";



GRANT ALL ON FUNCTION "public"."create_qgen_draft_on_activity"() TO "anon";
GRANT ALL ON FUNCTION "public"."create_qgen_draft_on_activity"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_qgen_draft_on_activity"() TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_auth_user_created"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_auth_user_created"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_auth_user_created"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sync_last_active"() TO "anon";
GRANT ALL ON FUNCTION "public"."sync_last_active"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."sync_last_active"() TO "service_role";


















GRANT ALL ON TABLE "public"."activities" TO "anon";
GRANT ALL ON TABLE "public"."activities" TO "authenticated";
GRANT ALL ON TABLE "public"."activities" TO "service_role";



GRANT ALL ON TABLE "public"."bank_questions" TO "anon";
GRANT ALL ON TABLE "public"."bank_questions" TO "authenticated";
GRANT ALL ON TABLE "public"."bank_questions" TO "service_role";



GRANT ALL ON TABLE "public"."bank_questions_concepts_maps" TO "anon";
GRANT ALL ON TABLE "public"."bank_questions_concepts_maps" TO "authenticated";
GRANT ALL ON TABLE "public"."bank_questions_concepts_maps" TO "service_role";



GRANT ALL ON TABLE "public"."boards" TO "anon";
GRANT ALL ON TABLE "public"."boards" TO "authenticated";
GRANT ALL ON TABLE "public"."boards" TO "service_role";



GRANT ALL ON TABLE "public"."chapters" TO "anon";
GRANT ALL ON TABLE "public"."chapters" TO "authenticated";
GRANT ALL ON TABLE "public"."chapters" TO "service_role";



GRANT ALL ON TABLE "public"."classes" TO "anon";
GRANT ALL ON TABLE "public"."classes" TO "authenticated";
GRANT ALL ON TABLE "public"."classes" TO "service_role";



GRANT ALL ON TABLE "public"."concepts" TO "anon";
GRANT ALL ON TABLE "public"."concepts" TO "authenticated";
GRANT ALL ON TABLE "public"."concepts" TO "service_role";



GRANT ALL ON TABLE "public"."gen_artifacts" TO "anon";
GRANT ALL ON TABLE "public"."gen_artifacts" TO "authenticated";
GRANT ALL ON TABLE "public"."gen_artifacts" TO "service_role";



GRANT ALL ON TABLE "public"."gen_questions" TO "anon";
GRANT ALL ON TABLE "public"."gen_questions" TO "authenticated";
GRANT ALL ON TABLE "public"."gen_questions" TO "service_role";



GRANT ALL ON TABLE "public"."gen_questions_concepts_maps" TO "anon";
GRANT ALL ON TABLE "public"."gen_questions_concepts_maps" TO "authenticated";
GRANT ALL ON TABLE "public"."gen_questions_concepts_maps" TO "service_role";



GRANT ALL ON TABLE "public"."orgs" TO "anon";
GRANT ALL ON TABLE "public"."orgs" TO "authenticated";
GRANT ALL ON TABLE "public"."orgs" TO "service_role";



GRANT ALL ON TABLE "public"."qgen_draft_instructions_users_maps" TO "anon";
GRANT ALL ON TABLE "public"."qgen_draft_instructions_users_maps" TO "authenticated";
GRANT ALL ON TABLE "public"."qgen_draft_instructions_users_maps" TO "service_role";



GRANT ALL ON TABLE "public"."qgen_draft_sections" TO "anon";
GRANT ALL ON TABLE "public"."qgen_draft_sections" TO "authenticated";
GRANT ALL ON TABLE "public"."qgen_draft_sections" TO "service_role";



GRANT ALL ON TABLE "public"."qgen_drafts" TO "anon";
GRANT ALL ON TABLE "public"."qgen_drafts" TO "authenticated";
GRANT ALL ON TABLE "public"."qgen_drafts" TO "service_role";



GRANT ALL ON TABLE "public"."subjects" TO "anon";
GRANT ALL ON TABLE "public"."subjects" TO "authenticated";
GRANT ALL ON TABLE "public"."subjects" TO "service_role";



GRANT ALL ON TABLE "public"."topics" TO "anon";
GRANT ALL ON TABLE "public"."topics" TO "authenticated";
GRANT ALL ON TABLE "public"."topics" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































