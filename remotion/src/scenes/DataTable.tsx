import React from 'react';
import {useCurrentFrame} from 'remotion';
import {z} from 'zod';
import {Panel3D} from '../fx/Panel3D';
import {actionFrame} from '../lib/actions';
import {AppIconBadge} from '../lib/icons';
import {theme} from '../theme';
import type {SceneProps} from '../types';

export const schema = z.strictObject({
  title: z.string(),
  columns: z.array(z.string()),
  rows: z.array(z.strictObject({id: z.string().min(1), cells: z.array(z.string())})),
});
type Props = z.infer<typeof schema>;

const FRAMES_PER_CHAR = 1.5;

/** Planilha: as linhas existentes aparecem prontas; a linha-alvo é digitada célula a célula. */
export const DataTable: React.FC<SceneProps<Props>> = ({props, actions}) => {
  const frame = useCurrentFrame();
  const template = `repeat(${props.columns.length}, 1fr)`;
  return (
    <Panel3D width={920} padding={30}>
      <div style={{display: 'flex', alignItems: 'center', gap: 14, fontSize: 27, fontWeight: 700, marginBottom: 22}}>
        <AppIconBadge icon="sheets" size={40} />
        {props.title}
      </div>
      <div style={{display: 'grid', gridTemplateColumns: template, padding: '0 14px 12px', fontSize: 19, fontWeight: 600, color: theme.textDim, borderBottom: `1.5px solid ${theme.border}`}}>
        {props.columns.map((c, i) => <div key={i}>{c}</div>)}
      </div>
      {props.rows.map((row) => {
        const typeAt = actionFrame(actions, 'type', row.id);
        if (typeAt !== null && frame < typeAt) {
          return <div key={row.id} style={{height: 64, borderBottom: `1px solid ${theme.border}`}} />;
        }
        let budget = typeAt === null ? Infinity : Math.floor((frame - typeAt) / FRAMES_PER_CHAR);
        let cursorDrawn = false;
        return (
          <div key={row.id} style={{display: 'grid', gridTemplateColumns: template, alignItems: 'center', height: 64, padding: '0 14px', fontSize: 23, fontWeight: 500, borderBottom: `1px solid ${theme.border}`, background: typeAt !== null ? 'rgba(255,255,255,0.05)' : 'transparent'}}>
            {row.cells.map((cell, i) => {
              const shown = cell.slice(0, Math.max(0, Math.min(cell.length, budget)));
              const active = !cursorDrawn && typeAt !== null && budget >= 0 && budget < cell.length;
              budget -= cell.length;
              if (active) cursorDrawn = true;
              return (
                <div key={i} style={{boxSizing: 'border-box', height: 44, display: 'flex', alignItems: 'center', padding: '0 8px', marginLeft: -8, border: `2px solid ${active ? theme.blue : 'transparent'}`, borderRadius: 6}}>
                  {shown}
                </div>
              );
            })}
          </div>
        );
      })}
    </Panel3D>
  );
};
