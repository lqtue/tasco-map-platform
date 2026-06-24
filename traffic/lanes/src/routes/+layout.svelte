<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/state';
  let { children } = $props();
  // strip the base prefix so the active check works under sub-path hosting
  const path = $derived(page.url.pathname.slice(base.length) || '/');
</script>

<nav class="nav">
  <span class="brand">TASCO MapOps Toolkit</span>
  <a href={`${base}/`} class:on={path === '/'}>Dashboard</a>
  <a href={`${base}/map`} class:on={path.startsWith('/map')}>Map</a>
  <a href={`${base}/editor`} class:on={path.startsWith('/editor')}>Editor</a>
</nav>

{@render children()}

<style>
  .nav {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 14px;
    margin-bottom: 10px;
    background: #1a5fb4;
    border-radius: 6px;
  }
  .brand {
    font-weight: 700;
    color: #fff;
    margin-right: 6px;
  }
  .nav a {
    color: #cfe0f5;
    text-decoration: none;
    font-size: 14px;
    padding: 3px 8px;
    border-radius: 4px;
  }
  .nav a.on {
    background: #fff;
    color: #1a5fb4;
    font-weight: 600;
  }
</style>
