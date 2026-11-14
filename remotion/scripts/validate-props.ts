/**
 * Valida um arquivo de RenderProps (saída de timeline.build_render_props)
 * contra os schemas zod do Remotion. Uso: npm run validate -- caminho/props.json
 */
import {readFileSync} from 'node:fs';
import {REGISTRY} from '../src/registry';
import {renderPropsSchema} from '../src/types';

const file = process.argv[2];
if (!file) {
  console.error('uso: validate-props <props.json>');
  process.exit(2);
}

const errors: string[] = [];
const parsed = renderPropsSchema.safeParse(JSON.parse(readFileSync(file, 'utf-8')));
if (!parsed.success) {
  for (const issue of parsed.error.issues) {
    errors.push(`${issue.path.join('.') || '(raiz)'}: ${issue.message}`);
  }
} else {
  for (const scene of parsed.data.scenes) {
    const entry = REGISTRY[scene.component];
    if (!entry) {
      errors.push(`cena ${scene.id}: componente ${scene.component} ainda não implementado`);
      continue;
    }
    const result = entry.schema.safeParse(scene.props);
    if (!result.success) {
      for (const issue of result.error.issues) {
        errors.push(`cena ${scene.id}: props.${issue.path.join('.')}: ${issue.message}`);
      }
    }
    if (scene.component === 'Media' && !scene.media) {
      errors.push(`cena ${scene.id}: Media sem arquivo de mídia`);
    }
  }
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log(`ok: ${file}`);
