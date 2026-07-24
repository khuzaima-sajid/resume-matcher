import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ResumeMatch — Score your resume against any job",
  description:
    "Upload your resume and a job description to get an instant match score, missing keywords, and rewrite suggestions.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans text-slate-900 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
