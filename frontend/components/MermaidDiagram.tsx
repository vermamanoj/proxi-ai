import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, X } from 'lucide-react';

interface MermaidDiagramProps {
  chart: string;
}

// Track rendered diagrams as data URLs to avoid re-rendering
const renderedCache = new Map<string, string>();

/**
 * Sanitize mermaid syntax to fix common LLM output issues.
 * Only cleans parentheses INSIDE quoted strings (edge labels),
 * preserves valid mermaid node syntax like A(rounded) or B((circle)).
 */
function sanitizeMermaidSyntax(chart: string): string {
  // Replace parentheses only inside double-quoted strings (edge labels)
  // Match: "..." and replace ( with - and remove )
  return chart.replace(/"([^"]+)"/g, (match, content) => {
    const cleaned = content
      .replace(/\(/g, ' - ')  // Replace ( with -
      .replace(/\)/g, '')     // Remove )
      .replace(/\s+/g, ' ')   // Collapse multiple spaces
      .trim();
    return `"${cleaned}"`;
  });
}

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#6366f1',
    primaryTextColor: '#fff',
    primaryBorderColor: '#4f46e5',
    lineColor: '#6366f1',
    secondaryColor: '#1e1b4b',
    tertiaryColor: '#312e81',
    background: '#0f0f0f',
    mainBkg: '#1a1a2e',
    nodeBorder: '#4f46e5',
    clusterBkg: '#1a1a2e',
    clusterBorder: '#4f46e5',
    titleColor: '#fff',
    edgeLabelBackground: '#1a1a2e',
  },
  flowchart: {
    curve: 'basis',
    padding: 15,
  },
  sequence: {
    actorMargin: 50,
    boxMargin: 10,
    boxTextMargin: 5,
  },
});

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [imageUrl, setImageUrl] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isZoomed, setIsZoomed] = useState(false);
  
  // Stable ID based on chart content hash to prevent re-renders
  const chartId = useMemo(() => {
    const trimmed = chart?.trim() || '';
    let hash = 0;
    for (let i = 0; i < trimmed.length; i++) {
      hash = ((hash << 5) - hash) + trimmed.charCodeAt(i);
      hash |= 0;
    }
    return `mermaid-${Math.abs(hash).toString(36)}`;
  }, [chart]);

  // Convert SVG string to data URL for stable image rendering
  const svgToDataUrl = useCallback((svgString: string): string => {
    const encoded = encodeURIComponent(svgString)
      .replace(/'/g, '%27')
      .replace(/"/g, '%22');
    return `data:image/svg+xml,${encoded}`;
  }, []);

  useEffect(() => {
    const renderDiagram = async () => {
      const trimmed = chart?.trim();
      if (!trimmed) return;

      // Sanitize LLM output to fix common syntax issues
      const sanitized = sanitizeMermaidSyntax(trimmed);

      // Check cache first to prevent flickering
      const cached = renderedCache.get(sanitized);
      if (cached) {
        setImageUrl(cached);
        setError(null);
        return;
      }

      try {
        const { svg } = await mermaid.render(chartId, sanitized);
        const dataUrl = svgToDataUrl(svg);
        renderedCache.set(sanitized, dataUrl);
        setImageUrl(dataUrl);
        setError(null);
      } catch (err) {
        console.error('Mermaid render error:', err);
        setError('Failed to render diagram');
      } finally {
        // Clean up orphaned mermaid elements
        document.querySelectorAll('div[id^="dmermaid-"], div[id^="mermaid-"]').forEach(el => {
          if (el.parentElement === document.body) {
            el.remove();
          }
        });
      }
    };

    renderDiagram();
  }, [chart, chartId, svgToDataUrl]);

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-xs">
        <span className="font-semibold">Diagram Error:</span> {error}
        <pre className="mt-2 text-xs opacity-70 overflow-x-auto">{chart}</pre>
      </div>
    );
  }

  if (!imageUrl) {
    return (
      <div className="my-3 p-4 bg-black/30 rounded-lg flex items-center justify-center h-24">
        <div className="w-5 h-5 border-2 border-proxi-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      {/* Diagram thumbnail with zoom button */}
      <div 
        ref={containerRef}
        className="my-3 p-4 bg-black/30 rounded-lg overflow-x-auto relative group cursor-pointer"
        onClick={() => setIsZoomed(true)}
      >
        <img 
          src={imageUrl} 
          alt="Mermaid Diagram" 
          className="max-w-full h-auto"
          style={{ minHeight: '80px' }}
        />
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="p-1.5 bg-gray-800/80 rounded text-gray-300 text-xs flex items-center gap-1">
            <ZoomIn className="w-3 h-3" />
            Click to zoom
          </div>
        </div>
      </div>

      {/* Fullscreen zoom modal */}
      {isZoomed && (
        <div 
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4"
          onClick={() => setIsZoomed(false)}
        >
          <button
            className="absolute top-4 right-4 p-2 bg-gray-800 hover:bg-gray-700 rounded-full text-white transition-colors"
            onClick={() => setIsZoomed(false)}
          >
            <X className="w-6 h-6" />
          </button>
          <img 
            src={imageUrl} 
            alt="Mermaid Diagram (Zoomed)" 
            className="max-w-[95vw] max-h-[95vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
};
