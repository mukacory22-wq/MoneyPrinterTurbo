import type {ResolvedAction} from '../types';

/** Ações que revelam um alvo: ele fica oculto até a ação acontecer. */
export const REVEAL_ACTIONS = new Set(['show', 'typing', 'comment', 'reveal', 'type']);

/** Quadro da primeira ação `doName` (opcionalmente para um alvo), ou null. */
export const actionFrame = (
  actions: ResolvedAction[],
  doName: string,
  target?: string,
): number | null => {
  const found = actions.find(
    (a) => a.do === doName && (target === undefined || a.target === target),
  );
  return found ? found.frame : null;
};

/** Quadro em que o alvo é revelado; null se ele está visível desde o início. */
export const revealFrame = (actions: ResolvedAction[], target: string): number | null => {
  const found = actions.find((a) => a.target === target && REVEAL_ACTIONS.has(a.do));
  return found ? found.frame : null;
};

export const isRevealed = (actions: ResolvedAction[], target: string, frame: number): boolean => {
  const at = revealFrame(actions, target);
  return at === null || frame >= at;
};
