"use client";

import { useRef, useState } from "react";

import type { ApiError } from "@/lib/client";

/** Written the way the departments actually write them, not as feature demos. */
const EXAMPLES = [
  "Book 3 double rooms and 1 suite for 10 nights with half board for the lead cast and director",
  "2 dorms and a guesthouse for the stunt team, 5 nights, full board",
  "a couple of twin rooms for the grips — 12 nights, B&B",
];

interface Props {
  pending: boolean;
  error: ApiError | null;
  onSubmit: (text: string) => void;
}

export function RequestComposer({ pending, error, onSubmit }: Props) {
  const [text, setText] = useState("");
  const field = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const trimmed = text.trim();
    if (trimmed && !pending) onSubmit(trimmed);
  };

  const useExample = (example: string) => {
    setText(example);
    field.current?.focus();
  };

  return (
    <section className="panel composer no-print" aria-labelledby="composer-heading">
      <h2 className="eyebrow" id="composer-heading">
        New request
      </h2>

      <label className="visually-hidden" htmlFor="request-text">
        Accommodation request, in plain English
      </label>
      <textarea
        id="request-text"
        ref={field}
        className="composer__field"
        value={text}
        placeholder="Book 3 double rooms and 1 suite for 10 nights with half board…"
        spellCheck={false}
        disabled={pending}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            submit();
          }
        }}
      />

      <div className="composer__actions">
        <span className="composer__shortcut">
          <kbd>Ctrl</kbd> + <kbd>Enter</kbd>
        </span>
        <button
          type="button"
          className="button"
          onClick={submit}
          disabled={pending || text.trim().length === 0}
        >
          {pending ? "Costing…" : "Book accommodation"}
        </button>
      </div>

      {error ? (
        <div className="notice" role="alert">
          <span className="notice__code">{error.code}</span>
          <p className="notice__message">{error.message}</p>
          {error.hint ? <p className="notice__hint">{error.hint}</p> : null}
        </div>
      ) : null}

      <div className="examples">
        <h3 className="eyebrow">Try one of these</h3>
        <ul className="examples__list">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <button
                type="button"
                className="examples__button"
                onClick={() => useExample(example)}
              >
                {example}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
