"use client";

import { useEffect } from "react";

/**
 * The last line of defence. Anything the page throws that is not an ApiError
 * lands here, so the office sees a way forward instead of a blank document.
 */
export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="shell">
      <section className="panel placeholder placeholder--full">
        <h2 className="placeholder__title">Something went wrong</h2>
        <p className="placeholder__body">
          The page stopped before it could finish. No booking was lost — anything
          already confirmed is still on record.
        </p>
        <p className="placeholder__body">
          <button type="button" className="button" onClick={reset}>
            Try again
          </button>
        </p>
      </section>
    </main>
  );
}
