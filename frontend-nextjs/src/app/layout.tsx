import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import AuthCheck from "@/components/AuthCheck";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit"
});

export const metadata: Metadata = {
  title: "AI Embodied Agent Platform",
  description: "Multi-domain intelligent manufacturing coordination",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${outfit.variable} font-sans antialiased bg-[#0a0e17] text-white`}>
        <AuthCheck>
          {children}
        </AuthCheck>
      </body>
    </html>
  );
}

