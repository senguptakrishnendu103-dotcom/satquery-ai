import React, { useEffect, useRef, useState } from 'react';

export const LiveSpaceBackground: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isReducedMotion, setIsReducedMotion] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Smooth mouse tracker for gentle, unified stage movement (NO layer separation)
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setIsReducedMotion(mediaQuery.matches);
    const mediaHandler = (e: MediaQueryListEvent) => setIsReducedMotion(e.matches);
    mediaQuery.addEventListener('change', mediaHandler);

    const handleMouseMove = (e: MouseEvent) => {
      if (isReducedMotion) return;
      const x = (e.clientX / window.innerWidth - 0.5) * 32; // wider parallax range
      const y = (e.clientY / window.innerHeight - 0.5) * 32;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      mediaQuery.removeEventListener('change', mediaHandler);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isReducedMotion]);

  // Twinkling Starfield Particle Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const stars = Array.from({ length: 40 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random(),
      speed: Math.random() * 0.015 + 0.005,
      vy: -(Math.random() * 0.1 + 0.03),
      color: Math.random() > 0.4 ? '#38BDF8' : (Math.random() > 0.5 ? '#F59E0B' : '#FFFFFF')
    }));

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      stars.forEach((star) => {
        star.alpha += star.speed;
        if (star.alpha > 1 || star.alpha < 0.1) {
          star.speed = -star.speed;
        }

        star.y += star.vy;
        if (star.y < 0) {
          star.y = height;
          star.x = Math.random() * width;
        }

        ctx.save();
        ctx.globalAlpha = Math.max(0.1, Math.min(1, star.alpha));
        ctx.fillStyle = star.color;
        ctx.shadowBlur = star.radius * 3;
        ctx.shadowColor = star.color;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none">

      {/* Ambient Drift Layer: purely CSS-driven (animate-cosmicDrift keyframes).
          This element owns `transform` exclusively so the animation is never
          interrupted or overwritten by the inline mouse-parallax below. */}
      <div className="absolute inset-0 animate-cosmicDrift" style={{ willChange: 'transform' }}>

        {/* Mouse Parallax Layer: purely JS-driven inline transform. Nested
            inside the drift layer so the two transforms compose visually
            instead of competing for the same `transform` property. */}
        <div
          className="absolute inset-0 transition-transform duration-300 ease-out"
          style={{
            transform: isReducedMotion
              ? 'none'
              : `translate3d(${mousePos.x}px, ${mousePos.y}px, 0)`,
            willChange: 'transform'
          }}
        >
          {/* Layer 1: Full-Bleed Deep Space Galaxy Background Image */}
          <div
            className="absolute inset-0 bg-cover bg-center bg-no-repeat pointer-events-none"
            style={{
              backgroundImage: `url('/galaxy_space_bg.png')`,
              opacity: 0.90
            }}
          />

          {/* Layer 2: Photorealistic Celestial Earth Layer (Locked in sync) */}
          <div
            className="absolute top-0 bottom-0 left-0 w-full md:w-3/5 bg-no-repeat bg-left-center bg-contain pointer-events-none opacity-80"
            style={{
              backgroundImage: `url('/celestial_earth.png')`,
              backgroundPosition: 'left 5% center'
            }}
          />

          {/* Layer 3: Scientific Grid Isolines & Degree Tickers (Locked in sync) */}
          <svg
            className="w-full h-full stroke-sat-accent/40 fill-none absolute inset-0 pointer-events-none"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="none"
          >
            <defs>
              <pattern id="cozyGrid" width="60" height="60" patternUnits="userSpaceOnUse">
                <path d="M 60 0 L 0 0 0 60" fill="none" stroke="currentColor" strokeWidth="0.75" strokeOpacity="0.2" strokeDasharray="2 4" />
                <circle cx="0" cy="0" r="1.5" fill="currentColor" fillOpacity="0.3" />
                <circle cx="60" cy="0" r="1.5" fill="currentColor" fillOpacity="0.3" />
              </pattern>
            </defs>

            {/* Global Coordinate Grid */}
            <rect width="100%" height="100%" fill="url(#cozyGrid)" />

            {/* Contour Lines */}
            <g strokeWidth="1" strokeOpacity="0.3" strokeDasharray="6 3">
              <path d="M -100 150 Q 200 80, 500 220 T 1100 180 T 1800 280" />
              <path d="M -100 450 Q 350 320, 800 520 T 1500 420 T 2000 580" strokeWidth="1.5" strokeOpacity="0.4" />
              <path d="M -100 700 Q 400 600, 950 780 T 1600 680 T 2100 820" />
            </g>

            {/* Latitude & Longitude Tickers */}
            <g className="font-mono text-[9px] fill-sat-accent stroke-none opacity-60">
              <text x="40" y="80">LAT 45.0000° N</text>
              <text x="40" y="320">LAT 30.0000° N</text>
              <text x="40" y="560">LAT 15.0000° N</text>

              <text x="500" y="30">LON 30.0000° E</text>
              <text x="1000" y="30">LON 60.0000° E</text>
              <text x="1500" y="30">LON 90.0000° E</text>
            </g>
          </svg>
        </div>
      </div>

      {/* Layer 4: Twinkling Star Particle Canvas (Overlay) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none opacity-80"
      />

      {/* Layer 5: Vignette Contrast Overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/35 via-transparent to-black/45 pointer-events-none" />

      {/* Layer 6: Cozy Warm Glow — only visible in light mode.
          .cozy-glow's background-image is defined solely under html.light in
          index.css, so in dark mode this div paints nothing and is invisible. */}
      <div className="cozy-glow absolute inset-0 pointer-events-none" />

    </div>
  );
};