"""Constraint vocabulary used by query understanding (English + Tamil/Tanglish cues)."""
from __future__ import annotations

# ---------------------------------------------------------------- diets
# NutriChef follows the app's own profile options: "Vegetarian" excludes eggs (Indian convention),
# "Eggetarian" is vegetarian + eggs. Users can change this in preferences (vegetarian_includes_eggs).
DIET_PHRASES: dict[str, str] = {
    "vegetarian": "vegetarian", "veg": "vegetarian", "veggie": "vegetarian", "vegitarian": "vegetarian",
    "meatless": "vegetarian", "meat free": "vegetarian", "meat-free": "vegetarian", "saivam": "vegetarian",
    "shakahari": "vegetarian", "sakahari": "vegetarian", "pure veg": "vegetarian", "lacto vegetarian": "vegetarian",
    "vegan": "vegan", "plant based": "vegan", "plant-based": "vegan", "fully plant based": "vegan",
    "eggetarian": "eggetarian", "ovo vegetarian": "eggetarian", "lacto ovo vegetarian": "eggetarian",
    "pescatarian": "pescatarian", "pescetarian": "pescatarian",
    "non veg": "non-vegetarian", "non-veg": "non-vegetarian", "nonveg": "non-vegetarian",
    "non vegetarian": "non-vegetarian", "non-vegetarian": "non-vegetarian", "asaivam": "non-vegetarian",
    "gluten free": "gluten-free", "gluten-free": "gluten-free", "celiac": "gluten-free", "coeliac": "gluten-free",
    "dairy free": "dairy-free", "dairy-free": "dairy-free", "lactose free": "dairy-free", "lactose-free": "dairy-free",
    "lactose intolerant": "dairy-free",
    "nut free": "nut-free", "nut-free": "nut-free", "egg free": "egg-free", "egg-free": "egg-free",
    "eggless": "egg-free", "without egg": "egg-free",
    "jain": "jain",
}
DIETS = ("vegetarian", "vegan", "eggetarian", "pescatarian", "non-vegetarian", "gluten-free", "dairy-free",
         "nut-free", "egg-free", "jain")

# Exclusion groups a user can name after "no"/"without"/"-free" that are not single lexicon entries.
GROUP_WORDS: dict[str, str] = {
    "meat": "meat", "meats": "meat", "non veg": "meat", "nonveg": "meat", "animal products": "animal",
    "gluten": "gluten", "wheat": "gluten", "soy": "soy", "soya": "soy", "nuts": "nuts", "nut": "nuts",
    "tree nuts": "tree_nut", "dairy": "dairy", "lactose": "dairy", "eggs": "egg", "egg": "egg",
    "seafood": "seafood", "fish": "fish", "shellfish": "shellfish", "alcohol": "alcohol", "booze": "alcohol",
    "onion garlic": "onion_garlic", "onion and garlic": "onion_garlic",
}

# ---------------------------------------------------------------- cuisines
CUISINE_PHRASES: dict[str, str] = {
    "indian": "indian", "desi": "indian", "north indian": "north indian", "punjabi": "north indian",
    "mughlai": "north indian", "south indian": "south indian", "tamil": "south indian", "tamilnadu": "south indian",
    "tamil nadu": "south indian", "chettinad": "south indian", "kerala": "south indian", "karnataka": "south indian",
    "andhra": "south indian", "hyderabadi": "south indian", "udupi": "south indian", "madras": "south indian",
    "bengali": "indian", "gujarati": "indian", "goan": "indian", "maharashtrian": "indian", "rajasthani": "indian",
    "italian": "italian", "mexican": "mexican", "tex mex": "mexican", "tex-mex": "mexican", "chinese": "chinese",
    "indo chinese": "chinese", "szechuan": "chinese", "sichuan": "chinese", "cantonese": "chinese",
    "thai": "thai", "japanese": "japanese", "korean": "korean", "vietnamese": "vietnamese", "asian": "asian",
    "french": "french", "greek": "greek", "mediterranean": "mediterranean", "middle eastern": "middle eastern",
    "lebanese": "middle eastern", "turkish": "middle eastern", "persian": "middle eastern", "israeli": "middle eastern",
    "moroccan": "north african", "north african": "north african", "ethiopian": "african", "african": "african",
    "spanish": "spanish", "american": "american", "southern": "american", "cajun": "american", "bbq": "american",
    "caribbean": "caribbean", "jamaican": "caribbean", "british": "british", "english": "british", "irish": "british",
    "german": "european", "european": "european", "scandinavian": "european", "russian": "european",
    "latin american": "latin american", "brazilian": "latin american", "peruvian": "latin american",
    "cuban": "latin american",
}
CUISINE_PARENT = {"south indian": "indian", "north indian": "indian", "chinese": "asian", "thai": "asian",
                  "japanese": "asian", "korean": "asian", "vietnamese": "asian"}

