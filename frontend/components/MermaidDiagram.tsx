import React, { useEffect, useRef, useState, useMemo } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
}

// Track rendered diagrams to avoid re-rendering same content
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
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  
  // Stable ID based on chart content hash to prevent re-renders
  const chartId = useMemo(() => {
    const trimmed = chart?.trim() || '';
    // Simple hash for stable ID
    let hash = 0;
    for (let i = 0; i < trimmed.length; i++) {
      hash = ((hash << 5) - hash) + trimmed.charCodeAt(i);
      hash |= 0;
    }
    return `mermaid-${Math.abs(hash).toString(36)}`;
  }, [chart]);

  useEffect(() => {
    const renderDiagram = async () => {
      const trimmed = chart?.trim();
      if (!trimmed || !containerRef.current) return;

      // Sanitize LLM output to fix common syntax issues
      const sanitized = sanitizeMermaidSyntax(trimmed);

      // Check cache first to prevent flickering
      const cached = renderedCache.get(sanitized);
      if (cached) {
        setSvg(cached);
        setError(null);
        return;
      }

      try {
        const { svg } = await mermaid.render(chartId, sanitized);
        renderedCache.set(sanitized, svg);
        setSvg(svg);
        setError(null);
      } catch (err) {
        console.error('Mermaid render error:', err);
        setError('Failed to render diagram');
      }
    };

    renderDiagram();
  }, [chart, chartId]);

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-xs">
        <span className="font-semibold">Diagram Error:</span> {error}
        <pre className="mt-2 text-xs opacity-70 overflow-x-auto">{chart}</pre>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-3 p-4 bg-black/30 rounded-lg overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};
