"use client";
import { useState, useRef, useEffect } from "react";

interface LegalTooltipProps {
  term: string;
  explanation: string;
}

// Ámbar: contrasta sobre fondo oscuro sin chocar con el naranja del jaguar
// (#F0A020) ni el del tigre (#E05818).
const AMBER = "#F59E0B";

export function LegalTooltip({ term, explanation }: LegalTooltipProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  // Cerrar al hacer clic fuera o con Escape
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span ref={ref} style={{ position: "relative", display: "inline-block" }}>
      <button
        onClick={() => setOpen(v => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        style={{
          fontWeight: 600,
          color: AMBER,
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
          textDecoration: "underline",
          textDecorationStyle: "dotted",
          textUnderlineOffset: "2px",
          font: "inherit",
        }}
      >
        {term}
      </button>

      {open && (
        <span
          role="dialog"
          aria-label={`Explicación: ${term}`}
          className="fade-up"
          style={{
            position: "absolute",
            zIndex: 100,
            bottom: "100%",
            left: 0,
            marginBottom: 8,
            width: "min(18rem, 80vw)",
            background: "#0E0E1A",
            border: `1px solid ${AMBER}66`,
            borderRadius: 8,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            padding: "10px 14px",
            fontSize: "12px",
            lineHeight: 1.5,
            color: "#C8C8D4",
            whiteSpace: "normal",
            textAlign: "left",
          }}
        >
          <span
            style={{
              display: "block",
              fontFamily: "var(--pixel)",
              fontSize: "5px",
              letterSpacing: "0.1em",
              color: AMBER,
              marginBottom: 6,
            }}
          >
            ¿QUÉ ES ESTO?
          </span>
          {explanation}
        </span>
      )}
    </span>
  );
}
