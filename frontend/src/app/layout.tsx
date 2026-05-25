import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import { Providers } from '@/components/providers';
import { Toaster } from '@/components/ui/sonner';
import { Activity, BarChart3, Stethoscope } from 'lucide-react';
import './globals.css';

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Physician Candidate Matcher',
  description:
    'AI-powered physician candidate matching for healthcare recruiters. Score, rank, and evaluate physician candidates against job descriptions with explainable results.',
};

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      {children}
    </Link>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="flex min-h-full flex-col bg-gray-50/50 font-sans antialiased">
        <Providers>
          <header className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
            <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
              <Link
                href="/"
                className="flex items-center gap-2 text-lg font-semibold tracking-tight text-foreground"
              >
                <Stethoscope className="size-5 text-blue-600" />
                <span className="hidden sm:inline">
                  Physician Candidate Matcher
                </span>
                <span className="sm:hidden">PCM</span>
              </Link>
              <nav className="flex items-center gap-1" aria-label="Main navigation">
                <NavLink href="/match">
                  <Activity className="size-4" />
                  Match
                </NavLink>
                <NavLink href="/analytics">
                  <BarChart3 className="size-4" />
                  Analytics
                </NavLink>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <Toaster richColors closeButton position="bottom-right" />
        </Providers>
      </body>
    </html>
  );
}
