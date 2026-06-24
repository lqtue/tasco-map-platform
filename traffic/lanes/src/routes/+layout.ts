// Pure client-side SPA: it calls the Overpass API directly from the browser
// and uses Leaflet for the map, so we disable SSR and prerender a shell.
export const ssr = false;
export const prerender = true;
