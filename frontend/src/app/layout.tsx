import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '@/components/Navbar';

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
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
          <p className="max-w-2xl mx-auto italic mb-1">
            &ldquo;A participant&rsquo;s agreement to one use must never automatically become agreement to another use. Silence is never agreement.&rdquo;
          </p>
          <p>&copy; 2026 SceneSteward. Documentary Ethics &amp; Participant Care Architecture.</p>
        </footer>
      </body>
    </html>
  );
}
