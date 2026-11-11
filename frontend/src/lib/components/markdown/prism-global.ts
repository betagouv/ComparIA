import Prism from 'prismjs'

// The language components below read `Prism` as a global. prismjs only sets it
// itself where `global` exists (Node), and the production bundle runs them
// before the core in the browser, so it is set here, in a module the
// languages import first.
;(globalThis as { Prism?: typeof Prism }).Prism = Prism

export default Prism
