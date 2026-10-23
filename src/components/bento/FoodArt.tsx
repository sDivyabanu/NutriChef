// Illustrative food tile used where a photo would go. The recipe dataset ships no images and NutriChef never
// hotlinks remote photos, so each recipe gets a category-matched artwork (clearly decorative, aria-hidden).

const RULES: [RegExp, string, string][] = [
  [/salad|slaw|greens/, "🥗", "#DCEBDF"],
  [/soup|bisque|chowder|rasam|broth|stew|chili/, "🍲", "#F6DCCB"],
  [/curry|masala|dal|korma|tikka|paneer|biryani|vindaloo|sambar|kuzhambu/, "🍛", "#F8D9B8"],
  [/pasta|spaghetti|linguine|penne|lasagn|noodle|ramen|lo mein|pad thai/, "🍝", "#F5E1C9"],
  [/pizza|flatbread/, "🍕", "#F7D7C4"],
  [/rice|risotto|pilaf|paella|pulao/, "🍚", "#EDE7DA"],
  [/taco|burrito|quesadilla|enchilada|fajita|nacho/, "🌮", "#F6DEC3"],
  [/sandwich|burger|slider|wrap|toast/, "🥪", "#F1E2CC"],
  [/egg|omelet|frittata|shakshuka/, "🍳", "#F9E8C2"],
  [/pancake|waffle|crepe/, "🥞", "#F6E0C1"],
  [/cake|cupcake|cheesecake|torte/, "🍰", "#F9DCE0"],
  [/cookie|biscotti|brownie|bar/, "🍪", "#F1DCC6"],
  [/pie|tart|crumble|cobbler|galette/, "🥧", "#F4DDC6"],
  [/ice cream|sorbet|gelato|popsicle|semifreddo/, "🍨", "#F5E0EA"],
  [/chocolate|fudge|truffle/, "🍫", "#EBD6CC"],
  [/bread|loaf|roll|bun|focaccia|biscuit|naan|roti/, "🍞", "#F3E3CC"],
  [/cocktail|margarita|martini|spritz|punch|sangria|mojito/, "🍸", "#E2EEF0"],
  [/smoothie|shake|lassi|juice|lemonade/, "🥤", "#F7E2D8"],
  [/tea|coffee|latte|chai/, "☕", "#EDE2D6"],
  [/shrimp|prawn|crab|lobster|scallop|clam|mussel/, "🍤", "#F8DCCF"],
  [/salmon|fish|cod|tuna|trout|halibut|snapper/, "🐟", "#DDEBEC"],
  [/chicken|turkey|duck/, "🍗", "#F5DEC6"],
  [/steak|beef|pork|lamb|rib|brisket|meatball/, "🥩", "#F2D5CC"],
  [/tofu|tempeh/, "🥢", "#E7EEDF"],
  [/sushi|bento|onigiri/, "🍱", "#F5E8E0"],
  [/dumpling|wonton|gyoza|potsticker/, "🥟", "#F3E6D3"],
  [/potato|fries|latke/, "🥔", "#EFE3CF"],
  [/mushroom/, "🍄", "#EAE0D6"],
  [/eggplant|brinjal|aubergine/, "🍆", "#E8DDEA"],
  [/corn/, "🌽", "#F7EBC5"],
  [/avocado|guacamole/, "🥑", "#E2EDD5"],
  [/carrot/, "🥕", "#F8DFCB"],
  [/tomato/, "🍅", "#F8D6CF"],
  [/broccoli|cauliflower|kale|spinach/, "🥦", "#DDEAD9"],
  [/apple|pear|peach|plum|berry|berries|cherry|fruit|mango|banana/, "🍑", "#F9DED3"],
  [/cheese/, "🧀", "#F6E8C4"],
];

export function foodArt(title: string, hints: string[] = []): { emoji: string; bg: string } {
  const t = `${title} ${hints.join(" ")}`.toLowerCase();
  for (const [rx, emoji, bg] of RULES) if (rx.test(t)) return { emoji, bg };
  return { emoji: "🍽️", bg: "#F5E8E0" };
}

export default function FoodArt({
  title,
  hints = [],
  className = "",
  size = "md",
}: {
  title: string;
  hints?: string[];
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
}) {
  const { emoji } = foodArt(title, hints);
  const salad = /salad|greens|spinach|avocado/i.test(`${title} ${hints.join(' ')}`);
  const bg = salad ? '#BDA7F2' : '#FFD86B';
  return (
    <div className={`${className.includes("absolute") ? "" : "relative "}overflow-hidden flex items-center justify-center ${className}`} style={{ backgroundColor: bg }} aria-hidden>
      <svg viewBox="0 0 400 260" className={`w-full h-full transition-transform duration-300 group-hover:rotate-3 ${size === 'sm' ? 'max-h-40' : ''}`} preserveAspectRatio="xMidYMid slice">
        <g stroke="#0A0A0A" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <path d="m42 38 5-16 5 16 16 5-16 5-5 16-5-16-16-5Z" fill="#F7F5ED" />
          <ellipse cx="207" cy="210" rx="110" ry="12" fill="#0A0A0A" opacity=".12" stroke="none" />
          <g transform="rotate(-9 200 135)">
            <ellipse cx="200" cy="140" rx="110" ry="79" fill="#0A0A0A" />
            <ellipse cx="195" cy="130" rx="110" ry="79" fill="#F7F5ED" />
            <ellipse cx="195" cy="130" rx="86" ry="59" fill={salad ? '#A8BE78' : '#FF4D35'} />
            {[[156,113],[189,101],[221,112],[172,143],[212,146]].map(([x,y],i)=><rect key={i} x={x-8} y={y-7} width="17" height="16" rx="3" fill="#FFF0BF" transform={`rotate(${i*14} ${x} ${y})`} />)}
            <path d="m189 124 7-17 8 18Zm-43 10 15-2-8 12m69-8 14-8-4 16" fill="#779D63" />
          </g>
          <path d="m325 66-16 74m8-76-9 31m18-27-8 30m-6-36-8 31q-4 13 4 15" fill="none" strokeWidth="4" />
          <path d="M68 145 85 77q14-18 18 2l-18 71" fill="#F7F5ED" />
          <path d="m272 44 5-11m8 17 10-7m-13-6 2-11" fill="none" />
        </g>
      </svg>
      <span className="absolute right-4 bottom-4 rounded-full border-2 border-black bg-cream px-3 py-1 text-2xl">{emoji}</span>
    </div>
  );
}
