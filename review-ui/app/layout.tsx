import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Providers from "./providers";
import Nav from "@/components/nav";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Claude Flow Review",
  description: "Code review dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-background text-foreground">
        <Providers>
          <div className="min-h-screen md:flex">
            <Nav />
            <main className="min-w-0 flex-1 md:pl-64 md:pt-14">
              <div className="mx-auto max-w-[1440px]">{children}</div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
