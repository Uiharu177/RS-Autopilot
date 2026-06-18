import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'

hljs.registerLanguage('json', json)

hljs.registerLanguage('resonance', () => ({
  contains: [
    { begin: /\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/, className: 'time' },
    { begin: /\b(INFO)\b/, className: 'info' },
    { begin: /\b(WARNING|WARN)\b/, className: 'warning' },
    { begin: /\b(ERROR)\b/, className: 'error' },
    { begin: /\b(SUCCESS)\b/, className: 'success' },
    { begin: /\b(DEBUG)\b/, className: 'built_in' },
  ]
}))

export default hljs
