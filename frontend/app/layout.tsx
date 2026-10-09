import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'ProjectEval — evaluate at scale', description: 'Fair, evidence-based project evaluation for teams and cohorts.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
