import re
import sublime
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
        # Contexto de la línea actual
        line_prefix = view.substr(Region(view.line(pt).a, pt))
        # Contexto amplio para soportar etiquetas multilínea (hasta 500 caracteres atrás)
        wide_context = view.substr(Region(max(0, pt - 500), pt))
        
        kind_directive = [KindId.NAMESPACE, 'd', 'Alpine.js Directive']
        kind_property = [KindId.VARIABLE, 'p', 'Alpine.js Property']
        kind_modifier = [KindId.KEYWORD, 'm', 'Modifier']
        kind_event = [KindId.FUNCTION, 'e', 'Event']

        # 1. CONTEXTO: CDN de Alpine.js en script src
        if re.search(r'<script\s+[^>]*src=["\'][^"\']*$', line_prefix):
            out = [CompletionItem(
                "https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js",
                kind=[KindId.MARKUP, 'c', 'CDN'],
                annotation='Alpine.js v3.15.11'
            )]
            return CompletionList(out)

        # 2. CONTEXTO: Dentro de un VALOR de atributo (x-text="...", @click="...")
        # Detectamos si estamos dentro de un atributo Alpine (incluyendo shorthands)
        attr_match = re.search(r'([\w\.:@-]+)\s*=\s*["\']([^"\']*)$', wide_context, re.DOTALL)
        
        if attr_match:
            attr_name = attr_match.group(1)
            is_alpine = (
                attr_name.startswith('x-') or 
                attr_name.startswith('@') or 
                attr_name.startswith(':')
            )
            
            if is_alpine:
                content = view.substr(Region(0, view.size()))
                # Encontrar todos los bloques x-data="..." o x-data='...'
                x_data_blocks = re.findall(r'x-data\s*=\s*(?P<q>["\'])(.*?)(?P=q)', content, re.DOTALL)
                
                properties = set()
                for _, block_content in x_data_blocks:
                    # Extraer llaves de diversas formas:
                    # 1. key: value
                    properties.update(re.findall(r'(\w+)\s*:', block_content))
                    # 2. get key(), set key(), key() { ... }
                    properties.update(re.findall(r'(?:get|set)?\s*(\w+)\s*\(\)', block_content))
                    # 3. Métodos con parámetros: key(param) { ... }
                    properties.update(re.findall(r'(\w+)\s*\([^)]*\)\s*\{', block_content))

                out = []
                # Filtrar propiedades del sistema (como get, set) y duplicados
                ignored_keys = {'get', 'set', 'return', 'if', 'else', 'this'}
                for prop in sorted(list(properties)):
                    if prop not in ignored_keys:
                        out.append(CompletionItem(prop, kind=kind_property, details='Defined in x-data'))
                
                magics = ['$event', '$dispatch', '$nextTick', '$refs', '$el', '$watch', '$root', '$data', '$id']
                for magic in magics:
                    out.append(CompletionItem(magic, kind=[KindId.SNIPPET, 'v', 'Magic Variable']))

                return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)
            else:
                return CompletionList([])

        # 3. CONTEXTO: Dentro de un NOMBRE de atributo (Modificadores y Eventos)
        line_suffix = view.substr(Region(pt, view.line(pt).b))
        has_assignment = bool(re.match(r'^\s*=', line_suffix))

        # Modificadores
        last_word = line_prefix.split()[-1] if line_prefix.strip() else ""
        if '.' in last_word:
            attr_parts = last_word.split('.')
            attr_base = attr_parts[0]
            if attr_base.startswith('@') or attr_base.startswith('x-on:'):
                modifiers = [
                    ('prevent', 'preventDefault'), ('stop', 'stopPropagation'), ('outside', 'Outside element'),
                    ('window', 'On window'), ('document', 'On document'), ('once', 'Only once'),
                    ('debounce', 'Debounce 250ms'), ('throttle', 'Throttle 250ms'), ('self', 'Only on self'),
                    ('camel', 'To camelCase'), ('dot', 'To dots'), ('passive', 'Passive listener'),
                    ('capture', 'Capture phase'), ('enter', 'Key: Enter'), ('space', 'Key: Space'),
                    ('tab', 'Key: Tab'), ('escape', 'Key: Escape'), ('up', 'Key: Up'),
                    ('down', 'Key: Down'), ('left', 'Key: Left'), ('right', 'Key: Right'),
                    ('shift', 'Shift'), ('ctrl', 'Ctrl'), ('alt', 'Alt'), ('meta', 'Meta')
                ]
                out = []
                for mod, desc in modifiers:
                    if has_assignment:
                        out.append(CompletionItem(mod, kind=kind_modifier, details=desc))
                    else:
                        out.append(CompletionItem.snippet_completion(mod, mod + '="$1"', kind=kind_modifier, details=desc))
                return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)

        # Eventos
        if re.search(r'(?:x-on:|@)[\w-]*$', line_prefix):
            events = [
                'afterprint', 'beforeprint', 'beforeunload', 'error', 'hashchange', 'load', 'message',
                'offline', 'online', 'pagehide', 'pageshow', 'popstate', 'resize', 'storage', 'unload',
                'blur', 'change', 'contextmenu', 'focus', 'input', 'invalid', 'reset', 'search', 'select', 'submit',
                'keydown', 'keypress', 'keyup', 'click', 'dblclick', 'mousedown', 'mousemove', 'mouseout', 
                'mouseover', 'mouseup', 'mousewheel', 'wheel', 'drag', 'dragend', 'dragenter', 'dragleave', 
                'dragover', 'dragstart', 'drop', 'scroll', 'copy', 'cut', 'paste', 'abort', 'canplay', 
                'canplaythrough', 'cuechange', 'durationchange', 'emptied', 'ended', 'loadeddata', 
                'loadedmetadata', 'loadstart', 'pause', 'play', 'playing', 'progress', 'ratechange', 
                'seeked', 'seeking', 'stalled', 'suspend', 'timeupdate', 'volumechange', 'waiting', 'toggle'
            ]
            out = []
            for event in sorted(list(set(events))):
                if has_assignment:
                    out.append(CompletionItem(event, kind=kind_event))
                else:
                    out.append(CompletionItem.snippet_completion(event, event + '="$1"', kind=kind_event))
            return CompletionList(out, flags=sublime.INHIBIT_WORD_COMPLETIONS)

        # 4. CONTEXTO: Directivas base x-* 
        if view.match_selector(pt, 'text.html meta.tag - string - meta.attribute-with-value'):
            if not re.search(r'=\s*["\'][^"\']*$', wide_context, re.DOTALL):
                available_completions = [
                    CompletionItem.snippet_completion('x-data', 'x-data="{ $1 }"', kind=kind_directive),
                    CompletionItem.snippet_completion('x-init', 'x-init="$1"'),
                    CompletionItem.snippet_completion('x-show', 'x-show="$1"'),
                    CompletionItem.snippet_completion('x-bind', 'x-bind:$1="$2"'),
                    CompletionItem.snippet_completion('x-on', 'x-on:$1="$2"'),
                    CompletionItem.snippet_completion('x-text', 'x-text="$1"'),
                    CompletionItem.snippet_completion('x-html', 'x-html="$1"'),
                    CompletionItem.snippet_completion('x-model', 'x-model="$1"'),
                    CompletionItem.snippet_completion('x-modalable', 'x-modalable="$1"'),
                    CompletionItem.snippet_completion('x-for', 'x-for="$1"'),
                    CompletionItem('x-transition', kind=kind_directive),
                    CompletionItem.snippet_completion('x-ref', 'x-ref="$1"'),
                    CompletionItem('x-cloak', kind=kind_directive),
                    CompletionItem.snippet_completion('x-teleport', 'x-teleport="$1"'),
                    CompletionItem.snippet_completion('x-if', 'x-if="$1"'),
                    CompletionItem.snippet_completion('x-id', 'x-id="$1"'),
                ]
                return CompletionList(available_completions)

        return CompletionList([])
