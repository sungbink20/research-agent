"use client";

import { InvestmentMemo } from "@/lib/types";

interface MemoDisplayProps {
  memo: InvestmentMemo;
  memoId: string;
}

/**
 * Renders a full investment memo in a scannable format.
 *
 * Design choices:
 * - Sections are visually separated with clear headers
 * - Lists use bullet points for easy scanning
 * - Bull/bear cases are color-coded (green/red) for quick visual parsing
 * - Sources are at the bottom, like footnotes
 *
 * This is designed for how analysts actually read: scan headers,
 * drill into sections of interest, skim bull/bear quickly.
 */
export default function MemoDisplay({ memo, memoId }: MemoDisplayProps) {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b border-zinc-700 pb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">
              {memo.company_name}
            </h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="px-2.5 py-0.5 bg-blue-600/20 text-blue-400 text-sm rounded-full">
                {memo.category}
              </span>
              {memo.website && (
                <a
                  href={
                    memo.website.startsWith("http")
                      ? memo.website
                      : `https://${memo.website}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-zinc-400 hover:text-zinc-300 underline"
                >
                  {memo.website}
                </a>
              )}
            </div>
          </div>
          <span className="text-xs text-zinc-500 font-mono">{memoId}</span>
        </div>
      </div>

      {/* Summary */}
      <Section title="Summary">
        <p className="text-zinc-300 leading-relaxed">{memo.summary}</p>
      </Section>

      {/* Product + Customer + Business Model in a grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Section title="Product">
          <p className="text-zinc-300 text-sm leading-relaxed">
            {memo.product}
          </p>
        </Section>
        <Section title="Customer">
          <p className="text-zinc-300 text-sm leading-relaxed">
            {memo.customer}
          </p>
        </Section>
      </div>

      <Section title="Business Model">
        <p className="text-zinc-300 leading-relaxed">{memo.business_model}</p>
      </Section>

      {/* Traction Signals */}
      {memo.traction_signals.length > 0 && (
        <Section title="Traction Signals">
          <BulletList items={memo.traction_signals} />
        </Section>
      )}

      {/* Competitors */}
      {memo.competitors.length > 0 && (
        <Section title="Competitors">
          <BulletList items={memo.competitors} />
        </Section>
      )}

      {/* Bull / Bear side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {memo.bull_case.length > 0 && (
          <Section title="Bull Case" accent="green">
            <BulletList items={memo.bull_case} className="text-green-300/90" />
          </Section>
        )}
        {memo.bear_case.length > 0 && (
          <Section title="Bear Case" accent="red">
            <BulletList items={memo.bear_case} className="text-red-300/90" />
          </Section>
        )}
      </div>

      {/* Risks */}
      {memo.risks.length > 0 && (
        <Section title="Risks">
          <BulletList items={memo.risks} className="text-amber-300/90" />
        </Section>
      )}

      {/* Open Questions */}
      {memo.open_questions.length > 0 && (
        <Section title="Open Questions">
          <ol className="list-decimal list-inside space-y-2">
            {memo.open_questions.map((q, i) => (
              <li key={i} className="text-zinc-300 text-sm leading-relaxed">
                {q}
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Sources */}
      {memo.sources.length > 0 && (
        <Section title="Sources">
          <div className="space-y-3">
            {memo.sources.map((source, i) => (
              <div key={i} className="text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-zinc-500 font-mono text-xs mt-0.5">
                    [{i + 1}]
                  </span>
                  <div>
                    <span className="text-zinc-300">{source.title}</span>
                    {source.url && (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-blue-400 hover:text-blue-300 underline text-xs"
                      >
                        link
                      </a>
                    )}
                    <span className="ml-2 text-zinc-600 text-xs">
                      ({source.source_type})
                    </span>
                    {source.snippet && (
                      <p className="text-zinc-500 text-xs mt-1 italic">
                        {source.snippet}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-zinc-600 mt-4">
            Note: Sources marked &quot;llm_knowledge&quot; are from the AI
            model&apos;s training data and were not fetched live. Verify
            independently before relying on them.
          </p>
        </Section>
      )}
    </div>
  );
}

// --- Sub-components ---

function Section({
  title,
  children,
  accent,
}: {
  title: string;
  children: React.ReactNode;
  accent?: "green" | "red";
}) {
  const borderColor =
    accent === "green"
      ? "border-green-600/30"
      : accent === "red"
        ? "border-red-600/30"
        : "border-zinc-700/50";

  return (
    <div className={`bg-zinc-800/50 rounded-lg p-5 border ${borderColor}`}>
      <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">
        {title}
      </h2>
      {children}
    </div>
  );
}

function BulletList({
  items,
  className = "text-zinc-300",
}: {
  items: string[];
  className?: string;
}) {
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className={`text-sm leading-relaxed ${className}`}>
          <span className="text-zinc-600 mr-2">&bull;</span>
          {item}
        </li>
      ))}
    </ul>
  );
}
