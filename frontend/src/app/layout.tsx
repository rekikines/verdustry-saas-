import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  weight: ["400", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Verdustry — Gestion Data",
  description: "Plateforme SaaS de gestion de données environnementales",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="h-full">
      <body
        className={`${inter.variable} ${sora.variable} min-h-full font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}