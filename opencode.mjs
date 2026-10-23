// OpenCode v2 adapter; public skills keep their original package-relative files.
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = new URL('./', import.meta.url);
const manifest = JSON.parse(readFileSync(new URL('plugin.json', root), 'utf8'));

export default {
  id: `gx-marketplace.${manifest.name}`,
  async setup(ctx) {
    const skills = readdirSync(new URL('skills/', root), { withFileTypes: true })
      .filter(entry => entry.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))
      .map(entry => {
        const url = new URL(`skills/${entry.name}/SKILL.md`, root);
        const text = readFileSync(url, 'utf8');
        const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/.exec(text);
        const description = /^description: (.+)$/m.exec(frontmatter?.[1] ?? '')?.[1];
        if (!description) throw new Error(`Missing description for ${manifest.name}:${entry.name}`);
        return {
          id: `${manifest.name}-${entry.name}`, name: `${manifest.name}:${entry.name}`,
          description, path: fileURLToPath(url), content: text.slice(frontmatter[0].length),
          autoinvoke: true,
        };
      });
    const registration = await ctx.skill.transform(editor => {
      for (const skill of skills) editor.add(skill);
    });
    return () => registration.dispose();
  },
};
