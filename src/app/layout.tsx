import "./globals.css";
import { Poppins } from "next/font/google";
import PageWrapper from "@/components/PageWrapper";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata = {
  title: "Nutrichef",
  description: "Smart recipe suggestions based on your ingredients & diet.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={poppins.className}>
      <body className="bg-gradient-to-b from-emerald-50 via-white to-emerald-100 text-slate-800">
        <PageWrapper>
          <main className="flex-1">{children}</main>

          {/* Footer */}
          <footer className="text-center py-6 text-slate-500 text-sm border-t border-slate-200">
            © {new Date().getFullYear()} Nutrichef. All rights reserved.
          </footer>
        </PageWrapper>
      </body>
    </html>
  );
}
