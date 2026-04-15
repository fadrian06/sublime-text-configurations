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
        line_prefix = view.substr(Region(view.line(pt).a, pt))
        
        kind_directive = [KindId.NAMESPACE, 'd', 'Alpine.js Directive']
        kind_property = [KindId.VARIABLE, 'p', 'Alpine.js Property']
        kind_modifier = [KindId.KEYWORD, 'm', 'Modifier']
        kind_event = [KindId.FUNCTION, 'e', 'Event']

        # 1. CONTEXTO: Dentro de un VALOR de atributo (x-on="...", x-text="...")
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
            # Añadir propiedades de x-data
            for prop in sorted(list(properties)):
                if prop.lower().startswith(prefix.lower()):
                    out.append(CompletionItem(prop, kind=kind_property, details='Defined in x-data'))
            
            # Añadir variables mágicas comunes
            magics = ['$event', '$dispatch', '$nextTick', '$refs', '$el', '$watch', '$root', '$data', '$id']
            for magic in magics:
                if magic.lower().startswith(prefix.lower()) or (prefix.startswith('$') and magic.lower().startswith(prefix.lower())):
                    out.append(CompletionItem(magic, kind=[KindId.SNIPPET, 'v', 'Magic Variable']))

            return CompletionList(out)

        # 2. CONTEXTO: Dentro de un NOMBRE de atributo (x-on:..., @...)
        # Caso A: Modificadores (después de un punto en x-on o @)
        modifier_match = re.search(r'(?:x-on:|@)[\w-]+(?:\.[\w-]+)*\.$', line_prefix)
        if modifier_match:
            modifiers = [
                ('prevent', 'Calls event.preventDefault()'),
                ('stop', 'Calls event.stopPropagation()'),
                ('outside', 'Listen for events outside element'),
                ('window', 'Register listener on window'),
                ('document', 'Register listener on document'),
                ('once', 'Only call once'),
                ('debounce', 'Debounce execution (default 250ms)'),
                ('throttle', 'Throttle execution (default 250ms)'),
                ('self', 'Only trigger if event originated on self'),
                ('camel', 'Convert event name to camelCase'),
                ('dot', 'Convert dashes to dots in event name'),
                ('passive', 'Mark listener as passive'),
                ('capture', 'Execute during capturing phase'),
                # Keyboard/Mouse modifiers
                ('enter', 'Key: Enter'), ('space', 'Key: Space'), ('tab', 'Key: Tab'),
                ('escape', 'Key: Escape'), ('up', 'Key: Up'), ('down', 'Key: Down'),
                ('left', 'Key: Left'), ('right', 'Key: Right'),
                ('shift', 'Modifier: Shift'), ('ctrl', 'Modifier: Ctrl'),
                ('alt', 'Modifier: Alt'), ('meta', 'Modifier: Meta'), ('cmd', 'Modifier: Cmd')
            ]
            out = []
            for mod, detail in modifiers:
                out.append(CompletionItem(mod, kind=kind_modifier, details=detail))
            return CompletionList(out)

        # Caso B: Eventos (después de x-on: o @)
        event_match = re.search(r'(?:x-on:|@)$', line_prefix)
        if event_match:
            events = [
                # Window
                'afterprint', 'beforeprint', 'beforeunload', 'error', 'hashchange', 'load', 'message',
                'offline', 'online', 'pagehide', 'pageshow', 'popstate', 'resize', 'storage', 'unload',
                # Form
                'blur', 'change', 'contextmenu', 'focus', 'input', 'invalid', 'reset', 'search', 'select', 'submit',
                # Keyboard
                'keydown', 'keypress', 'keyup',
                # Mouse
                'click', 'dblclick', 'mousedown', 'mousemove', 'mouseout', 'mouseover', 'mouseup', 'mousewheel', 'wheel',
                # Drag
                'drag', 'dragend', 'dragenter', 'dragleave', 'dragover', 'dragstart', 'drop', 'scroll',
                # Clipboard
                'copy', 'cut', 'paste',
                # Media
                'abort', 'canplay', 'canplaythrough', 'cuechange', 'durationchange', 'emptied', 'ended',
                'loadeddata', 'loadedmetadata', 'loadstart', 'pause', 'play', 'playing', 'progress',
                'ratechange', 'seeked', 'seeking', 'stalled', 'suspend', 'timeupdate', 'volumechange', 'waiting',
                # Misc
                'toggle'
            ]
            out = []
            for event in sorted(list(set(events))):
                out.append(CompletionItem(event, kind=kind_event))
            return CompletionList(out)

        # 3. CONTEXTO: Sugerir directivas x-* (comportamiento base)
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
            CompletionItem.snippet_completion('x-ref', 'x-ref="$1"', kind=kind_directive),
            CompletionItem('x-cloak', kind=kind_directive),
            CompletionItem.snippet_completion('x-teleport', 'x-teleport="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-if', 'x-if="$1"', kind=kind_directive),
            CompletionItem.snippet_completion('x-id', 'x-id="$1"', kind=kind_directive),
        ]
        
        out = [comp for comp in available_completions if comp.trigger.lower().startswith(prefix.lower())]
        return CompletionList(out)
