"use client";

import Link from "next/link";
import { useState } from "react";

import { BackIcon, LinkIcon, PrintIcon } from "./icons";

interface Props {
  bookingId: string;
  /** Shown when the bill is open on its own page rather than beside the composer. */
  showBack?: boolean;
}

export function BillActions({ bookingId, showBack = false }: Props) {
  const [copied, setCopied] = useState(false);

  const copyLink = async () => {
    const link = `${window.location.origin}/bills/${bookingId}`;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2400);
    } catch {
      // Clipboard access is refused in some browsers and on insecure origins.
      window.prompt("Copy this link:", link);
    }
  };

  return (
    <div className="actions no-print">
      {showBack ? (
        <Link href="/" className="button button--quiet">
          <BackIcon />
          New request
        </Link>
      ) : (
        <Link href={`/bills/${bookingId}`} className="button button--quiet">
          Open bill
        </Link>
      )}

      <div className="actions__spacer" />

      {copied ? <span className="actions__note">Link copied</span> : null}
      <button type="button" className="button button--quiet" onClick={copyLink}>
        <LinkIcon />
        Copy link
      </button>
      <button type="button" className="button" onClick={() => window.print()}>
        <PrintIcon />
        Print or save PDF
      </button>
    </div>
  );
}
