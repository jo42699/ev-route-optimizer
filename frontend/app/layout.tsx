import type { Metadata } from 'next';
import 'leaflet/dist/leaflet.css';
import './globals.css';
import { JourneyProvider } from '@/lib/journey-context';
export const metadata: Metadata = {title:'ChargeSmart — Smarter routes. Greener journeys.', description:'Find your next charging stop with transparent EV route recommendations.'};
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body><JourneyProvider>{children}</JourneyProvider></body></html>; }
