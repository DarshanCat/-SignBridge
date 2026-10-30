import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignBridge: Indian Sign Language translation prototype",
  description: "Academic prototype for bidirectional ISL and English translation with a 3D avatar.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
