import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://evar-research.elitelab-ai.chatgpt.site'),
  title: 'EVAR — Evidence-Verified Adversarial Review',
  description:
    'Audited evidence from 720 code-review decisions, including an untouched holdout built from real human pull-request comments.',
  openGraph: {
    title: 'EVAR — Agreement is not evidence',
    description: 'Untouched result: auditable verification, but no performance advantage over the stronger text-evidence baseline.',
    type: 'website',
    images: ['/og.png'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EVAR — Agreement is not evidence',
    description: 'Untouched result: auditable verification, but no performance advantage over the stronger text-evidence baseline.',
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
