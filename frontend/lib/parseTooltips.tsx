import { Fragment } from "react";
import { LegalTooltip } from "@/components/LegalTooltip";

/**
 * Convierte texto con {{término::explicación}} en JSX, reemplazando cada
 * marca por un <LegalTooltip>. El texto restante se conserva tal cual
 * (incluidos los saltos de línea, que el contenedor renderiza con pre-wrap).
 *
 * Tolerante con el streaming: una marca incompleta como "{{tutela::expli"
 * (sin cierre) simplemente no coincide y se muestra como texto plano hasta
 * que llegan las llaves de cierre.
 */
export function parseTooltips(text: string): React.ReactNode[] {
  const PATTERN = /\{\{([^:]+)::([^}]+)\}\}/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<Fragment key={key++}>{text.slice(lastIndex, match.index)}</Fragment>);
    }
    parts.push(
      <LegalTooltip key={key++} term={match[1].trim()} explanation={match[2].trim()} />
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>);
  }

  return parts;
}
