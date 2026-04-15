import re
from sublime import View, CompletionList, CompletionItem, Region
from sublime_plugin import EventListener
from typing import List
from sublime_types import Point, KindId


class AlpineJsCompletions(EventListener):
    def on_modified_async(self, view: View):
        # Evitar disparar en la consola o widgets
        if view.settings().get('is_widget'):
            return
            
        # Obtener el punto actual del cursor
        if not view.sel():
            return
        pt = view.sel()[0].b
        if pt == 0:
            return
            
        # Verificar el último carácter escrito
        char = view.substr(Region(pt - 1, pt))
        
        # Si es uno de nuestros disparadores, forzamos el autocompletado
        if char in ":@.":
            # Solo si estamos dentro de una etiqueta HTML
            if view.match_selector(pt, "text.html meta.tag"):
                # Pequeño retardo para dejar que el buffer se actualice
                view.run_command("auto_complete", {
                    "disable_auto_insert": True,
                    "next_completion_if_showing": False
                })

    def on_query_completions(
        self,
        view: View,
        prefix: str,
        locations: List[Point],
    ) -> CompletionList:
        pt = locations[0]
        line_prefix = view.substr(Region(view.line(pt).a, pt))
        
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
        attr_value_match = re.search(r'(?:x-(?:show|text|html|model|modelable|ref|bind|on|data|effect|init)|[@:])[\w\.:-]*=["\'][^"\']*$', line_prefix)
        if attr_value_match:
            content = view.substr(Region(0, view.size()))
            x_data_matches = re.findall(r'x-data\s*=\s*["\']\{\s*([^}]*)\s*\}["\']', content)
            
            properties = set()
            for match in x_data_matches:
                keys = re.findall(r'(\w+)\s*:', match)
                for key in keys:
                    properties.add(key)

            out = []
            for prop in sorted(list(properties)):
                out.append(CompletionItem(prop, kind=kind_property, details='Defined in x-data'))
            
            magics = ['$event', '$dispatch', '$nextTick', '$refs', '$el', '$watch', '$root', '$data', '$id']
            for magic in magics:
                out.append(CompletionItem(magic, kind=[KindId.SNIPPET, 'v', 'Magic Variable']))

            return CompletionList(out)

        # 3. CONTEXTO: Dentro de un NOMBRE de atributo (x-on:..., @...)
        # Caso A: Modificadores (ej: @click.prevent)
        last_word = line_prefix.split()[-1] if line_prefix.strip() else ""
        if '.' in last_word:
            attr_base = last_word.split('.')[0]
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
                out = [CompletionItem(mod, kind=kind_modifier, details=desc) for mod, desc in modifiers]
                return CompletionList(out)

        # Caso B: Eventos (ej: @click, x-on:submit)
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
            out = [CompletionItem(event, kind=kind_event) for event in sorted(list(set(events)))]
            return CompletionList(out)

        # 4. CONTEXTO: Directivas base x-*
        if view.match_selector(pt, 'text.html meta.tag'):
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
                CompletionItem.snippet_completion('x-ref', 'x-ref="$1"', kind=kind_directive),
                CompletionItem('x-cloak', kind=kind_directive),
                CompletionItem.snippet_completion('x-teleport', 'x-teleport="$1"', kind=kind_directive),
                CompletionItem.snippet_completion('x-if', 'x-if="$1"', kind=kind_directive),
                CompletionItem.snippet_completion('x-id', 'x-id="$1"', kind=kind_directive),
            ]
            return CompletionList(available_completions)

        return CompletionList([])
