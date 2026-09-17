"use client";

import { useEffect, useState } from "react";

import { Bill } from "@/components/Bill";
import { BillActions } from "@/components/BillActions";
import { RequestBuilder } from "@/components/RequestBuilder";
import { RequestComposer } from "@/components/RequestComposer";
import { ApiError, createBooking, getBooking, listBookings } from "@/lib/client";
import type { Booking } from "@/lib/types";

export default function Page() {
  const [bill, setBill] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [serviceError, setServiceError] = useState<ApiError | null>(null);

  // On arrival, open the most recent bill. The office is usually here to look
  // at what was raised ten minutes ago, not at an empty page. The full ledger
  // lives on /bills.
  useEffect(() => {
    let abandoned = false;

    void (async () => {
      try {
        const page = await listBookings(1);
        const newest = page.items[0];
        if (newest && !abandoned) setBill(await getBooking(newest.booking_id));
      } catch (error) {
        if (error instanceof ApiError && !abandoned) setServiceError(error);
      } finally {
        if (!abandoned) setLoading(false);
      }
    })();

    return () => {
      abandoned = true;
    };
  }, []);

  const submit = async (text: string) => {
    setPending(true);
    setSubmitError(null);
    try {
      setBill(await createBooking(text));
      setServiceError(null);
    } catch (error) {
      if (error instanceof ApiError) setSubmitError(error);
      else throw error;
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="shell">
      <div className="rail">
        <RequestComposer pending={pending} error={submitError} onSubmit={submit} />
        <RequestBuilder pending={pending} onSubmit={submit} />
      </div>

      {bill ? (
        <div>
          <BillActions bookingId={bill.booking_id} />
          <Bill booking={bill} />
        </div>
      ) : (
        <section className="panel placeholder no-print">
          <h2 className="placeholder__title">
            {serviceError
              ? "The service is not responding"
              : loading
                ? "Opening the ledger"
                : "No bills yet"}
          </h2>
          <p className="placeholder__body">
            {serviceError
              ? (serviceError.hint ?? serviceError.message)
              : "Write a request the way you would send it to the production office, or build one from the rate card. It will be read, costed, and billed here."}
          </p>
        </section>
      )}
    </main>
  );
}
