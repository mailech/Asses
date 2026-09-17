import type { Booking } from "./types";

/**
 * Server-side reads for pages that render a bill on the server.
 *
 * A shared bill link has to work on first paint -- it may be opened from an
 * email, printed straight away, or fetched by something that does not run
 * JavaScript. Those pages talk to the API directly rather than going back out
 * through the browser and in again via /api.
 */

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export type BookingResult =
  | { status: "ok"; booking: Booking }
  | { status: "not_found" }
  | { status: "unavailable" };

export async function fetchBooking(bookingId: string): Promise<BookingResult> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/accommodations/${encodeURIComponent(bookingId)}`,
      { cache: "no-store", headers: { Accept: "application/json" } },
    );
    if (response.status === 404) return { status: "not_found" };
    if (!response.ok) return { status: "unavailable" };
    return { status: "ok", booking: (await response.json()) as Booking };
  } catch {
    return { status: "unavailable" };
  }
}
