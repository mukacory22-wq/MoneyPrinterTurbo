import React from 'react';
import type {AppIcon} from '../types';

const COLORS: Record<AppIcon, string> = {
  whatsapp: '#25D366',
  calendar: '#3B82F6',
  pix: '#2FB7A8',
  alarm: '#F2674A',
  ai: '#E0795A',
  mic: '#4C8DFF',
  maps: '#34A853',
  sheets: '#1FA463',
  instagram: '#D6336C',
  bell: '#5B616B',
  generic: '#5B616B',
};

const stroke = {fill: 'none', stroke: '#fff', strokeWidth: 2.2, strokeLinecap: 'round', strokeLinejoin: 'round'} as const;

/** Glifos simples e genéricos (viewBox 24x24), sem logotipos de marcas. */
const GLYPHS: Record<AppIcon, React.ReactNode> = {
  whatsapp: (
    <>
      <path {...stroke} d="M12 3.5a8.5 8.5 0 0 0-7.3 12.8L3.5 20.5l4.3-1.1A8.5 8.5 0 1 0 12 3.5z" />
      <path {...stroke} strokeWidth={1.8} d="M9.2 8.6c-.4 2.6 2.6 5.8 5.6 6.1.7 0 1.3-.5 1.5-1.1l-1.7-1-.9.8c-1-.4-2-1.4-2.5-2.4l.8-.9-1-1.8c-.7.1-1.6.6-1.8 1.3z" />
    </>
  ),
  calendar: (
    <>
      <rect {...stroke} x="4" y="5.5" width="16" height="14" rx="3" />
      <path {...stroke} d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </>
  ),
  pix: <path {...stroke} d="M12 3.8l8.2 8.2-8.2 8.2L3.8 12zM8 8l4 4 4-4M8 16l4-4 4 4" />,
  alarm: (
    <>
      <circle {...stroke} cx="12" cy="13" r="7" />
      <path {...stroke} d="M12 9.5V13l2.5 1.5M5 4.5L3 6.5M19 4.5l2 2" />
    </>
  ),
  ai: <path fill="#fff" d="M12 2.5l1.9 6.1 6.1 1.9-6.1 1.9L12 18.5l-1.9-6.1L4 10.5l6.1-1.9zM18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" />,
  mic: (
    <>
      <rect {...stroke} x="9" y="3.5" width="6" height="10.5" rx="3" />
      <path {...stroke} d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
    </>
  ),
  maps: (
    <>
      <path {...stroke} d="M12 21s6.5-6.2 6.5-11A6.5 6.5 0 0 0 5.5 10c0 4.8 6.5 11 6.5 11z" />
      <circle {...stroke} cx="12" cy="10" r="2.3" />
    </>
  ),
  sheets: (
    <>
      <rect {...stroke} x="4.5" y="4" width="15" height="16" rx="2.5" />
      <path {...stroke} d="M4.5 9.5h15M4.5 14.5h15M10 9.5V20" />
    </>
  ),
  instagram: (
    <>
      <rect {...stroke} x="4" y="4" width="16" height="16" rx="5" />
      <circle {...stroke} cx="12" cy="12" r="3.6" />
      <circle fill="#fff" cx="16.7" cy="7.3" r="1.1" />
    </>
  ),
  bell: <path {...stroke} d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15zM10 20.5h4" />,
  generic: <circle fill="#fff" cx="12" cy="12" r="4" />,
};

export const iconColor = (icon: AppIcon): string => COLORS[icon];

/** Ícone de app: quadrado arredondado colorido com glifo branco. */
export const AppIconBadge: React.FC<{icon: AppIcon; size?: number; dim?: number}> = ({
  icon, size = 56, dim = 0,
}) => (
  <div
    style={{
      width: size,
      height: size,
      flexShrink: 0,
      borderRadius: size * 0.27,
      background: COLORS[icon],
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      filter: dim ? `saturate(${1 - dim}) brightness(${1 - 0.45 * dim})` : undefined,
      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.3)',
    }}
  >
    <svg viewBox="0 0 24 24" width={size * 0.64} height={size * 0.64}>
      {GLYPHS[icon]}
    </svg>
  </div>
);

export const CheckIcon: React.FC<{size?: number; color?: string}> = ({size = 24, color = '#fff'}) => (
  <svg viewBox="0 0 24 24" width={size} height={size}>
    <path fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);