# ---------------------------------------------------------------- meal types
MEAL_PHRASES: dict[str, str] = {
    "breakfast": "breakfast", "brekkie": "breakfast", "brunch": "breakfast", "morning": "breakfast",
    "tiffin": "breakfast", "kaalai": "breakfast", "kalai": "breakfast", "kaalai unavu": "breakfast",
    "lunch": "lunch", "madhiyam": "lunch", "mathiyam": "lunch", "lunchbox": "lunch", "lunch box": "lunch",
    "dinner": "dinner", "supper": "dinner", "night": "dinner", "iravu": "dinner", "raathri": "dinner",
    "main course": "dinner", "main dish": "dinner", "weeknight": "dinner", "entree": "dinner",
    "snack": "snack", "snacks": "snack", "evening snack": "snack", "tea time": "snack", "teatime": "snack",
    "dessert": "dessert", "desserts": "dessert", "sweet dish": "dessert", "pudding": "dessert",
    "appetizer": "appetizer", "appetiser": "appetizer", "starter": "appetizer", "starters": "appetizer",
    "side": "side", "side dish": "side", "sides": "side", "drink": "drink", "drinks": "drink",
    "beverage": "drink", "cocktail": "drink", "smoothie": "drink", "soup": "soup", "salad": "salad",
}

# ---------------------------------------------------------------- qualities (soft preferences)
QUALITY_PHRASES: dict[str, str] = {
    "high protein": "high-protein", "high-protein": "high-protein", "protein rich": "high-protein",
    "protein-rich": "high-protein", "protein packed": "high-protein", "lots of protein": "high-protein",
    "low calorie": "low-calorie", "low-calorie": "low-calorie", "low cal": "low-calorie", "low-cal": "low-calorie",
    "light": "light", "high fibre": "high-fibre", "high-fibre": "high-fibre", "high fiber": "high-fibre",
    "high-fiber": "high-fibre", "fibre rich": "high-fibre", "fiber rich": "high-fibre",
    "low oil": "low-oil", "low-oil": "low-oil", "less oil": "low-oil", "oil free": "low-oil", "oil-free": "low-oil",
    "low fat": "low-fat", "low-fat": "low-fat", "low carb": "low-carb", "low-carb": "low-carb", "keto": "low-carb",
    "low sugar": "low-sugar", "low-sugar": "low-sugar", "healthy": "healthy", "healthier": "healthy",
    "nutritious": "healthy", "wholesome": "healthy",
    "spicy": "spicy", "hot and spicy": "spicy", "fiery": "spicy", "kaaram": "spicy", "karam": "spicy",
    "kaarama": "spicy", "spicy-hot": "spicy", "mild": "mild", "not spicy": "mild", "less spicy": "mild",
    "non spicy": "mild", "kid friendly": "mild",
    "filling": "filling", "hearty": "filling", "satisfying": "filling", "substantial": "filling",
    "comfort": "comforting", "comforting": "comforting", "cozy": "comforting", "crispy": "crispy",
    "crunchy": "crispy", "creamy": "creamy", "tangy": "tangy", "sweet": "sweet", "quick": "quick", "fast": "quick",
    "easy": "easy", "simple": "easy", "beginner": "easy", "one pot": "one-pot", "one-pot": "one-pot",
    "one pan": "one-pot", "budget": "budget", "cheap": "budget",
}

# ---------------------------------------------------------------- cue words
EXCLUDE_CUES = {"without", "no", "not", "avoid", "avoiding", "excluding", "exclude", "except", "minus", "skip",
                "hate", "dislike", "allergic", "allergy", "intolerant", "free", "nor", "zero", "never", "omit",
                "remove", "withoutt"}
