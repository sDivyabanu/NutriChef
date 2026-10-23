// src/lib/normalizeIngredient.ts
export function normalizeIngredient(raw: string): string {
  if (!raw) return "";
  // lower, trim
  let s = raw.toLowerCase().trim();

  // remove numbers, fractions, e.g. "2", "1/2", "1 1/2"
  s = s.replace(/\d+\s*\d*\/?\d*/g, "").trim();

  // remove common units (simple list) and parentheses
  s = s.replace(/\((.*?)\)/g, ""); // remove parentheses
  s = s.replace(/\b(cups?|cup|tablespoons?|tbsp|tbsps?|teaspoons?|tsp|grams?|g|kg|ml|ltr|lbs?|pounds?)\b/g, "");
  s = s.replace(/\b(of|and|or)\b/g, "");
  s = s.replace(/[^a-z\s-]/g, ""); // keep letters, spaces, hyphens

  s = s.replace(/\s+/g, " ").trim();

  // naive singularization: remove trailing 's' for plural -> singular (simple)
  // keep a small exceptions map
  const exceptions: Record<string, string> = {
    "scallions": "scallion",
    "chives": "chive",
    "tomatoes": "tomato",
    "potatoes": "potato",
    "mushrooms": "mushroom",
    "berries": "berry",
    "olives": "olive",
    "peppers": "pepper"
  };

  if (exceptions[s]) return exceptions[s];

  if (s.endsWith("es")) s = s.slice(0, -2);
  else if (s.endsWith("s")) s = s.slice(0, -1);

  return s;
}
