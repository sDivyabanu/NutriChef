-- CreateTable
CREATE TABLE "Profile" (
    "id" UUID NOT NULL,
    "full_name" TEXT,
    "avatar_url" TEXT,
    "height_cm" DOUBLE PRECISION,
    "weight_kg" DOUBLE PRECISION,
    "age" INTEGER,
    "diet_type" TEXT,
    "allergies" TEXT[],
    "health_conditions" TEXT[],
    "other_info" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Profile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "DietPreference" (
    "user_id" UUID NOT NULL,
    "diet_type" TEXT,
    "allergies" TEXT[],
    "intolerances" TEXT[],
    "calorie_target" INTEGER,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "DietPreference_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "HydrationTarget" (
    "user_id" UUID NOT NULL,
    "daily_target_ml" INTEGER DEFAULT 2000,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "HydrationTarget_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "IngredientList" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "title" TEXT,
    "items" TEXT[],
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "IngredientList_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PantryItem" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "name" TEXT,
    "quantity" TEXT,
    "category" TEXT,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PantryItem_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Recipe" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "source" TEXT,
    "source_id" TEXT,
    "title" TEXT,
    "image_url" TEXT,
    "url" TEXT,
    "diet_labels" TEXT[],
    "ingredient_lines" TEXT[],
    "nutrients" JSONB,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Recipe_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "UserRecipe" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "recipe_name" TEXT,
    "tag" TEXT,
    "calories" INTEGER,
    "protein" INTEGER,
    "fat" INTEGER,
    "carbs" INTEGER,
    "instructions" TEXT,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "UserRecipe_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "WaterLog" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "logged_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "amount_ml" INTEGER,

    CONSTRAINT "WaterLog_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "WeightLog" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "logged_on" DATE DEFAULT CURRENT_TIMESTAMP,
    "weight_kg" DECIMAL,
    "note" TEXT,

    CONSTRAINT "WeightLog_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "DietPreference" ADD CONSTRAINT "DietPreference_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "HydrationTarget" ADD CONSTRAINT "HydrationTarget_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "IngredientList" ADD CONSTRAINT "IngredientList_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PantryItem" ADD CONSTRAINT "PantryItem_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "UserRecipe" ADD CONSTRAINT "UserRecipe_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "WaterLog" ADD CONSTRAINT "WaterLog_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "WeightLog" ADD CONSTRAINT "WeightLog_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "Profile"("id") ON DELETE SET NULL ON UPDATE CASCADE;
