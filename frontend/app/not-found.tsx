import Link from "next/link";

export default function NotFound() {
  return (
    <main className="shell shell--single">
      <section className="panel placeholder">
        <h2 className="placeholder__title">No such bill</h2>
        <p className="placeholder__body">
          That reference is not on record. Check the link, or look through the{" "}
          <Link href="/bills">bill history</Link>.
        </p>
      </section>
    </main>
  );
}
