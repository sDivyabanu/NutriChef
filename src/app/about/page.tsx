export default function AboutPage() {
  return (
    <main className="max-w-3xl mx-auto py-20 px-6 bg-white">
      <h1 className="text-4xl font-bold text-slate-800 mb-6">About Nutichef</h1>
      <p className="text-slate-600 mb-8">
        Nutichef is your personal kitchen assistant. Simply upload or enter the
        ingredients you have, and we’ll suggest recipes tailored to your diet.
        Beyond just cooking, Nutichef helps you stay on track with hydration and
        weight goals.
      </p>

      <h2 className="text-2xl font-semibold text-emerald-600 mb-4">Why Nutichef?</h2>
      <ul className="list-disc list-inside text-slate-600 space-y-2 mb-10">
        <li>Discover recipes from the ingredients you already have</li>
        <li>Personalized suggestions based on dietary preferences</li>
        <li>Track hydration and daily water intake</li>
        <li>Log weight and see your progress over time</li>
      </ul>

      <h2 className="text-2xl font-semibold text-emerald-600 mb-4">FAQ</h2>
      <div className="space-y-6 text-slate-600">
        <div>
          <p className="font-semibold text-slate-800">How does recipe suggestion work?</p>
          <p>
            You can either upload a photo of your ingredients (AI detects items),
            or enter them manually. Nutichef matches them with suitable recipes.
          </p>
        </div>
        <div>
          <p className="font-semibold text-slate-800">
            Do I need to pay to use Nutichef?
          </p>
          <p>
            No — Nutichef is free for core features. Advanced AI suggestions may
            require a premium plan later.
          </p>
        </div>
        <div>
          <p className="font-semibold text-slate-800">Can I use it on mobile?</p>
          <p>
            Yes, Nutichef is fully responsive and works seamlessly on desktop
            and mobile devices.
          </p>
        </div>
      </div>
    </main>
  );
}
