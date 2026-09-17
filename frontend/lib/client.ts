import type { ApiErrorBody, Booking, BookingPage } from "./types";

/** An error the service described in its own words, ready to show the user. */
export class ApiError extends Error {
  readonly code: string;
  readonly hint: string | null;

  constructor(body: ApiErrorBody["error"]) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.hint = body.hint;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, init);
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    if (body && typeof body === "object" && "error" in body) {
      throw new ApiError((body as ApiErrorBody).error);
    }
    throw new ApiError({
      code: "unexpected_error",
      message: `The service returned ${response.status}.`,
      hint: null,
    });
  }
  return body as T;
}

export function createBooking(text: string): Promise<Booking> {
  return request<Booking>("accommodations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export function listBookings(limit = 25): Promise<BookingPage> {
  return request<BookingPage>(`accommodations?limit=${limit}`);
}

export function getBooking(bookingId: string): Promise<Booking> {
  return request<Booking>(`accommodations/${bookingId}`);
}
