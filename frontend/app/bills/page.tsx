"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ApiError, listBookings } from "@/lib/client";
import { mealPlanLabel, money, plural, timestamp } from "@/lib/format";
import type { BookingSummary } from "@/lib/types";

export default function BillHistoryPage() {
  const [bookings, setBookings] = useState<BookingSummary[]>([]);
  const [count, setCount] = useState(0);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let abandoned = false;

    void (async () => {
      try {
        const page = await listBookings(100);
        if (abandoned) return;
        setBookings(page.items);
        setCount(page.count);
      } catch (caught) {
        if (caught instanceof ApiError && !abandoned) setError(caught);
      } finally {
        if (!abandoned) setLoading(false);
      }
    })();

    return () => {
      abandoned = true;
    };
  }, []);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return bookings;
    return bookings.filter(
      (booking) =>
        booking.reference.toLowerCase().includes(needle) ||
        booking.raw_input.toLowerCase().includes(needle),
    );
  }, [bookings, query]);

  return (
    <main className="history">
      <div className="history__head no-print">
        <div>
          <h1 className="history__title">Bill history</h1>
          <p className="history__count">
            {loading
              ? "Loading…"
              : `${plural(count, "bill")} on record${
                  query.trim() && matches.length !== bookings.length
                    ? ` · ${matches.length} matching`
                    : ""
                }`}
          </p>
        </div>
        <input
          className="control history__search"
          type="search"
          placeholder="Search reference or request…"
          value={query}
          aria-label="Search bills"
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      {error ? (
        <section className="panel placeholder">
          <h2 className="placeholder__title">The service is not responding</h2>
          <p className="placeholder__body">{error.hint ?? error.message}</p>
        </section>
      ) : !loading && bookings.length === 0 ? (
        <section className="panel placeholder">
          <h2 className="placeholder__title">No bills yet</h2>
          <p className="placeholder__body">
            Raise the first one from the <Link href="/">request page</Link>.
          </p>
        </section>
      ) : (
        <div className="history__scroll">
          <table className="history__table">
            <thead>
              <tr>
                <th scope="col">Reference</th>
                <th scope="col">Request</th>
                <th scope="col" className="numeric">
                  Rooms
                </th>
                <th scope="col" className="numeric">
                  Nights
                </th>
                <th scope="col" className="numeric">
                  Total
                </th>
              </tr>
            </thead>
            <tbody>
              {matches.map((booking) => (
                <tr key={booking.booking_id}>
                  <td>
                    <Link
                      className="history__link"
                      href={`/bills/${booking.booking_id}`}
                    >
                      {booking.reference}
                    </Link>
                  </td>
                  <td>
                    <span className="history__request">{booking.raw_input}</span>
                    <span className="history__meta">
                      {timestamp(booking.created_at)} ·{" "}
                      {plural(booking.guests, "guest")} ·{" "}
                      {mealPlanLabel(booking.meal_plan)}
                    </span>
                  </td>
                  <td className="numeric figure">{booking.room_count}</td>
                  <td className="numeric figure">{booking.nights}</td>
                  <td className="numeric figure">
                    {money(booking.total, booking.currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
