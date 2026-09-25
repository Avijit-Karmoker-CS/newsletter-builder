import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { Shell } from "@/components/Shell";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display-loaded",
});

const body = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-body-loaded",
});

export const metadata: Metadata = {
  title: "Newsletter Builder",
  description: "Build, review, and send newsletters with Slack + Mailchimp",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable}`}>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
