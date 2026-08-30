import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://evar-research.elitelab-ai.chatgpt.site'),
  title: 'EVAR — Evidence-Verified Adversarial Review',
  description:
    'Frozen evidence from 600 code-review decisions testing how deterministic verification trades false-consensus reduction for supported-claim retention.',
  openGraph: {
    title: 'EVAR — Agreement is not evidence',
    description: 'Frozen results: less false consensus, with a measurable supported-claim retention cost.',
    type: 'website',
    images: ['/og.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EVAR — Agreement is not evidence',
    description: 'Frozen results: less false consensus, with a measurable supported-claim retention cost.',
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
