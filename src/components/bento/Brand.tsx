import Link from "next/link";

/** A bold chef-hat mark shared by every navigation surface. */
export function LogoMark({ size = 36 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden><rect x="2" y="2" width="36" height="36" rx="9" fill="#FF4D35" stroke="#0A0A0A" strokeWidth="2.5" /><path d="M12 24v-6c-7-4-1-12 4-8 2-7 11-5 11 1 7-2 10 7 3 9v8H12Z" fill="#F7F5ED" stroke="#0A0A0A" strokeWidth="2" /><path d="M13 24h16" stroke="#0A0A0A" strokeWidth="2" /></svg>;
}
export function Logo({ href = "/" }: { href?: string }) {
  return <Link href={href} className="brand" aria-label="NutriChef home"><LogoMark /><span>NUTRI<span className="brand-chef">CHEF</span><small>GOOD FOOD. SMARTER.</small></span></Link>;
}
