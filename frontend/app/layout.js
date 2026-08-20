import './globals.css';

export const metadata = {
  title: 'Myntra Wishlist AI Discovery Engine — PM Analytics Platform',
  description: 'Evidence-backed Voice of Customer (VoC) Intelligence Engine diagnosing 30-day wishlist conversion drop-offs without monetary incentives.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0d0e12] text-gray-100 antialiased selection:bg-[#ff3f6c] selection:text-white">
        {children}
      </body>
    </html>
  );
}
