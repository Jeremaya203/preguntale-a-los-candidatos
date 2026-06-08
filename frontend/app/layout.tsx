import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Pregúntale a los Candidatos · Colombia 2026',
  description: 'Plataforma ciudadana de análisis y comparación de propuestas electorales en Colombia.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="scanlines">{children}</body>
    </html>
  );
}
