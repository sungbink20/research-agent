"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";

interface FeedbackFormProps {
  memoId: string;
  existingRating?: number | null;
  existingFeedback?: string | null;
}

/**
 * Inline feedback form for rating and commenting on a memo.
 *
 * This is important for the product loop: we need to know which memos
 * are useful and which aren't, so we can improve the prompts and pipeline.
 * The rating is a simple 1-5 scale. The text feedback is optional.
 */
export default function FeedbackForm({
  memoId,
  existingRating,
  existingFeedback,
}: FeedbackFormProps) {
  const [rating, setRating] = useState<number | null>(existingRating ?? null);
  const [feedback, setFeedback] = useState(existingFeedback ?? "");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (rating === null && !feedback.trim()) return;
    setIsSubmitting(true);
    setError(null);

    try {
      await submitFeedback(memoId, {
        rating: rating ?? undefined,
        feedback: feedback.trim() || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-5">
        <p className="text-green-400 text-sm">
          Feedback saved. Thank you -- this helps improve future memos.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-5 space-y-4">
      <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
        Rate this memo
      </h3>

      {/* Star rating */}
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => setRating(star)}
            className={`text-2xl transition-colors ${
              rating !== null && star <= rating
                ? "text-yellow-400"
                : "text-zinc-600 hover:text-zinc-400"
            }`}
            aria-label={`Rate ${star} out of 5`}
          >
            &#9733;
          </button>
        ))}
        {rating !== null && (
          <span className="text-sm text-zinc-500 self-center ml-2">
            {rating}/5
          </span>
        )}
      </div>

      {/* Text feedback */}
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="What was useful? What was wrong or missing?"
        className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-white text-sm placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
        rows={2}
      />

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={isSubmitting || (rating === null && !feedback.trim())}
        className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:text-zinc-600 text-white text-sm rounded-lg transition-colors"
      >
        {isSubmitting ? "Submitting..." : "Submit Feedback"}
      </button>
    </div>
  );
}
