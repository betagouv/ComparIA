<script lang="ts">
  import { page } from '$app/stores'

  // Typage des données
  interface Model {
    id: string
    simple_name: string
    url?: string
    license: string
    [key: string]: unknown
  }

  // Chargement des données des modèles
  export let data: { models: Model[] }

  // Extraire les modèles depuis les données
  $: models = data.models
</script>

<div class="models-container">
  <table>
    <thead>
      <tr>
        <th>Nom</th>
        <th>Lien</th>
        <th>Licence</th>
      </tr>
    </thead>
    <tbody>
      {#each models as model}
        <tr>
          <td>{model.simple_name}</td>
          <td>
            {#if model.url}
              <a href={model.url} target="_blank" rel="noopener external">
                {model.url}
              </a>
            {:else}
              Non disponible
            {/if}
          </td>
          <td>{model.license}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .models-container {
    margin: 2rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }

  th {
    font-weight: 600;
    background-color: #f7fafc;
  }

  a {
    color: #3182ce;
    text-decoration: none;
  }

  a:hover {
    text-decoration: underline;
  }
</style>
