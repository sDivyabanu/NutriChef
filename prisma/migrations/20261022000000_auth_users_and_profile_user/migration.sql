-- Additive migration: brings the database in line with schema.prisma.
-- The init migration omitted these objects although the schema and the
-- signup route depend on them. Uses IF NOT EXISTS so it is safe on databases
-- where /api/signup already created auth_users at runtime.
-- Reverse: DROP CONSTRAINT "fk_user"; DROP INDEX "Profile_user_id_key";
--          ALTER TABLE "Profile" DROP COLUMN "user_id"; (auth_users holds credentials — back up before dropping)

CREATE TABLE IF NOT EXISTS "auth_users" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "auth_users_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "auth_users_email_key" ON "auth_users"("email");

ALTER TABLE "Profile" ADD COLUMN IF NOT EXISTS "user_id" UUID;
CREATE UNIQUE INDEX IF NOT EXISTS "Profile_user_id_key" ON "Profile"("user_id");

DO $$ BEGIN
  ALTER TABLE "Profile" ADD CONSTRAINT "fk_user" FOREIGN KEY ("user_id")
    REFERENCES "auth_users"("id") ON DELETE CASCADE ON UPDATE NO ACTION;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
