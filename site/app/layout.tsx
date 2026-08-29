import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://evar-research.elitelab-ai.chatgpt.site'),
  title: 'EVAR — Evidence-Verified Adversarial Review',
  description:
    'A research harness testing whether deterministic evidence verification can reduce false consensus in AI code review.',
  openGraph: {
    title: 'EVAR — Agreement is not evidence',
    description: 'Executable evidence for more reliable reviewer–critic code review.',
    type: 'website',
    images: ['/og.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EVAR — Agreement is not evidence',
    description: 'Executable evidence for more reliable reviewer–critic code review.',
    images: ['/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