EXCLUDE_PHRASES = ("free of", "allergic to", "allergy to", "intolerant to", "don't want", "do not want", "dont want",
                   "don't like", "do not like", "dont like", "can't eat", "cannot eat", "cant eat", "don't eat",
                   "do not eat", "dont eat", "leave out", "hold the", "other than")
UNAVAILABLE_PHRASES = ("don't have", "do not have", "dont have", "ran out of", "out of", "no more")
AVAILABLE_CUES = {"have", "got", "having", "leftover", "leftovers", "fridge", "pantry", "kitchen", "left",
                  "iruku", "irukku", "irukudhu", "irukkudhu", "irukkuthu", "enkitta", "ennkitta", "kitta"}
AVAILABLE_PHRASES = ("i have", "i've got", "ive got", "i got", "i've", "we have", "in my fridge", "in the fridge",
                     "in my pantry", "using up", "use up", "left over")
REQUIRE_CUES = {"with", "using", "use", "containing", "contains", "featuring", "including", "includes", "only",
                "made", "vechu", "vachu", "vechi", "vachi", "potta", "pottu"}
PREFER_CUES = {"prefer", "preferably", "ideally", "maybe", "perhaps", "possibly", "optionally", "like", "love",
               "favourite", "favorite"}
# Tamil postpositional negation: "onion illama" = without onion, "onion venam" = no onion
TAMIL_POST_EXCLUDE = {"illama", "illamal", "illaamal", "illaama", "illaame", "illame", "venam", "vendam",
                      "vendaam", "venda", "thavira", "illatha", "illadha"}
TAMIL_POST_AVAILABLE = {"iruku", "irukku", "irukudhu", "irukkudhu", "irukkuthu", "irukkey", "vechu", "vachu",
                        "vechi", "vachi"}
# Tanglish function words that must never be spell-corrected
TANGLISH_WORDS = {
    "enna", "enakku", "enaku", "pannalam", "pannu", "pannunga", "panna", "panni", "seyya", "seiya", "samaikka",
    "samayal", "saapadu", "sapadu", "saapida", "vechu", "vachu", "iruku", "irukku", "enkitta", "ennkitta", "kitta",
    "illama", "illamal", "venam", "vendam", "konjam", "romba", "nalla", "seekiram", "kaaram", "karam", "suggest",
    "sollu", "sollunga", "ethachu", "edhavadhu", "edhachum", "oru", "rendu", "moonu", "naalu", "kudu", "kodu",
    "vendum", "venum", "thavira", "pottu", "potta", "aana", "ana", "um", "ah", "dhaan", "than", "la", "le", "ku",
    "kaalai", "madhiyam", "iravu", "unavu", "tiffin", "saivam", "asaivam", "kuzhambu", "kulambu", "poriyal",
    "kootu", "varuval", "thokku", "sadham", "satham", "chutney", "dosai", "idly", "upma", "pongal", "vada",
}
# Words that only occur in Tamil/Tanglish (used to label the query language; "suggest" etc. are excluded).
TAMIL_MARKERS = {
    "enna", "enakku", "enaku", "pannalam", "pannu", "pannunga", "panni", "samaikka", "samayal", "saapadu", "sapadu",
    "vechu", "vachu", "iruku", "irukku", "enkitta", "ennkitta", "kitta", "illama", "illamal", "venam", "vendam",
    "konjam", "romba", "nalla", "seekiram", "kaaram", "sollu", "sollunga", "ethachu", "edhavadhu", "edhachum",
    "kudu", "kodu", "vendum", "venum", "thavira", "pottu", "potta", "dhaan", "kaalai", "madhiyam", "iravu",
    "unavu", "saivam", "asaivam", "kuzhambu", "kulambu", "poriyal", "kootu", "varuval", "thokku", "sadham", "satham",
}
# Common query words that may be rare in recipe text but must never be "corrected".
QUERY_WORDS = {
    "calorie", "calories", "kcal", "kcals", "protein", "proteins", "carbs", "carb", "fibre", "fiber", "grams",
    "minutes", "minute", "mins", "hours", "hour", "recipes", "recipe", "suggest", "suggestions", "healthy",
    "vegetarian", "vegan", "breakfast", "lunch", "dinner", "snack", "snacks", "dessert", "something", "anything",
    "filling", "spicy", "quick", "dish", "dishes", "meal", "meals", "cuisine", "similar", "please", "thanks",
    "eggetarian", "pescatarian", "nonveg", "gluten", "dairy", "lactose", "allergic", "allergy", "keto", "tiffin",
    "fridge", "pantry", "leftover", "leftovers", "tonight", "today", "weekly", "plan", "people", "persons", "servings",
}
NEGATION_SCOPE_BREAKERS = {"but", "with", "using", "and i", "under", "in", "that", "which", "for", "having"}
LIST_SEPARATORS = {",", "and", "or", "&", "/", "nor", "plus", "also", "+", "um"}
RESET_PHRASES = ("start over", "reset", "new search", "clear filters", "clear all", "forget everything",
                 "never mind", "nevermind", "from scratch")

