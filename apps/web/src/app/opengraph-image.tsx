import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'Gatekeeper - Intel & Route Planning for EVE Online';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'linear-gradient(135deg, #0a0e17 0%, #0f1729 40%, #162032 70%, #0e2a3d 100%)',
          fontFamily: 'system-ui, sans-serif',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Grid overlay */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            opacity: 0.06,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }}
        />

        {/* Glow accent */}
        <div
          style={{
            position: 'absolute',
            top: '-120px',
            right: '-80px',
            width: '500px',
            height: '500px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(14,116,144,0.25) 0%, transparent 70%)',
            display: 'flex',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-100px',
            left: '-60px',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(6,182,212,0.15) 0%, transparent 70%)',
            display: 'flex',
          }}
        />

        {/* Title */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            zIndex: 1,
          }}
        >
          <div
            style={{
              fontSize: '72px',
              fontWeight: 800,
              color: '#ffffff',
              letterSpacing: '-2px',
              display: 'flex',
            }}
          >
            GATEKEEPER
          </div>
          <div
            style={{
              fontSize: '28px',
              fontWeight: 500,
              color: '#94a3b8',
              letterSpacing: '4px',
              textTransform: 'uppercase',
              display: 'flex',
            }}
          >
            Intel &amp; Route Planning
          </div>

          {/* Divider */}
          <div
            style={{
              width: '120px',
              height: '3px',
              background: 'linear-gradient(90deg, transparent, #0e7490, transparent)',
              borderRadius: '2px',
              marginTop: '8px',
              marginBottom: '8px',
              display: 'flex',
            }}
          />

          {/* Features row */}
          <div
            style={{
              display: 'flex',
              gap: '40px',
              fontSize: '18px',
              color: '#64748b',
              fontWeight: 500,
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#06b6d4', display: 'flex' }}>&#9679;</span> Universe Map
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#06b6d4', display: 'flex' }}>&#9679;</span> Kill Intel
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#06b6d4', display: 'flex' }}>&#9679;</span> Route Planner
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#06b6d4', display: 'flex' }}>&#9679;</span> Threat Analysis
            </span>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: 'absolute',
            bottom: '0',
            left: '0',
            right: '0',
            height: '56px',
            background: 'rgba(0,0,0,0.4)',
            borderTop: '1px solid rgba(14,116,144,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            fontSize: '18px',
            color: '#64748b',
          }}
        >
          <span style={{ color: '#0e7490', fontWeight: 700, display: 'flex' }}>edengk.com</span>
          <span style={{ display: 'flex' }}>|</span>
          <span style={{ display: 'flex' }}>For EVE Online Pilots</span>
        </div>
      </div>
    ),
    { ...size }
  );
}
