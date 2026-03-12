interface MathJaxApi {
  startup?: {
    promise?: Promise<unknown>;
  };
  typesetPromise?: (elements?: HTMLElement[]) => Promise<unknown>;
  typesetClear?: (elements?: HTMLElement[]) => void;
  texReset?: () => void;
}

declare global {
  interface Window {
    MathJax?: MathJaxApi & {
      tex?: {
        inlineMath?: Array<[string, string]>;
        displayMath?: Array<[string, string]>;
      };
      svg?: {
        fontCache?: string;
      };
      options?: {
        skipHtmlTags?: string[];
      };
    };
  }
}

const MATHJAX_SCRIPT_ID = 'dui-mathjax-script';
const MATHJAX_SCRIPT_SRC = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js';

let mathJaxLoader: Promise<MathJaxApi | null> | null = null;

function readMathJax(): MathJaxApi | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.MathJax ?? null;
}

function configureMathJax(): void {
  if (typeof window === 'undefined') {
    return;
  }
  const current = window.MathJax ?? {};
  window.MathJax = {
    ...current,
    tex: {
      ...current.tex,
      inlineMath: current.tex?.inlineMath ?? [['\\(', '\\)'], ['$', '$']],
      displayMath: current.tex?.displayMath ?? [['\\[', '\\]'], ['$$', '$$']],
    },
    svg: {
      ...current.svg,
      fontCache: current.svg?.fontCache ?? 'global',
    },
    options: {
      ...current.options,
      skipHtmlTags: current.options?.skipHtmlTags ?? ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
    },
  };
}

function waitForStartup(api: MathJaxApi | null): Promise<MathJaxApi | null> {
  const startupPromise = api?.startup?.promise;
  if (!startupPromise) {
    return Promise.resolve(api);
  }
  return startupPromise.then(() => api);
}

export function loadMathJax(): Promise<MathJaxApi | null> {
  if (typeof window === 'undefined') {
    return Promise.resolve(null);
  }

  const existingApi = readMathJax();
  if (existingApi?.typesetPromise) {
    return waitForStartup(existingApi);
  }

  if (mathJaxLoader) {
    return mathJaxLoader;
  }

  mathJaxLoader = new Promise<MathJaxApi | null>((resolve, reject) => {
    configureMathJax();

    const resolveLoaded = () => {
      void waitForStartup(readMathJax()).then(resolve).catch(reject);
    };

    const handleError = () => {
      mathJaxLoader = null;
      reject(new Error('MathJax failed to load.'));
    };

    const existingScript = document.getElementById(MATHJAX_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener('load', resolveLoaded, { once: true });
      existingScript.addEventListener('error', handleError, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = MATHJAX_SCRIPT_ID;
    script.async = true;
    script.src = MATHJAX_SCRIPT_SRC;
    script.addEventListener('load', resolveLoaded, { once: true });
    script.addEventListener('error', handleError, { once: true });
    document.head.appendChild(script);
  });

  return mathJaxLoader;
}

export function getMathJax(): MathJaxApi | null {
  return readMathJax();
}
