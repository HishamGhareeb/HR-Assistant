import type { ReactNode } from "react";

export function StatusChip({ tone, children }: { tone: string; children: ReactNode }) {
  return <span className={`chip chip--${tone}`}>{children}</span>;
}
