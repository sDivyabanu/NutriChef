-- Additive: link a favorite (UserRecipe) to a recipe id in the local NLP recipe store.
-- Reverse: ALTER TABLE "UserRecipe" DROP COLUMN "recipe_ref";
ALTER TABLE "UserRecipe" ADD COLUMN IF NOT EXISTS "recipe_ref" TEXT;
