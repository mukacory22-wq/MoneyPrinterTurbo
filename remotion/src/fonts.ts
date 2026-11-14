import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/instrument-serif/400-italic.css';
import '@fontsource/caveat/500.css';
import {continueRender, delayRender} from 'remotion';

/** Garante que as fontes embutidas estejam carregadas antes do primeiro quadro. */
export const loadFonts = (): void => {
  if (typeof document === 'undefined') return;
  const handle = delayRender('Carregando fontes');
  const sample = 'AÁÇãõ 0123 R$';
  Promise.all([
    document.fonts.load("400 20px 'Inter'", sample),
    document.fonts.load("500 20px 'Inter'", sample),
    document.fonts.load("600 20px 'Inter'", sample),
    document.fonts.load("700 20px 'Inter'", sample),
    document.fonts.load("italic 400 20px 'Instrument Serif'", sample),
    document.fonts.load("500 20px 'Caveat'", sample),
  ])
    .catch(() => undefined)
    .then(() => continueRender(handle));
};
