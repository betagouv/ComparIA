import Prism from 'prismjs'

// The language components read a global `Prism`. The bundler may run them
// before prismjs sets it, so set it here and load them from ./prism-languages,
// which imports this module first.
;(globalThis as { Prism?: typeof Prism }).Prism = Prism

export default Prism
