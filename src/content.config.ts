import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const songSchema = z.object({
  title: z.string(),
  audio: z.string(),
  lrc: z.string().optional(),
  duration: z.number().optional(),
});

const albums = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/albums' }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    year: z.number(),
    cover: z.string(),
    bgColor: z.string().default('#0b0a08'),
    accentColor: z.string().default('#c9a35a'),
    description: z.string().optional(),
    songs: z.array(songSchema),
    artist: z.string().default('JiangJingyi'),
    producedBy: z.string().default('SUNO'),
  }),
});

export const collections = { albums };
