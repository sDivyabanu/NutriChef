// Root wrapper. No transform/animation here: a transformed ancestor would break position:fixed children.
export default function PageWrapper({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen flex flex-col">{children}</div>;
}
