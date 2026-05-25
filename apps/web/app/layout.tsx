import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Opentra",
  description: "Operational observability for Indian D2C commerce teams"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
