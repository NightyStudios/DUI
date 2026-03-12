import { useEffect, useMemo, useRef, useState } from 'react';

import { getMathJax, loadMathJax } from './mathJax';

function wrapFormula(rawFormula: string): string {
  const formula = rawFormula.trim();
  if (formula.startsWith('\\(') || formula.startsWith('\\[') || formula.startsWith('$$')) {
    return formula;
  }
  return `\\(${formula}\\)`;
}

export function MathFormulaList(props: { formulas: string[] }) {
  const { formulas } = props;
  const rootRef = useRef<HTMLUListElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const formulaSignature = useMemo(() => formulas.join('\u0000'), [formulas]);

  useEffect(() => {
    let cancelled = false;

    if (formulas.length === 0) {
      setStatus('ready');
      return () => {
        cancelled = true;
      };
    }

    setStatus('loading');
    void loadMathJax()
      .then((api) => {
        if (cancelled) {
          return;
        }
        if (api?.typesetPromise) {
          setStatus('ready');
          return;
        }
        setStatus('error');
      })
      .catch(() => {
        if (!cancelled) {
          setStatus('error');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [formulaSignature, formulas.length]);

  useEffect(() => {
    if (status !== 'ready' || !rootRef.current) {
      return;
    }

    const mathJax = getMathJax();
    if (!mathJax?.typesetPromise) {
      return;
    }

    mathJax.texReset?.();
    void mathJax.typesetPromise([rootRef.current]).catch(() => {
      setStatus('error');
    });

    return () => {
      mathJax.typesetClear?.([rootRef.current!]);
    };
  }, [formulaSignature, status]);

  return (
    <div className="math-formula-list-root">
      <ul ref={status === 'ready' ? rootRef : null} className="plain-list math-formula-list">
        {formulas.map((formula) => (
          <li key={formula}>
            {status === 'ready' ? (
              <span className="math-formula" aria-label={formula}>
                {wrapFormula(formula)}
              </span>
            ) : (
              <code className="math-formula-plain">{formula}</code>
            )}
          </li>
        ))}
      </ul>
      {status === 'loading' ? <p className="math-formula-status">Рендерим формулы…</p> : null}
      {status === 'error' ? <p className="math-formula-status">MathJax не загрузился, оставлен plain text.</p> : null}
    </div>
  );
}
