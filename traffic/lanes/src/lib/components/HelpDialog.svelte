<script lang="ts">
  let dialog: HTMLDialogElement;
</script>

<button class="btn" onclick={() => dialog.showModal()}>? How to use</button>

<dialog bind:this={dialog} class="help-dialog">
  <header>
    <h2>How to use</h2>
    <button class="btn close" onclick={() => dialog.close()} aria-label="Close">✕</button>
  </header>

  <h3>Search</h3>
  <p>
    Pick a <b>Country</b> (sets the route-shield colours), choose a <b>Search by</b> mode,
    type the ref / name / id and hit <b>Search</b>. Open <b>Configuration</b> for options —
    adjacent ways, intersection detection, lane width, node tags — hover each for a one-line
    explanation. <i>Start at end number</i> picks which chain end to draw from when a road
    has several. Collapse the panel (▾) to save space.
  </p>

  <h3>Completeness</h3>
  <p>
    Two headline scores — <b>attributes tagged</b> and <b>length vs official</b> (Wikidata) —
    plus per-attribute coverage bars, worst first. <b>Details</b> shows a maxspeed
    distribution. <b>⬇ Export data</b> downloads every drawn way (computed fields + raw OSM
    tags) as CSV or JSON, with per-column tick boxes.
  </p>

  <h3>Diagram &amp; map</h3>
  <p>
    Each way row links to <b>(M)</b> Mapillary, <b>(J)</b> JOSM remote control,
    <b>(L)</b> level0 editor, <b>(R)</b> Rapid/iD editor, <b>(Z)</b> zoom the map to that
    segment, and <b>(V)</b> reload
    just that way. After a search the whole road is drawn and fit to view; <b>hovering</b> a
    row highlights that segment in place, <b>(Z)</b> zooms to it. Crossing roads appear as
    amber markers linking to Mapillary. Drag the divider to resize diagram vs map; use the
    layer control (top-right) or <b>Map options</b> to switch base imagery or paste a custom
    <code>{'{z}/{x}/{y}'}</code> tile source.
  </p>

  <footer>
    <button class="btn btn-primary" onclick={() => dialog.close()}>Got it</button>
  </footer>
</dialog>

<style>
  .help-dialog {
    width: min(620px, 92vw);
    border: 1px solid #d9dee6;
    border-radius: 10px;
    padding: 16px 20px;
    font-family: sans-serif;
    color: #374151;
    line-height: 1.5;
  }
  .help-dialog::backdrop {
    background: rgba(17, 24, 39, 0.45);
  }
  .help-dialog header {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }
  .help-dialog header h2 {
    margin: 0;
    font-size: 17px;
    flex: 1;
  }
  .help-dialog h3 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #6b7280;
    margin: 14px 0 4px;
  }
  .help-dialog p {
    margin: 0;
    font-size: 13px;
  }
  .help-dialog code {
    background: #f3f5f9;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 12px;
  }
  .close {
    padding: 2px 8px;
  }
  footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
</style>
