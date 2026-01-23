import React, { useRef, useEffect } from 'react';

interface VisualizerProps {
  active: boolean; // If true, the visualizer is "on"
  volume?: number; // Optional real-time volume (0.0 to 1.0)
}

export const Visualizer: React.FC<VisualizerProps> = ({ active, volume = 0 }) => {
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
        
        // Dynamic Amplitude:
        // If we have real volume, use it. Otherwise, simulate a "thinking/speaking" idle wave if active.
        // We boost the volume significantly for visual impact.
        const inputAmplitude = volume * 500; 
        
        // Base simulation (keeps it moving even during silence)
        const simulatedAmplitude = Math.abs(Math.sin(time)) * 10 + 5;
        
        // Blend them: Real volume takes precedence for spikes
        const amplitude = Math.max(inputAmplitude, simulatedAmplitude);
        
        // Color shifts based on intensity
        const intensity = Math.min(volume * 2, 1);
        const r = 0;
        const g = 255;
        const b = Math.floor(intensity * 255); // Shift to cyan on loud
        const color = `rgb(${r},${g},${b})`;

        // Primary Waveform
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        
        for (let x = 0; x < width; x++) {
          // Complex wave synthesis
          const y = centerY + 
            Math.sin((x + offset) * 0.05) * amplitude * Math.sin((x + offset) * 0.01) +
            Math.sin((x - offset * 2) * 0.1) * (amplitude * 0.5);
          ctx.lineTo(x, y);
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 2 + (intensity * 2); // Thicker line when loud
        ctx.shadowBlur = 10 + (intensity * 10);
        ctx.shadowColor = color;
        ctx.stroke();

        // Secondary "Ghost" line (Echo)
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        for (let x = 0; x < width; x++) {
           const y = centerY + Math.cos((x - offset) * 0.05) * (amplitude * 0.7);
           ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'rgba(0, 143, 17, 0.5)'; 
        ctx.lineWidth = 1;
        ctx.stroke();
        
        offset += 5 + (intensity * 5); // Speed up when loud
      } else {
        // Flatline (Standby)
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
  }, [active, volume]);

  return <canvas ref={canvasRef} className="w-full h-full" />;
};