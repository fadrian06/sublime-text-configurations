import re
from sublime import View, CompletionList, CompletionItem, Region
from sublime_plugin import EventListener
from typing import List
from sublime_types import Point, KindId


class AlpineJsCompletions(EventListener):
    def on_query_completions(
        self,
        view: View,
        prefix: str,
        locations: List[Point],
    ) -> CompletionList:
        pt = locations[0]
        
        # 1. Verificar contexto: ¿Estamos dentro de un valor de atributo Alpine?
        # Obtenemos el texto de la línea hasta el cursor
        line_prefix = view.substr(Region(view.line(pt).a, pt))
        # Buscamos si el cursor está precedido por un atributo x-* seguido de comillas abiertas
        attr_match = re.search(r'(x-(?:show|text|html|model|modelable|ref|bind|on|data))=["\'][^"\']*$', line_prefix)
        
        kind_directive = [KindId.NAMESPACE, 'd', 'Alpine.js Directive']
        kind_property = [KindId.VARIABLE, 'p', 'Alpine.js Property']

        if attr_match:
            # CONTEXTO: Dentro de un atributo (Sugerir propiedades de x-data)
            content = view.substr(Region(0, view.size()))
            # Buscamos patrones x-data="{ prop: val }"
            x_data_matches = re.findall(r'x-data\s*=\s*["\']\{\s*([^}]*)\s*\}["\']', content)
            
            properties = set()
            for match in x_data_matches:
                # Extraemos las llaves definidas (ej: "message:" -> "message")
                keys = re.findall(r'(\w+)\s*:', match)
                for key in keys:
                    properties.add(key)

            out = []
            for prop in sorted(list(properties)):
                if prop.lower().startswith(prefix.lower()):
                    out.append(CompletionItem(
                        prop,
                        kind=kind_property,
                        details='Defined in x-data'
                    ))
            return CompletionList(out)

        # CONTEXTO: Fuera de atributos (Sugerir directivas x-*)
        if not view.match_selector(pt, 'text.html meta.tag'):
            return []

        available_completions = [
            CompletionItem.snippet_completion('x-data', 'x-data="{ $1 }"', kind=kind_directive),
            CompletionItem.snippet_completion('x-init', 'x-init="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-show', 'x-show="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-bind', 'x-bind:$1="$2"', kind=kind_directive),
            CompletionItem.snippet_completion('x-on', 'x-on:$1="$2"', kind=kind_directive),
            CompletionItem.snippet_completion('x-text', 'x-text="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-html', 'x-html="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-model', 'x-model="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-modalable', 'x-modalable="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-for', 'x-for="$1"', kind=kind_directive),
            CompletionItem('x-transition', kind=kind_directive),
            CompletionItem.snippet_completion('x-effect', 'x-effect="$1"', kind=kind_directive),
            CompletionItem('x-ignore', kind=kind_directive),
            CompletionItem.snippet_completion('x-ref', 'x-ref="$1"', kind=kind_directive),
            CompletionItem('x-cloak', kind=kind_directive),
            CompletionItem.snippet_completion('x-teleport', 'x-teleport="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-if', 'x-if="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-id', 'x-id="$1"', kind=kind_directive),
        ]
        
        out = [comp for comp in available_completions if comp.trigger.lower().startswith(prefix.lower())]
        return CompletionList(out)
