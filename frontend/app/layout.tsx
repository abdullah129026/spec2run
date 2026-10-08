import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spec2Run — Talk your API into existence",
  description: "Speak in English, get a live deployed microservice.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-zinc-950 text-zinc-100 antialiased">{children}</body>
    </html>
  );
}
