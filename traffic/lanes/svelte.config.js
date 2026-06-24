import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter({
      fallback: 'index.html'
    }),
    // project Pages serve under /<repo>; CI sets BASE_PATH, local dev stays at ''
    paths: {
      base: process.env.BASE_PATH || ''
    }
  }
};

export default config;
