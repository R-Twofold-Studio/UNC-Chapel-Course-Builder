import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UNC Course Builder",
  description: "Plan UNC-Chapel Hill schedules and degree progress.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-zinc-900 antialiased">{children}</body>
    </html>
  );
}
