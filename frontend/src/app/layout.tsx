import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { THEME_INIT_SCRIPT } from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignBridge: Indian Sign Language translation prototype",
  description: "Academic prototype for bidirectional ISL and English translation with an anime avatar.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFF7F5" },
    { media: "(prefers-color-scheme: dark)", color: "#17111F" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-accent focus:px-4 focus:py-3 focus:font-extrabold focus:text-onaccent">
          Skip to the content
        </a>
        {children}
      </body>
    </html>
  );
}
