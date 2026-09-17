import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Bill } from "@/components/Bill";
import { BillActions } from "@/components/BillActions";
import { fetchBooking } from "@/lib/server";

type PageProps = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const result = await fetchBooking(id);
  if (result.status !== "ok") return { title: "Bill · Accommodation Manager" };
  return {
    title: `${result.booking.reference} · Accommodation Manager`,
    description: result.booking.raw_input,
  };
}

export default async function BillPage({ params }: PageProps) {
  const { id } = await params;
  const result = await fetchBooking(id);

  if (result.status === "not_found") notFound();

  if (result.status === "unavailable") {
    return (
      <main className="shell shell--single">
        <section className="panel placeholder">
          <h2 className="placeholder__title">The service is not responding</h2>
          <p className="placeholder__body">
            This bill exists on the accommodation service, which is not answering
            right now. Start the backend and reload.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell shell--single">
      <BillActions bookingId={result.booking.booking_id} showBack />
      <Bill booking={result.booking} />
    </main>
  );
}
