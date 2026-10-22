import "./globals.css";
// Plus Jakarta Sans is bundled locally via @fontsource (imported in globals.css): no Google Fonts request.
import { MotionConfig } from "@/components/MotionProvider";
import PageWrapper from "@/components/PageWrapper";

export const metadata = {
  title: "NutriChef",
  description: "Smart recipe suggestions based on your ingredients & diet.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-cream text-ink antialiased">
        <MotionConfig><PageWrapper>
          <div className="flex-1">{children}</div>

          {/* Footer */}
          <footer className="site-copyright text-center py-6 text-slate-600 text-xs font-mono">
            © {new Date().getFullYear()} NutriChef. All rights reserved.
          </footer>
        </PageWrapper></MotionConfig>
      </body>
    </html>
  );
}
