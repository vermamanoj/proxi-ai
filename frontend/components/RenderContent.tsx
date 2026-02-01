import React from 'react';
import { MermaidDiagram } from './MermaidDiagram';

interface RenderContentProps {
  content: string | unknown;
}

/**
 * Renders content with special handling for:
 * - Mermaid diagrams (```mermaid ... ```)
 * - ATTACK_PATH_DIAGRAM blocks
 * - Plain text
 */
export const RenderContent: React.FC<RenderContentProps> = ({ content }) => {
  if (typeof content !== 'string') {
    return <>{JSON.stringify(content)}</>;
  }

  // Check for mermaid code blocks
  const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  // Also handle ATTACK_PATH_DIAGRAM: prefix
  let processedContent = content;
  if (content.includes('ATTACK_PATH_DIAGRAM:')) {
    processedContent = content.replace('ATTACK_PATH_DIAGRAM:', '').trim();
  }

  while ((match = mermaidRegex.exec(processedContent)) !== null) {
    // Add text before the mermaid block
    if (match.index > lastIndex) {
      const textBefore = processedContent.slice(lastIndex, match.index).trim();
      if (textBefore) {
        parts.push(<span key={`text-${lastIndex}`}>{textBefore}</span>);
      }
    }

    // Add the mermaid diagram
    const mermaidCode = match[1].trim();
    parts.push(
      <MermaidDiagram key={`mermaid-${match.index}`} chart={mermaidCode} />
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last mermaid block
  if (lastIndex < processedContent.length) {
    const remaining = processedContent.slice(lastIndex).trim();
    if (remaining) {
      // Filter out "MERMAID_DIAGRAM_RENDERED" placeholder text
      const filtered = remaining.replace(/MERMAID_DIAGRAM_RENDERED/g, '').trim();
      if (filtered) {
        parts.push(<span key={`text-${lastIndex}`}>{filtered}</span>);
      }
    }
  }

  // If no mermaid found, return original content (minus placeholders)
  if (parts.length === 0) {
    const cleaned = content.replace(/MERMAID_DIAGRAM_RENDERED/g, '').trim();
    return <>{cleaned || content}</>;
  }

  return <>{parts}</>;
};

export default RenderContent;
