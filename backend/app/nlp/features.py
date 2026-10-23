"""Recipe-side NLP features computed at index time.

Everything here is *derived* from the recipe text and is labelled as such in the API ("estimated", "inferred").
Source fields (title, ingredient lines, instructions, user-entered nutrition) are never modified.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field

from .ingredients import IngredientExtractor
from .lexicon import Lexicon, get_lexicon
from .text import normalize

FEATURE_VERSION = 9

# ---------------------------------------------------------------- cuisine signals (title keywords, ingredients)
CUISINE_TITLE: dict[str, list[str]] = {
    "south indian": ["dosa", "dosai", "idli", "idly", "sambar", "sambhar", "rasam", "uttapam", "appam", "avial", "poriyal",
                     "kootu", "upma", "pongal", "payasam", "chettinad", "kerala", "madras", "malabar", "mangalorean",
                     "south indian", "tamil", "kuzhambu", "kulambu", "thoran", "vada", "lemon rice", "curd rice",
                     "tamarind rice", "puliyodarai", "bisi bele"],
    "indian": ["curry", "masala", "tikka", "biryani", "dal", "daal", "dhal", "paneer", "korma", "vindaloo", "chutney",
               "raita", "pakora", "samosa", "naan", "chapati", "roti", "paratha", "tandoori", "saag", "aloo", "gobi",
               "chana", "chole", "rajma", "kheer", "lassi", "kofta", "keema", "pulao", "pilau", "makhani", "jalfrezi",
               "bhaji", "indian", "bombay", "goan", "punjabi", "kashmiri", "dhansak", "halwa", "chaat", "khichdi",
               "rogan josh", "achari", "kulfi", "ladoo", "jalebi", "bhuna", "balti", "dum"],
    "italian": ["pasta", "risotto", "lasagna", "lasagne", "pizza", "bruschetta", "panzanella", "carbonara", "bolognese",
                "pesto", "gnocchi", "polenta", "osso buco", "tiramisu", "panna cotta", "focaccia", "crostini", "frittata",
                "caprese", "italian", "tuscan", "parmigiana", "cacio e pepe", "minestrone", "ribollita", "spaghetti",
                "linguine", "fettuccine", "penne", "rigatoni", "orecchiette", "ravioli", "tortellini", "arancini",
                "piccata", "marsala", "saltimbocca", "cacciatore", "puttanesca", "amatriciana", "arrabbiata", "biscotti",
                "cannoli", "affogato", "calzone", "agrodolce", "vitello", "sicilian", "roman", "genovese", "bucatini"],
    "mexican": ["taco", "tacos", "burrito", "enchilada", "enchiladas", "quesadilla", "salsa", "guacamole", "mole",
                "pozole", "posole", "tamale", "tamales", "tostada", "carnitas", "fajita", "fajitas", "chilaquiles", "elote",
                "mexican", "tex-mex", "nachos", "huevos rancheros", "al pastor", "birria", "barbacoa", "chile relleno",
                "chiles rellenos", "horchata", "agua fresca", "churros", "tlayuda", "sopes", "michelada", "margarita"],
    "chinese": ["stir-fry", "stir-fried", "stir fry", "fried rice", "lo mein", "chow mein", "kung pao", "dumplings",
                "wonton", "wontons", "dim sum", "mapo", "char siu", "sichuan", "szechuan", "hunan", "cantonese",
                "general tso", "sweet and sour", "hoisin", "bao", "chinese", "congee", "egg rolls", "egg roll",
                "dan dan", "potstickers", "moo shu", "chow fun", "xiao long", "peking", "five-spice", "scallion pancakes"],
    "thai": ["pad thai", "thai", "tom yum", "tom kha", "larb", "satay", "green curry", "red curry", "massaman", "panang",
             "som tam", "khao soi", "pad see ew", "pad kra pao"],
    "japanese": ["sushi", "ramen", "miso", "teriyaki", "tempura", "udon", "soba", "japanese", "katsu", "yakitori",
                 "gyoza", "donburi", "onigiri", "okonomiyaki", "dashi", "tonkatsu", "matcha", "mochi", "sukiyaki",
                 "shabu", "ponzu", "furikake", "chawanmushi", "karaage", "yuzu", "nori"],
    "korean": ["kimchi", "bibimbap", "bulgogi", "gochujang", "korean", "japchae", "galbi", "kalbi", "tteok", "jjigae",
               "banchan", "kimbap", "gochugaru"],
    "vietnamese": ["pho", "banh mi", "vietnamese", "bun cha", "nuoc cham", "goi cuon", "banh xeo"],
    "middle eastern": ["hummus", "falafel", "shawarma", "tabbouleh", "fattoush", "kebab", "kebabs", "kabob", "kofta",
                       "baba ganoush", "baba ghanoush", "tahini", "za'atar", "zaatar", "shakshuka", "labneh", "pita",
                       "lebanese", "israeli", "turkish", "persian", "iranian", "mezze", "muhammara", "freekeh", "baklava",
                       "dukkah", "sumac", "halloumi", "manakeesh", "kibbeh", "mujadara", "fesenjan"],
    "greek": ["greek", "tzatziki", "moussaka", "souvlaki", "spanakopita", "gyro", "gyros", "avgolemono", "pastitsio",
              "dolmades", "horiatiki", "keftedes"],
    "french": ["french", "gratin", "coq au vin", "bouillabaisse", "ratatouille", "quiche", "souffle", "crepe", "crepes",
               "croissant", "tarte tatin", "provencal", "nicoise", "beurre", "confit", "bourguignon", "cassoulet",
               "madeleines", "galette", "clafoutis", "vichyssoise", "bearnaise", "au poivre", "en papillote",
               "croque", "pot-au-feu", "rillettes", "pate", "terrine", "vinaigrette", "remoulade", "dauphinoise"],
    "american": ["burger", "burgers", "bbq", "barbecue", "barbecued", "mac and cheese", "macaroni and cheese", "meatloaf",
                 "cornbread", "buffalo", "sloppy joe", "cobbler", "pot pie", "coleslaw", "thanksgiving", "southern",
                 "cajun", "creole", "gumbo", "jambalaya", "po' boy", "hush puppies", "biscuits", "grits", "pulled pork",
                 "brisket", "s'mores", "brownies", "chocolate chip cookies", "clam chowder", "lobster roll", "fried chicken",
                 "sliders", "hot dog", "pancakes", "waffles", "chili con carne", "deviled eggs", "key lime"],
    "spanish": ["paella", "gazpacho", "tapas", "spanish", "romesco", "patatas bravas", "churros", "manchego", "sangria",
                "catalan", "basque", "salmorejo", "albondigas", "crema catalana", "pimientos de padron"],
    "north african": ["tagine", "moroccan", "harissa", "chermoula", "ras el hanout", "tunisian", "algerian", "couscous"],
    "caribbean": ["jerk", "jamaican", "caribbean", "callaloo", "plantain", "plantains", "cuban", "mojo", "puerto rican",
                  "sofrito", "trinidad", "haitian"],
    "british": ["shepherd's pie", "cottage pie", "fish and chips", "scones", "trifle", "bangers", "yorkshire pudding",
                "sticky toffee", "welsh", "scotch eggs", "toad in the hole", "bubble and squeak", "british", "english",
                "irish", "scottish", "eton mess", "crumpets", "mince pies"],
    "african": ["berbere", "injera", "ethiopian", "jollof", "west african", "nigerian", "senegalese", "south african",
                "piri piri", "peri peri", "suya", "bobotie"],
}
CUISINE_INGREDIENTS: dict[str, dict[str, float]] = {
    "south indian": {"curry leaves": 2.5, "urad dal": 1.5, "sambar powder": 3, "rasam powder": 3, "tamarind": 0.8,
                     "asafoetida": 0.8, "mustard seed": 0.5, "coconut": 0.5, "toor dal": 1.0, "dried red chili": 0.4,
                     "chana dal": 0.8, "coconut oil": 0.8},
    "indian": {"garam masala": 3, "turmeric": 1.2, "cumin": 0.4, "coriander seed": 0.4, "cardamom": 0.5, "ghee": 1.5,
               "paneer": 2, "curry leaves": 1.5, "asafoetida": 2, "fenugreek seed": 1.5, "fenugreek leaves": 2,
               "chaat masala": 3, "mustard oil": 2, "curry powder": 1.5, "nigella seed": 1.5, "carom seed": 2,
               "chickpea flour": 1.2, "basmati rice": 0.8, "lentil": 0.6, "ginger garlic paste": 2, "tamarind": 0.5,
               "naan": 2, "roti": 2, "toor dal": 1.5, "moong dal": 1.5, "urad dal": 1.5, "chana dal": 1.5,
               "mustard seed": 0.6, "cilantro": 0.2, "chili powder": 0.4, "yogurt": 0.2, "jaggery": 1},
    "italian": {"parmesan": 1.0, "mozzarella": 1.0, "pasta": 1.5, "basil": 0.5, "olive oil": 0.2, "bacon": 0.2,
                "ham": 0.3, "balsamic vinegar": 0.6, "ricotta": 0.8, "arborio rice": 2.5, "mascarpone": 1.2,
                "pizza dough": 2, "oregano": 0.3, "caper": 0.4, "anchovy": 0.4, "cornmeal": 0.3},
    "mexican": {"tortilla": 2, "jalapeno": 0.6, "chipotle": 1.5, "cilantro": 0.4, "lime": 0.3, "monterey jack": 0.6,
                "black bean": 0.6, "poblano": 1.2, "tomatillo": 1.8, "cumin": 0.3, "hominy": 1.5, "salsa": 1.2,
                "avocado": 0.4, "pinto bean": 0.8, "serrano chile": 0.6, "dried red chili": 0.3},
    "chinese": {"soy sauce": 0.6, "hoisin sauce": 2, "oyster sauce": 1.5, "sake": 0.6, "five-spice powder": 2,
                "sesame oil": 0.5, "bok choy": 1.2, "star anise": 0.4, "ginger": 0.3, "spring onion": 0.3,
                "rice vinegar": 0.3, "cornstarch": 0.2, "wonton wrapper": 1.5, "noodle": 0.4, "water chestnut": 1.2},
    "thai": {"fish sauce": 1.0, "lemongrass": 2, "coconut milk": 0.6, "lime": 0.3, "hot sauce": 0.2, "cilantro": 0.2,
             "basil": 0.2, "peanut": 0.3, "noodle": 0.2},
    "japanese": {"miso": 1.5, "mirin": 2, "sake": 0.8, "seaweed": 1.5, "fish stock": 1.0, "noodle": 0.3,
                 "horseradish": 0.3, "sushi rice": 2, "soy sauce": 0.4, "rice vinegar": 0.6, "tofu": 0.3, "shiso": 1.5},
    "korean": {"kimchi": 2.5, "red pepper flakes": 0.4, "sesame oil": 0.4, "hot sauce": 0.3, "soy sauce": 0.2},
    "vietnamese": {"fish sauce": 0.8, "noodle": 0.3, "lemongrass": 0.8, "mint": 0.2, "cilantro": 0.2},
    "middle eastern": {"tahini": 1.8, "sumac": 2.2, "za'atar": 2.2, "pita": 1.2, "chickpea": 0.5, "bulgur": 1.2,
                       "pomegranate": 0.6, "grenadine": 0.6, "hummus": 1.5, "cumin": 0.2, "mint": 0.2, "parsley": 0.1},
    "greek": {"feta": 1.2, "oregano": 0.3, "olive": 0.4, "puff pastry": 0.2, "greek yogurt": 0.4, "dill": 0.3,
              "lemon": 0.1},
    "french": {"creme fraiche": 1.0, "shallot": 0.3, "tarragon": 0.6, "mustard": 0.2, "swiss cheese": 0.5,
               "italian seasoning": 0.6, "wine": 0.2, "butter": 0.1, "chervil": 1.0},
    "american": {"barbecue sauce": 1.5, "cornbread": 1, "bacon": 0.2, "cheddar": 0.5, "ketchup": 0.5,
                 "corn syrup": 0.4, "seasoning blend": 0.4, "bun": 0.6},
    "spanish": {"saffron": 0.6, "paprika": 0.4, "sausage": 0.2, "ham": 0.2},
    "north african": {"couscous": 1.0, "hot sauce": 0.2, "seasoning blend": 0.3, "date": 0.3, "apricot": 0.2,
                      "cinnamon": 0.1, "cumin": 0.2},
    "caribbean": {"raw banana": 1.2, "habanero": 1.0, "allspice": 0.6, "seasoning blend": 0.3},
    "british": {},
    "african": {"seasoning blend": 0.3, "peanut butter": 0.3},
}
CUISINE_PARENT = {"south indian": "indian", "north indian": "indian", "chinese": "asian", "thai": "asian",
                  "japanese": "asian", "korean": "asian", "vietnamese": "asian"}

# ---------------------------------------------------------------- meal-type title cues
MEAL_TITLE: dict[str, list[str]] = {
    "dessert": ["cake", "cakes", "cookie", "cookies", "brownie", "brownies", "pie", "tart", "tarts", "pudding",
                "ice cream", "sorbet", "granita", "mousse", "cheesecake", "cupcake", "cupcakes", "fudge", "candy",
                "truffles", "macaron", "macarons", "meringue", "meringues", "pavlova", "crumble", "crisp", "cobbler",
                "custard", "panna cotta", "tiramisu", "parfait", "sundae", "frosting", "toffee", "shortbread",
                "biscotti", "blondies", "bars", "donut", "donuts", "doughnut", "doughnuts", "eclair", "eclairs",
                "cannoli", "baklava", "halwa", "kheer", "payasam", "ladoo", "barfi", "trifle", "compote",
                "semifreddo", "gelato", "souffle", "brittle", "bonbons", "caramels", "marshmallows", "galette",
                "clafoutis", "cobbler", "buckle", "streusel", "torte", "babka", "kulfi", "popsicles", "pops", "fool",
                "madeleines", "financiers", "crème brûlée", "creme brulee", "bread pudding", "s'mores", "baked alaska"],
    "drink": ["cocktail", "punch", "lemonade", "smoothie", "shake", "milkshake", "spritz", "margarita", "martini",
              "mojito", "sangria", "daiquiri", "negroni", "sour", "fizz", "julep", "toddy", "cooler", "lassi", "latte",
              "eggnog", "highball", "mule", "old fashioned", "manhattan", "collins", "gimlet", "paloma", "bellini",
              "mimosa", "spritzer", "shrub", "tonic", "horchata", "agua fresca", "cider", "hot chocolate", "cocoa",
              "chai", "iced tea", "tea", "coffee", "sling", "smash", "flip", "nog", "swizzle", "cobbler cocktail",
              "michelada", "bloody mary", "caipirinha", "spritz", "aperitif", "punch bowl"],
    "breakfast": ["pancake", "pancakes", "waffle", "waffles", "french toast", "omelet", "omelette", "frittata",
                  "scrambled eggs", "scramble", "eggs benedict", "granola", "oatmeal", "porridge", "muesli", "breakfast",
                  "brunch", "hash", "muffin", "muffins", "scone", "scones", "shakshuka", "bagel", "bagels",
                  "overnight oats", "huevos rancheros", "coffee cake", "dosa", "idli", "upma", "poha", "pongal",
                  "paratha", "chilla", "uttapam", "crepes", "crepe", "quiche", "strata", "dutch baby", "fried eggs",
                  "poached eggs", "egg sandwich", "breakfast burrito", "chia pudding", "smoothie bowl", "biscuits and gravy",
                  "cinnamon rolls", "sticky buns", "baked eggs", "migas", "congee"],
    "soup": ["soup", "bisque", "chowder", "gazpacho", "pho", "ramen", "consomme", "minestrone", "rasam", "gumbo",
             "vichyssoise", "potage", "avgolemono", "broth", "velouté", "veloute", "laksa", "tom yum", "tom kha",
             "ribollita", "pozole", "posole", "borscht", "soupe", "stracciatella", "mulligatawny", "dal soup"],
    "salad": ["salad", "slaw", "coleslaw", "tabbouleh", "fattoush", "panzanella", "caprese", "raita", "kachumber"],
    "appetizer": ["dip", "crostini", "bruschetta", "canape", "canapes", "bites", "chips", "crackers", "deviled eggs",
                  "poppers", "sliders", "spring rolls", "pakora", "pakoras", "samosa", "samosas", "hummus", "guacamole",
                  "tapenade", "pate", "terrine", "rillettes", "popcorn", "trail mix", "toasts", "fritters", "croquettes",
                  "arancini", "empanadas", "appetizer", "hors d'oeuvres", "snack", "snacks", "nuts", "wings", "skewers",
                  "crudites", "nachos", "tostadas", "dumplings", "potstickers", "gougeres", "blini", "baba ganoush",
                  "muhammara", "bhaji", "vada", "cheese ball", "spread", "quesadillas", "tartlets", "tapas"],
    "component": ["sauce", "dressing", "vinaigrette", "marinade", "rub", "spice mix", "seasoning", "stock", "pesto",
                  "chutney", "relish", "pickles", "pickled", "jam", "jelly", "compound butter", "syrup", "aioli",
                  "mayonnaise", "gravy", "ketchup", "mustard", "glaze", "lemon curd", "infused oil", "breadcrumbs",
                  "pizza dough", "pie crust", "pie dough", "pastry dough", "brine", "salsa verde", "gremolata",
                  "chimichurri", "spice blend", "masala powder", "garam masala", "ghee", "butter", "crème fraîche",
                  "whipped cream", "simple syrup", "bitters", "puree", "purée", "paste", "confit", "caramel sauce",
                  "hot sauce", "salt", "sugar", "candied", "croutons", "crumble topping", "frosting", "icing",
                  "dough", "crust", "base", "pickle", "preserves", "marmalade", "zhoug", "harissa", "tahini sauce",
                  "romesco", "mojo", "sofrito", "dukkah", "furikake", "togarashi", "za'atar"],
    "bread": ["bread", "loaf", "rolls", "buns", "focaccia", "biscuits", "naan", "flatbread", "flatbreads", "pita",
              "brioche", "challah", "baguette", "ciabatta", "sourdough", "cornbread", "popovers", "pretzels", "bagels",
              "roti", "chapati", "paratha", "puri", "bhatura", "tortillas", "crackers", "grissini"],
    "side": ["mashed", "roasted potatoes", "rice pilaf", "pilaf", "stuffing", "dressing", "gratin", "glazed",
             "sauteed", "sautéed", "steamed", "braised greens", "roasted carrots", "roasted vegetables", "green beans",
             "succotash", "polenta", "fries", "potato salad", "creamed", "puree", "roasted", "grilled vegetables",
             "smashed potatoes", "hasselback", "side", "slaw", "poriyal", "thoran", "kootu", "sabzi", "subzi",
             "pickled", "rice", "couscous", "pilau", "pulao", "risotto", "tian", "latkes", "rosti"],
}
MAIN_HINTS = {"chicken", "beef", "pork", "lamb", "turkey", "duck", "fish", "salmon", "shrimp", "tofu", "tempeh",
              "pasta", "curry", "stew", "roast", "casserole", "tacos", "burger", "biryani", "pizza", "sandwich",
              "sandwiches", "bowl", "bowls", "stir-fry", "noodles", "lasagna", "chili", "braise", "braised", "ragù",
              "ragu", "steak", "chops", "meatballs", "enchiladas", "burritos", "pie", "kebabs", "skewers", "paneer",
              "dal", "masala", "korma", "tagine", "risotto", "paella", "gnocchi", "frittata", "quiche"}

DURATION_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?|one|two|three|four|five|six|eight|ten|twelve|fifteen|twenty|thirty|forty|forty-five|sixty|a|an|half an)"
    r"(?:\s*(?:-|to|or)\s*(?P<b>\d+(?:\.\d+)?))?\s*(?:more\s+|additional\s+|longer\s+)?(?P<u>minutes?|mins?|hours?|hrs?)\b"
)
OVERNIGHT_RE = re.compile(r"\bovernight\b")
AHEAD_RE = re.compile(r"\b(ahead|do ahead|make ahead|can be made|will keep|keeps|store|stored|storage|up to \d+ (days|weeks)|refrigerate up to|freeze up to)\b")
_W2N = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "eight": 8, "ten": 10, "twelve": 12,
        "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "sixty": 60, "a": 1, "an": 1,
        "half an": 0.5}
HARD_TECHNIQUES = re.compile(
    r"\b(deep[- ]fry|deep[- ]frying|candy thermometer|deep[- ]fry thermometer|laminat|temper(ed|ing)? (the )?chocolate|"
    r"souffl|water bath|bain[- ]marie|pastry bag|piping bag|proof|let rise|until doubled|caramel|sous vide|"
    r"debone|butterfly|truss|cure|smoker|soft[- ]ball stage|hard[- ]crack)\w*"
)
FRY_RE = re.compile(r"\b(deep[- ]fr\w+|fry until|fried until|frying|pan[- ]fry|shallow[- ]fry|fritter)\b")


@dataclass
class RecipeFeatures:
    recipe_id: int
    text_hash: str
    parsed: list[dict]
    ingredients: list[str]                 # canonical names (all, incl. optional)
    essential: list[str]                   # non-staple, non-optional canonical names
    alternatives: list[list[str]]
    unknown_lines: list[str]
    equipment_lines: int
    diet: dict[str, bool]
    diet_uncertain: list[str]
    animal: list[str]
    allergens: list[str]
    maybe_allergens: list[str]
    cuisine: str | None
    cuisine_scores: dict[str, float]
    meal_types: list[str]
    est_time_min: int | None
    time_basis: str | None
    difficulty: str
    spice_level: str
    spicy_ingredients: list[str]
    protein_ingredients: list[str]
    fibre_ingredients: list[str]
    vegetable_count: int
    oil_heavy: bool
    fried: bool
    title_norm: str
    n_steps: int
    extras: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def text_hash(rec: dict) -> str:
    payload = json.dumps([rec["title"], rec["ingredients"], rec["instructions"], FEATURE_VERSION], ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _phrase_regex(phrases: list[str]) -> re.Pattern:
    alts = sorted({re.escape(normalize(p)) for p in phrases}, key=len, reverse=True)
    return re.compile(r"(?<![a-z])(?:" + "|".join(alts) + r")(?![a-z])")


_CUISINE_RX = {c: _phrase_regex(k) for c, k in CUISINE_TITLE.items()}
_MEAL_RX = {m: _phrase_regex(k) for m, k in MEAL_TITLE.items()}
_MAIN_RX = _phrase_regex(sorted(MAIN_HINTS))
_NOT_DESSERT_RX = _phrase_regex(["pot pie", "shepherd's pie", "cottage pie", "pizza pie", "chicken pie", "meat pie",
                                 "savory", "savoury", "tomato tart", "onion tart", "tart cherry"])
_HOT_TITLE_RX = _phrase_regex(["spicy", "hot", "fiery", "vindaloo", "jerk", "chili", "chile", "sriracha", "harissa",
                               "diablo", "arrabbiata", "buffalo"])


class FeatureExtractor:
    def __init__(self, lexicon: Lexicon | None = None):
        self.lex = lexicon or get_lexicon()
        self.extractor = IngredientExtractor(self.lex)

    def compute(self, rec: dict) -> RecipeFeatures:
        title = normalize(rec["title"])
        instructions = normalize(rec.get("instructions") or "")
        parsed_lines = [self.extractor.parse_line(line) for line in rec["ingredients"]]
        parsed: list[dict] = []
        names: list[str] = []
        essential: list[str] = []
        unknown: list[str] = []
        alternatives: list[list[str]] = []
        equipment = 0
        alt_members: set[str] = set()
        for pl in parsed_lines:
            if pl.kind != "ingredient":
                equipment += 1
                continue
            parsed.extend(pl.ingredients)
            alternatives.extend(pl.alternatives)
            for alt in pl.alternatives:
                alt_members.update(alt[1:])
            if pl.unknown:
                unknown.append(pl.raw)
            for ing in pl.ingredients:
                n = ing["name"]
                if not n:
                    continue
                names.append(n)
                e = self.lex.get(n)
                if not ing["optional"] and not (e and e.staple) and n not in alt_members:
                    essential.append(n)
        names = list(dict.fromkeys(names))
        essential = list(dict.fromkeys(essential))

        # ---- diet: an ingredient line offering a compliant alternative ("butter or oil") counts as compliant
        alt_of: dict[str, list[str]] = {}
        for alt in alternatives:
            for n in alt:
                alt_of[n] = alt
        entries = [self.lex.get(n) for n in names if self.lex.get(n)]

        def ok(pred) -> bool:
            for e in entries:
                if pred(e):
                    continue
                alts = alt_of.get(e.name, [])
                if any(pred(self.lex.get(a)) for a in alts if a != e.name and self.lex.get(a)):
                    continue
                return False
            return True

        allergens = sorted({a for e in entries for a in e.allergens})
        maybe = sorted({a for e in entries for a in e.maybe_allergens} - set(allergens))
        animal = sorted({e.animal for e in entries if e.animal})
        diet = {
            "vegetarian": ok(lambda e: e.vegetarian and "egg" not in e.allergens),
            "eggetarian": ok(lambda e: e.vegetarian),
            "vegan": ok(lambda e: e.vegan),
            "pescatarian": ok(lambda e: e.animal in (None, "seafood") and "nonveg" not in e.tags or e.animal == "seafood"),
            "gluten_free": ok(lambda e: "gluten" not in e.allergens),
            "dairy_free": ok(lambda e: "dairy" not in e.allergens),
            "egg_free": ok(lambda e: "egg" not in e.allergens),
            "nut_free": ok(lambda e: not ({"tree_nut", "peanut"} & e.allergens)),
        }
        uncertain = list(unknown)
        uncertain += [f"{e.name} (may contain {', '.join(sorted(e.maybe_allergens))})" for e in entries if e.maybe_allergens]

        # ---- cuisine (title keywords weigh 3, signature ingredients add their weight)
        scores: dict[str, float] = {}
        name_set = set(names)
        for cuisine, kws in CUISINE_TITLE.items():
            s = 3.0 * len(set(_CUISINE_RX[cuisine].findall(title)))
            s += sum(w for ing, w in CUISINE_INGREDIENTS.get(cuisine, {}).items() if ing in name_set)
            if s:
                scores[cuisine] = round(s, 2)
        cuisine = None
        if scores:
            ranked = sorted(scores.items(), key=lambda kv: -kv[1])
            best, top = ranked[0]
            second = ranked[1][1] if len(ranked) > 1 else 0.0
            if best == "indian" and scores.get("south indian", 0) >= 3:
                best, top = "south indian", scores["south indian"] + top
            if top >= 3 and (top >= 1.4 * second or CUISINE_PARENT.get(ranked[1][0]) == best
                             or CUISINE_PARENT.get(best) == ranked[1][0]):
                cuisine = best

        # ---- meal type
        meal: list[str] = []
        # classify from the head phrase: "pork chops in mustard sauce" is a main, "mustard sauce" is a component
        head = re.split(r"\s(?:with|in|on|over|plus|alongside|served with)\s|,|:", title, maxsplit=1)[0]
        for mt, rx in _MEAL_RX.items():
            if rx.search(head) or (mt in ("drink", "breakfast", "soup", "salad") and rx.search(title)):
                meal.append(mt)
        sweet = any(self.lex.get(n) and (self.lex.get(n).category in ("sweetener", "sweet") or self.lex.is_a(n, "chocolate")
                                          or n in ("condensed milk", "dulce de leche", "ice cream", "jam", "marshmallow"))
                    for n in names)
        if "dessert" in meal and not sweet and not re.search(r"ice cream|sorbet|granita|gelato|pudding", title):
            meal.remove("dessert")
        cats = [self.lex.get(n).category for n in names if self.lex.get(n)]
        if "dessert" in meal and _NOT_DESSERT_RX.search(title):
            meal.remove("dessert")
            meal.append("main")
        if not meal and cats and sum(c in ("alcohol", "beverage") for c in cats) >= max(1, len(cats) // 2) and "alcohol" in cats:
            meal.append("drink")
        has_protein_main = any(self.lex.get(n) and self.lex.get(n).category in ("meat", "poultry", "fish", "shellfish",
                                                                                  "plant_protein") for n in essential)
        if _MAIN_RX.search(title) or (has_protein_main and not set(meal) & {"dessert", "drink", "component"}):
            if "main" not in meal and not set(meal) & {"dessert", "drink"}:
                meal.append("main")
        if "component" in meal and "main" in meal and has_protein_main:
            meal.remove("component")
        if not meal:
            meal.append("side" if not has_protein_main else "main")

        # ---- time: sum of durations stated in the instructions (excluding make-ahead/storage sentences)
        total = 0.0
        found = False
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", instructions):
            if AHEAD_RE.search(sentence):
                continue
            for m in DURATION_RE.finditer(sentence):
                a = m.group("a")
                av = float(a) if re.fullmatch(r"\d+(?:\.\d+)?", a) else _W2N.get(a, 1)
                bv = float(m.group("b")) if m.group("b") else av
                v = (av + bv) / 2
                total += v * (60 if m.group("u").startswith("h") else 1)
                found = True
            if OVERNIGHT_RE.search(sentence):
                total += 8 * 60
                found = True
        est_time = int(round(total)) if found else None

        # ---- difficulty, spice, health proxies
        steps = [s for s in re.split(r"\n+", rec.get("instructions") or "") if s.strip()]
        techniques = len(set(m.group(0) for m in HARD_TECHNIQUES.finditer(instructions)))
        score = len(essential) / 4 + len(steps) / 3 + 2 * techniques + (1 if (est_time or 0) > 120 else 0)
        difficulty = "easy" if score <= 4.5 else "medium" if score <= 8.5 else "hard"

        spicy = [n for n in essential if self.lex.get(n) and self.lex.get(n).spicy and n not in ("poblano", "paprika")]
        hot_title = bool(_HOT_TITLE_RX.search(title))
        spice_level = "hot" if len(spicy) >= 2 or (spicy and hot_title) or "habanero" in spicy else "medium" if spicy or hot_title else "mild"

        protein = []
        for ing in parsed:
            n = ing["name"]
            e = self.lex.get(n) if n else None
            if not e or ing["optional"] or "protein" not in (e.tags | {t for a in e.ancestors for t in self.lex.get(a).tags}):
                continue
            if ing.get("unit") in ("tsp", "tbsp", "pinch", "dash") or e.category in ("nut", "seed", "condiment"):
                continue
            protein.append(n)
        protein = list(dict.fromkeys(protein))
        fibre = [n for n in essential if self.lex.get(n) and "fibre" in {t for a in self.lex.get(n).ancestors for t in self.lex.get(a).tags}]
        veg_count = sum(1 for n in essential if self.lex.get(n) and self.lex.get(n).category == "vegetable")
        oil_amount = 0.0
        for ing in parsed:
            e = self.lex.get(ing["name"]) if ing["name"] else None
            if e and (e.category == "oil" or e.name in ("butter", "ghee")) and ing.get("quantity"):
                factor = {"cup": 16, "tbsp": 1, "tsp": 1 / 3, "ml": 1 / 15, "stick": 8}.get(ing.get("unit") or "", 0)
                oil_amount += ing["quantity"] * factor
        fried = bool(FRY_RE.search(instructions)) or bool(re.search(r"(?<![a-z])fried(?![a-z])", title))
        oil_heavy = oil_amount >= 8 or bool(re.search(r"\bdeep[- ]fr", instructions))

        return RecipeFeatures(
            recipe_id=rec["id"], text_hash=text_hash(rec), parsed=parsed, ingredients=names, essential=essential,
            alternatives=alternatives, unknown_lines=unknown, equipment_lines=equipment, diet=diet,
            diet_uncertain=uncertain, animal=animal, allergens=allergens, maybe_allergens=maybe, cuisine=cuisine,
            cuisine_scores=scores, meal_types=meal, est_time_min=est_time,
            time_basis="sum of durations stated in the instructions" if found else None,
            difficulty=difficulty, spice_level=spice_level, spicy_ingredients=spicy, protein_ingredients=protein,
            fibre_ingredients=fibre, vegetable_count=veg_count, oil_heavy=oil_heavy, fried=fried, title_norm=title,
            n_steps=len(steps), extras={"oil_tbsp_equiv": round(oil_amount, 1)},
        )
