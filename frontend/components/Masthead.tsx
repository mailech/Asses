"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { BillsIcon } from "./icons";

/**
 * The account control is deliberately honest: this deployment has no
 * authentication, so the menu says who the session is acting as and says that
 * signing in is not wired up, rather than offering a button that does nothing.
 */
export function Masthead() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const account = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    const dismiss = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent) {
        if (event.key === "Escape") setMenuOpen(false);
        return;
      }
      if (!account.current?.contains(event.target as Node)) setMenuOpen(false);
    };

    document.addEventListener("mousedown", dismiss);
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("mousedown", dismiss);
      document.removeEventListener("keydown", dismiss);
    };
  }, [menuOpen]);

  return (
    <header className="masthead no-print">
      <div className="masthead__inner">
        <div>
          <Link href="/" className="masthead__title">
            Accommodation Manager
          </Link>
          <p className="masthead__subtitle">
            Crew lodging, costed against the standing rate card.
          </p>
        </div>

        <nav className="masthead__nav" aria-label="Main">
          <Link
            href="/bills"
            className="navbtn"
            aria-current={pathname === "/bills" ? "page" : undefined}
          >
            <BillsIcon />
            All bills
          </Link>

          <div className="account" ref={account}>
            <button
              type="button"
              className="account__avatar"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Account"
              onClick={() => setMenuOpen((open) => !open)}
            >
              PO
            </button>

            {menuOpen ? (
              <div className="account__menu" role="menu">
                <p className="account__name">Production office</p>
                <p className="account__status">Shared account · not signed in</p>
                <Link
                  href="/bills"
                  className="button button--quiet"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <BillsIcon />
                  Bill history
                </Link>
                <p className="account__note">
                  Every bill on this deployment belongs to the shared production
                  office account. Per-user sign-in arrives with authentication on
                  the API.
                </p>
              </div>
            ) : null}
          </div>
        </nav>
      </div>
    </header>
  );
}
