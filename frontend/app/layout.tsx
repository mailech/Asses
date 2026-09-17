import type { Metadata } from "next";

import { Masthead } from "@/components/Masthead";
import "./globals.css";

export const metadata: Metadata = {
  title: "Accommodation Manager",
  description:
    "Turn a plain-English crew lodging request into a priced, printable bill.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Masthead />
        {children}
      </body>
    </html>
  );
}