# Tamil (transliterated) ingredient words from the lexicon; used to label mixed Tamil-English queries.
TAMIL_INGREDIENT_WORDS = frozenset(['aattu', 'aatu', 'annasi', 'arisi', 'athi', 'attu', 'aval', 'avarakkai', 'avil', 'brinji', 'chinna', 'cholam', 'elakkai', 'ellu', 'elumichai', 'elumichampazham', 'ennai', 'eral', 'godhumai', 'gothumai', 'ilai', 'inji', 'iral', 'jathikai', 'javvarisi', 'jeeragam', 'jeerakam', 'kaalan', 'kaanja', 'kadalai', 'kadugu', 'kaduku', 'kambu', 'kanava', 'karamani', 'kari', 'karivepillai', 'kariveppilai', 'karunjeeragam', 'karupatti', 'karuveppilai', 'kathirikaai', 'kathirikai', 'kathirikkai', 'kathrikai', 'kathrikkai', 'keerai', 'kezhvaragu', 'kirambu', 'kizhangu', 'kodai', 'koli', 'konda', 'kondakadalai', 'kose', 'kothamalli', 'kovakkai', 'koyya', 'kozhi', 'kudai', 'kungumapoo', 'lavangam', 'lavangapattai', 'maadhulai', 'maanga', 'maavu', 'malli', 'mampazham', 'manjal', 'meen', 'milagai', 'milagu', 'mor', 'moru', 'mullangi', 'mundhiri', 'munthiri', 'murunga', 'murungaikai', 'murungakkai', 'mutta', 'muttai', 'muttaikos', 'muttaikose', 'nalla', 'nallennai', 'nandu', 'neer', 'nei', 'neyyi', 'nilakadalai', 'omam', 'oorugai', 'paal', 'pachai', 'palakkai', 'pappali', 'parangikai', 'parangikkai', 'paruppu', 'parupu', 'pasalai', 'pasi', 'pattai', 'pattani', 'pavakai', 'pavakkai', 'payaru', 'payatham', 'pazham', 'peerkangai', 'pericham', 'perungaayam', 'perungayam', 'perunjeeragam', 'podi', 'poo', 'poondu', 'poosanikai', 'pori', 'pudalanga', 'pudalangai', 'puli', 'ravai', 'saaru', 'sakkarai', 'sakkaravalli', 'samai', 'sarkarai', 'seeragam', 'seerakam', 'semiya', 'sevai', 'sombu', 'sorakai', 'sorakkai', 'suraikai', 'tannir', 'thaen', 'thairu', 'thakaali', 'thakkali', 'thanni', 'thattai', 'thayir', 'thenga', 'thengai', 'thinai', 'thiratchai', 'thool', 'thuvaram', 'ularntha', 'ulundhu', 'ulundu', 'ulutham', 'uppu', 'urulai', 'urulaikilangu', 'urulaikizhangu', 'vagaigal', 'valli', 'vara', 'varagu', 'vazhaikai', 'vazhaipazham', 'vazhakkai', 'vellai', 'vellam', 'vellarikai', 'vellarikkai', 'vendaikai', 'vendakai', 'vendakkai', 'vendhaya', 'vendhayam', 'vengaayam', 'vengayam', 'vengayum', 'venkayam', 'vennai', 'venthayam', 'verkadalai', 'vidhai', 'yelakkai'])
