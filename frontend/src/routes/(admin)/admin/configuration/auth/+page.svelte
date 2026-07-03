<script lang="ts">
  import { Badge } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { auth, initAuth } from '$lib/auth.svelte'
  import { onMount } from 'svelte'

  onMount(() => {
    if (!auth.config) initAuth()
  })

  const config = $derived(auth.config)
</script>

<PageLayout
  seoTitle="Configuration — Authentification"
  title="Configuration — Authentification"
  subtitle="Etat actuel, modifiable via variables d'environnement."
>
  {#if config}
    <div class="fr-table fr-table--no-caption">
      <table>
        <tbody>
          <tr>
            <th scope="row" class="w-48!">Mode d'accès</th>
            <td>
              {#if config.access_policy === 'sign_in_required'}
                <Badge text="sign_in_required" variant="yellow" size="sm" />
                <span class="fr-text--sm ml-2! text-[--text-mention-grey]">
                  Connexion obligatoire pour accéder à l'arène
                </span>
              {:else}
                <Badge text="anonymous_first" variant="light-info" size="sm" />
                <span class="fr-text--sm ml-2! text-[--text-mention-grey]">
                  Connexion facultative
                </span>
              {/if}
            </td>
          </tr>
          <tr>
            <th scope="row">Méthodes</th>
            <td>
              <Badge text="email_code" variant="light-info" size="sm" />
            </td>
          </tr>
          <tr>
            <th scope="row">SMTP</th>
            <td>
              {#if config.smtp_configured}
                <Badge text="configuré" variant="green" size="sm" />
              {:else}
                <Badge text="non configuré" variant="red" size="sm" />
                <span class="fr-text--sm ml-2! text-[--text-mention-grey]">
                  Les codes de connexion sont logués en console
                </span>
              {/if}
            </td>
          </tr>
          <tr>
            <th scope="row">Domaines autorisés</th>
            <td>
              {#if config.domain_allowlist.length > 0}
                {#each config.domain_allowlist as domain}
                  <Badge text={domain} variant="light-info" size="sm" />
                {/each}
              {:else}
                <span class="fr-text--sm text-[--text-mention-grey]">
                  Tous les domaines acceptés
                </span>
              {/if}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  {:else}
    <p class="fr-text--sm text-[--text-mention-grey]">Chargement...</p>
  {/if}
</PageLayout>
