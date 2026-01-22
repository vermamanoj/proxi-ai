import React, { useRef, useEffect } from 'react';

interface VisualizerProps {
  active: boolean; // If true, we simulate waveform movement
}

export const Visualizer: React.FC<VisualizerProps> = ({ active }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let offset = 0;
    let time = 0;

    const draw = () => {
      // Resize
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      // Cyberpunk Grid Background
      ctx.strokeStyle = '#1a1a1a';
      ctx.lineWidth = 1;
      const gridSize = 20;
      
      // Vertical lines
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      
      // Horizontal lines
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      if (active) {
        time += 0.1;
        // Simulate speech syllables using sine waves modulated by time
        const speechModulation = Math.abs(Math.sin(time)) * 0.5 + 0.5;
        const simulatedVolume = 0.5 * speechModulation + (Math.random() * 0.1);
        
        // Waveform
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        
        const amplitude = 35 * simulatedVolume; 
        
        for (let x = 0; x < width; x++) {
          // Combined sine waves for techy look
          const y = centerY + 
            Math.sin((x + offset) * 0.05) * amplitude * Math.sin((x + offset) * 0.01) +
            Math.sin((x - offset * 2) * 0.1) * (amplitude * 0.5);
          ctx.lineTo(x, y);
        }

        // Hacker Green Color Scheme
        ctx.strokeStyle = '#00ff41';
        ctx.lineWidth = 2;
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#00ff41';
        ctx.stroke();

        // Secondary line
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        for (let x = 0; x < width; x++) {
           const y = centerY + Math.cos((x - offset) * 0.05) * (amplitude * 0.7);
           ctx.lineTo(x, y);
        }
        ctx.strokeStyle = '#008F11'; // Darker green
        ctx.lineWidth = 1;
        ctx.shadowColor = '#008F11';
        ctx.stroke();
        
        offset += 5; 
      } else {
        // Idle line
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.strokeStyle = '#222';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [active]);

  return <canvas ref={canvasRef} className="w-full h-full" />;
};