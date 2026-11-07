import type { Metadata } from 'next';
import { Fraunces, Inter, IBM_Plex_Mono } from 'next/font/google';
import './globals.css';
import { Navbar } from '@/components/Navbar';
import { ToastProvider } from '@/components/Toast';

const display = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  style: ['normal', 'italic'],
  axes: ['opsz'],
});

const sans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: 'SceneSteward — Documentary Consent & Ethical Storytelling',
  description: 'Production safety, participant consent tracking, and ethical boundary verification system.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-slate-950 font-sans text-slate-100 antialiased flex flex-col">
        <ToastProvider>
          <Navbar />
          <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
            {children}
          </main>
          <footer className="mt-8 border-t border-slate-800/80">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
              <div className="flex items-center gap-3" aria-hidden="true">
                <span className="h-px flex-1 bg-slate-800" />
                <span className="h-1.5 w-1.5 rotate-45 bg-brass-500/70" />
                <span className="h-px flex-1 bg-slate-800" />
              </div>
              <p className="mx-auto max-w-2xl text-center font-display text-sm italic leading-relaxed text-slate-400">
                &ldquo;A participant&rsquo;s agreement to one use must never automatically become agreement to another use. Silence is never agreement.&rdquo;
              </p>
              <div className="flex flex-col items-center gap-1.5">
                <span className="ss-kicker">SceneSteward</span>
                <p className="text-[11px] text-slate-500">
                  &copy; 2026 SceneSteward &middot; Documentary Ethics &amp; Participant Care Architecture
                </p>
              </div>
            </div>
          </footer>
        </ToastProvider>
      </body>
    </html>
  );
}
