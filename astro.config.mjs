// @ts-check

import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://civilservicejobs.co',  // Replace with your domain for sitemap
  integrations: [sitemap(), tailwind()],
});