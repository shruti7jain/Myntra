import './globals.css';

export const metadata = {
  title: 'Myntra Wishlist AI Discovery Engine — PM Analytics Platform',
  description: 'Evidence-backed Voice of Customer (VoC) Intelligence Engine diagnosing 30-day wishlist conversion drop-offs without monetary incentives.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f8f9fb] text-[#282c3f] antialiased selection:bg-[#ff3f6c] selection:text-white">
        {children}
      </body>
    </html>
  );
}
