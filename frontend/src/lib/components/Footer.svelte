<script lang="ts">
  import ThemeSelector from '$components/ThemeSelector.svelte'
  import { getI18nContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  const locale = getLocale()
  const i18nData = getI18nContext()

  const links = [
    {
      href: 'https://github.com/betagouv/languia',
      label: m['footer.links.sources'](),
      target: '_blank',
      rel: 'noopener external'
    }
  ]
</script>

<footer id="main-footer" style="background:#1f1f1f;color:rgba(255,255,255,0.7);padding:48px 0 24px;">
  <div class="fr-container">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:32px;margin-bottom:40px;">
      <a href="/" title={m['footer.backHome']()} style="text-decoration:none;">
        <span style="font-size:1.25rem;font-weight:400;letter-spacing:-0.04em;color:#ffffff;font-family:Arial,sans-serif;">
          Compa<span style="color:#fa520f;">RAG</span>
        </span>
      </a>
      <p style="max-width:380px;font-size:0.875rem;margin:0;line-height:1.5;">
        {@html sanitize(
          m['footer.writeUs']({
            formLinkProps: externalLinkProps('https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX'),
            contactLinkProps: externalLinkProps(`mailto:${i18nData.contact}`)
          })
        )}
      </p>
    </div>

    <div style="border-top:1px solid rgba(255,255,255,0.12);padding:32px 0 24px;margin-bottom:24px;">
      <p style="font-size:0.95rem;font-weight:400;color:#ffffff;margin:0 0 4px;">Lettre d'information</p>
      <p style="font-size:0.8rem;color:rgba(255,255,255,0.55);margin:0 0 16px;">Partenariats, nouveaux outils, jeux de données et fonctionnalités.</p>
      <iframe
        data-tally-src="https://tally.so/embed/zxKR40?alignLeft=1&hideTitle=1&transparentBackground=1&dynamicHeight=1"
        loading="lazy"
        width="100%"
        height="120"
        frameborder="0"
        marginheight="0"
        marginwidth="0"
        title="Infolettre CompaRAG"
        style="outline:none;color-scheme:dark;"
      ></iframe>
    </div>

    <div style="border-top:1px solid rgba(255,255,255,0.12);padding-top:20px;display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:12px;">
      <ul style="list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:16px;">
        {#each links as { label, ...props } (props.href)}
          <li>
            <a style="color:rgba(255,255,255,0.55);font-size:0.8rem;text-decoration:none;" {...props}
              onmouseenter={(e) => (e.currentTarget as HTMLElement).style.color='#fa520f'}
              onmouseleave={(e) => (e.currentTarget as HTMLElement).style.color='rgba(255,255,255,0.55)'}
            >{label}</a>
          </li>
        {/each}
      </ul>
      <ThemeSelector />
    </div>
  </div>
</footer>
