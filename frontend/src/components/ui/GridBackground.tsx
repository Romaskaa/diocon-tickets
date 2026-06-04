import React from 'react';

interface GridBackgroundProps {
  variant?: 'dots' | 'grid' | 'lines';
  opacity?: number;
}

const GridBackground: React.FC<GridBackgroundProps> = ({ variant = 'dots', opacity = 1 }) => {
  if (variant === 'dots') {
    return (
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          opacity: 0.35 * opacity,
          backgroundImage: 'radial-gradient(circle, var(--dot-color) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, black 30%, transparent 100%)',
        }}
      />
    );
  }
  if (variant === 'grid') {
    return (
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          opacity: 0.18 * opacity,
          backgroundImage: `
            linear-gradient(to right, var(--grid-color) 1px, transparent 1px),
            linear-gradient(to bottom, var(--grid-color) 1px, transparent 1px)
          `,
          backgroundSize: '32px 32px',
          maskImage: 'radial-gradient(ellipse 70% 50% at 50% 50%, black 40%, transparent 100%)',
          WebkitMaskImage: 'radial-gradient(ellipse 70% 50% at 50% 50%, black 40%, transparent 100%)',
        }}
      />
    );
  }
  return null;
};

export default GridBackground;
