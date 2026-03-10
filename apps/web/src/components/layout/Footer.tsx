'use client';

export function Footer() {
  return (
    <footer className="border-t border-border mt-12 py-6 px-4">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text-secondary">
        <div className="flex items-center gap-4">
          <span>&copy; {new Date().getFullYear()} EVE Gatekeeper</span>
          <span className="hidden sm:inline">&middot;</span>
          <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-primary/20 text-primary border border-primary/30">
            Early Access
          </span>
        </div>
        <div className="text-center sm:text-right leading-relaxed">
          EVE Online and all related trademarks are property of CCP hf.
        </div>
      </div>
    </footer>
  );
}
